"""Prompt-submit governance hook generation."""

from __future__ import annotations

import json
from pathlib import Path

from providence_core.utils.text_io import write_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME

SUPPORTED_PROMPT_HOOK_AGENTS = frozenset({"claude", "codex", "gemini"})
CENTRAL_PROMPT_SUBMIT_HOOK = (
    Path(RUNTIME_DIRNAME) / "runtime" / "hooks" / "prompt-submit.py"
)
CENTRAL_PROMPT_SUBMIT_COMMAND = f"python3 {CENTRAL_PROMPT_SUBMIT_HOOK.as_posix()}"

PROMPT_SUBMIT_HOOK_SCRIPT = '''#!/usr/bin/env python3
"""Shared prompt-submit governance hook for Claude Code / Codex CLI / Gemini CLI.

Reads the hook's stdin JSON payload, extracts the "prompt" field, runs a
lightweight governance check, and emits the shared additionalContext output
shape understood by supported platforms. Never blocks (always exits 0).

Explicit `/sdd-ask ...` prompts are a special case: the slash-command adapter
for that turn will itself run a full `providence ask` call, so this hook skips its
own full invocation to avoid paying the governance-snapshot cost twice in the
same turn (spike: 20260714-sdd-ask-single-entrypoint-spike, R-001 preferred
strategy). If detection is ever uncertain, this hook falls back to the full
path rather than silently dropping governance context.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

def _extract_context_field(context: str, field: str, default: str) -> str:
    pattern = rf"\\b{re.escape(field)}\\s*[:=]\\s*([A-Za-z0-9_.-]+)"
    match = re.search(pattern, context)
    return match.group(1) if match else default

def _extract_footer_line(context: str) -> str | None:
    match = re.search(r"^PROVIDENCE GOVERNANCE:.*$", context, re.MULTILINE)
    return match.group(0) if match else None

def _render_activation_header(context: str) -> str:
    fingerprint = _extract_context_field(context, "fingerprint", "unknown")[:8]
    execution_gate = _extract_context_field(context, "execution_gate", "unknown")
    lines = [
        "PROVIDENCE GOVERNANCE ACTIVE | "
        "source=prompt-submit-hook | "
        "governance_mode=hard | "
        f"execution_gate={execution_gate} | "
        f"fingerprint={fingerprint}",
        "Instruction: start your response with one short SDD governance "
        "status line when this context is present.",
        "Instruction: this is context injection only; no provider delegation or "
        "implementation was executed by the hook.",
    ]
    footer_line = _extract_footer_line(context)
    if footer_line:
        lines.append(
            "Instruction: if the platform response policy allows it, end your "
            f"response with this compact footer: {footer_line}"
        )
    return "\\n".join(lines)

def _is_explicit_sdd_ask(prompt: str) -> bool:
    stripped = prompt.strip().casefold()
    return stripped == "/sdd-ask" or stripped.startswith("/sdd-ask ")

def _render_explicit_command_context() -> str:
    return "\\n".join([
        "PROVIDENCE GOVERNANCE ACTIVE | "
        "source=prompt-submit-hook | "
        "entrypoint=explicit_command | "
        "explicit_command=sdd-ask",
        "Instruction: this turn is an explicit /sdd-ask invocation; the hook "
        "deferred its own governance query to that command's own `providence ask` "
        "call this turn, to avoid running the full governance snapshot "
        "twice in one turn.",
        "Instruction: this is context injection only; no provider delegation or "
        "implementation was executed by the hook.",
    ])

def main() -> int:
    if Path(".providence/runtime/hook-disabled").exists():
        return 0
    if not Path(".providence/metadata.json").exists():
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    prompt = payload.get("prompt", "")
    if not prompt:
        return 0
    if _is_explicit_sdd_ask(prompt):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _render_explicit_command_context(),
            }
        }))
        return 0
    try:
        env = dict(os.environ)
        env["SDD_ASK_ENTRYPOINT"] = "hook"
        result = subprocess.run(
            ["providence", "ask", prompt],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        context = result.stdout.strip()
    except Exception:
        return 0
    if context:
        context = _render_activation_header(context) + "\\n\\n" + context
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

CLAUDE_PROMPT_SUBMIT_SETTINGS = {
    "hooks": {
        "UserPromptSubmit": [
            {
                "matcher": ".*",
                "hooks": [
                    {
                        "type": "command",
                        "command": CENTRAL_PROMPT_SUBMIT_COMMAND,
                    }
                ],
            }
        ]
    }
}

CODEX_PROMPT_SUBMIT_CONFIG = f'''[[hooks.UserPromptSubmit]]

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{CENTRAL_PROMPT_SUBMIT_COMMAND}"
timeout = 10
'''

GEMINI_PROMPT_SUBMIT_HOOKS = {
    "BeforeAgent": [
        {"hooks": [{"type": "command", "command": CENTRAL_PROMPT_SUBMIT_COMMAND}]}
    ]
}


def resolve_prompt_submit_hook_agents(selected: set[str] | None) -> set[str]:
    """Return hook-capable agents requested by the seedling selection."""
    if selected is None:
        return set(SUPPORTED_PROMPT_HOOK_AGENTS)
    return set(selected) & set(SUPPORTED_PROMPT_HOOK_AGENTS)


class PromptSubmitHookGenerator:
    """Generate central prompt-submit hook runtime and selected agent adapters."""

    def __init__(self, output_base: Path, agents: set[str]) -> None:
        self.output_base = output_base
        self.agents = set(agents)

    def generate(self) -> bool:
        """Generate the central hook and configured agent adapters."""
        if not self.agents:
            return False
        hook_path = self.output_base / CENTRAL_PROMPT_SUBMIT_HOOK
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(hook_path, PROMPT_SUBMIT_HOOK_SCRIPT)
        hook_path.chmod(0o755)

        if "claude" in self.agents:
            self._write_claude_adapter()
        if "codex" in self.agents:
            self._write_codex_adapter()
        if "gemini" in self.agents:
            self._write_gemini_adapter()
        return True

    def _write_claude_adapter(self) -> None:
        settings_path = self.output_base / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(
            settings_path, json.dumps(CLAUDE_PROMPT_SUBMIT_SETTINGS, indent=2) + "\n"
        )

    def _write_codex_adapter(self) -> None:
        config_path = self.output_base / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(config_path, CODEX_PROMPT_SUBMIT_CONFIG)

    def _write_gemini_adapter(self) -> None:
        settings_path = self.output_base / ".gemini" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = self._load_json_object(settings_path)
        settings["hooks"] = GEMINI_PROMPT_SUBMIT_HOOKS
        write_text_utf8(settings_path, json.dumps(settings, indent=2) + "\n")

    def _load_json_object(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
