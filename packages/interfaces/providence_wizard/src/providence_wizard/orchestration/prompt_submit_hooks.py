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
PROMPT_SUBMIT_LAUNCHER = (
    "sh -c '"
    "root=${PROVIDENCE_WORKSPACE_ROOT:-$PWD}; "
    'while [ "$root" != "/" ] && [ ! -f "$root/.providence/metadata.json" ]; '
    'do parent=${root%/*}; [ "$parent" = "$root" ] && break; root=$parent; done; '
    'hook="$root/.providence/runtime/hooks/prompt-submit.py"; '
    'if [ -f "$hook" ]; then exec python3 "$hook"; fi; exit 0'
    "' sh"
)
CENTRAL_PROMPT_SUBMIT_COMMAND = PROMPT_SUBMIT_LAUNCHER


def central_prompt_submit_command(output_base: Path) -> str:
    """Return a relocatable command for the generated central hook.

    ``output_base`` remains part of the API because callers use it to generate
    the hook itself.  The adapter command must not embed that path: the wizard
    consolidates and deploys the output into another project location.
    """
    del output_base
    return PROMPT_SUBMIT_LAUNCHER


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

Header/footer contract (20260913-governance-hooks-dogfood): every emitted
context starts with a `PROVIDENCE GOVERNANCE ACTIVE` header and carries a
footer *instruction* telling the model to end its response with a compact
`PROVIDENCE GOVERNANCE: ...` line. On the normal path the instruction embeds
the concrete footer text extracted from `providence ask`'s own output; on the
explicit `/sdd-ask` path (which does not call `providence ask` itself) it
embeds the same footer template the `/sdd-ask` command adapter resolves (see
`sdd-ask.prompt.md`'s `PROVIDENCE GOVERNANCE` section), so the contract is
never silently dropped.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

def _workspace_root() -> Path:
    try:
        return Path(__file__).resolve().parents[3]
    except IndexError:
        return Path.cwd()

def _extract_context_field(context: str, field: str, default: str) -> str:
    pattern = rf"\\b{re.escape(field)}\\s*[:=]\\s*([A-Za-z0-9_.-]+)"
    match = re.search(pattern, context)
    return match.group(1) if match else default

def _extract_footer_line(context: str) -> str | None:
    match = re.search(r"^PROVIDENCE GOVERNANCE:.*$", context, re.MULTILINE)
    return match.group(0) if match else None

def _footer_instruction(footer_line: str) -> str:
    return (
        "Instruction: if the platform response policy allows it, end your "
        f"response with this compact footer: {footer_line}"
    )

_SDD_ASK_FOOTER_TEMPLATE = (
    "PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=sdd-ask"
)

def _render_activation_header(context: str) -> str:
    fingerprint = _extract_context_field(context, "fingerprint", "unknown")[:8]
    execution_gate = _extract_context_field(context, "execution_gate", "unknown")
    lines = [
        "PROVIDENCE GOVERNANCE ACTIVE | "
        "source=prompt-submit-hook | "
        "governance_mode=hard | "
        f"execution_gate={execution_gate} | "
        f"fingerprint={fingerprint}",
        "Instruction: start your response with one short Providence governance "
        "status line when this context is present.",
        "Instruction: this is context injection only; no provider delegation or "
        "implementation was executed by the hook.",
    ]
    footer_line = _extract_footer_line(context)
    if footer_line:
        lines.append(_footer_instruction(footer_line))
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
        _footer_instruction(_SDD_ASK_FOOTER_TEMPLATE),
    ])

def _resolve_providence_cli(workspace_root: Path) -> str | None:
    found = shutil.which("providence")
    if found:
        return found
    for candidate in (
        workspace_root / ".venv" / "bin" / "providence",
        workspace_root / "venv" / "bin" / "providence",
    ):
        if candidate.is_file():
            return str(candidate)
    return None

def main() -> int:
    workspace_root = _workspace_root()
    if (workspace_root / ".providence/runtime/hook-disabled").exists():
        return 0
    if not (workspace_root / ".providence/metadata.json").exists():
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
    providence_cli = _resolve_providence_cli(workspace_root)
    if providence_cli is None:
        return 0
    try:
        env = dict(os.environ)
        env["SDD_ASK_ENTRYPOINT"] = "hook"
        env.setdefault("PROVIDENCE_WORKSPACE_ROOT", str(workspace_root))
        result = subprocess.run(
            [providence_cli, "ask", prompt],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(workspace_root),
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


def claude_user_prompt_submit_hook_entries(command: str) -> list[object]:
    """Return the `UserPromptSubmit` hook-entry list for the generated central hook."""
    return [
        {
            "matcher": ".*",
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                }
            ],
        }
    ]


def claude_prompt_submit_settings(command: str) -> dict[str, object]:
    """Return Claude hook settings pointing at the generated central hook."""
    return {
        "hooks": {
            "UserPromptSubmit": claude_user_prompt_submit_hook_entries(command),
        }
    }


def codex_prompt_submit_config(command: str) -> str:
    """Return Codex hook TOML pointing at the generated central hook."""
    escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
    return f'''[[hooks.UserPromptSubmit]]

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{escaped_command}"
timeout = 10
'''


def gemini_prompt_submit_hooks(command: str) -> dict[str, object]:
    """Return Gemini hook settings pointing at the generated central hook."""
    return {"BeforeAgent": [{"hooks": [{"type": "command", "command": command}]}]}


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
        self.central_command = central_prompt_submit_command(output_base)

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
        settings = self._load_json_object(settings_path)
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        # Merge only the "UserPromptSubmit" event key — other hook event
        # types (e.g. "PreToolUse", written by ai_seeds.generate_claude_seed)
        # must survive this write, not be silently overwritten.
        hooks["UserPromptSubmit"] = claude_user_prompt_submit_hook_entries(
            self.central_command
        )
        write_text_utf8(settings_path, json.dumps(settings, indent=2) + "\n")

    def _write_codex_adapter(self) -> None:
        config_path = self.output_base / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(config_path, codex_prompt_submit_config(self.central_command))

    def _write_gemini_adapter(self) -> None:
        settings_path = self.output_base / ".gemini" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = self._load_json_object(settings_path)
        settings["hooks"] = gemini_prompt_submit_hooks(self.central_command)
        write_text_utf8(settings_path, json.dumps(settings, indent=2) + "\n")

    def _load_json_object(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
