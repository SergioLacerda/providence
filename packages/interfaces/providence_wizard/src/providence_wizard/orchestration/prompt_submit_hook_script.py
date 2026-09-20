"""Source template of the generated central prompt-submit hook script.

`PROMPT_SUBMIT_HOOK_SCRIPT` is a string that the wizard writes out as a
standalone `.providence/runtime/hooks/prompt-submit.py`; it runs in the
external agent CLI's process (Claude/Codex/Gemini/Copilot), not in this
package. Kept apart from `prompt_submit_hooks` (the generator) so each stays
small.
"""

from __future__ import annotations

PROMPT_SUBMIT_HOOK_SCRIPT = '''#!/usr/bin/env python3
"""Shared prompt-submit governance hook for Claude Code / Codex CLI / Gemini CLI / Copilot.

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

def _event_name(payload: dict) -> str:
    # Each platform names its prompt event differently (Claude/Codex/Copilot:
    # UserPromptSubmit, Gemini: BeforeAgent) and echoes it in the payload.
    name = payload.get("hook_event_name") or payload.get("hookEventName")
    return name if isinstance(name, str) and name else "UserPromptSubmit"

def _resolve_providence_cli(workspace_root: Path) -> str | None:
    found = shutil.which("providence")
    if found:
        return found
    for candidate in (
        workspace_root / ".venv" / "bin" / "providence",
        workspace_root / ".venv" / "Scripts" / "providence.exe",
        workspace_root / "venv" / "bin" / "providence",
        workspace_root / "venv" / "Scripts" / "providence.exe",
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
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        payload = json.loads(raw or "{}")
    except (json.JSONDecodeError, OSError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    prompt = payload.get("prompt", "")
    if not prompt:
        return 0
    event_name = _event_name(payload)
    if _is_explicit_sdd_ask(prompt):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": event_name,
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
        env["PYTHONUTF8"] = "1"
        # The hook resolved this root from its own location; an inherited value
        # may name another project and must not win.
        env["PROVIDENCE_WORKSPACE_ROOT"] = str(workspace_root)
        result = subprocess.run(
            [providence_cli, "ask", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
                "hookEventName": event_name,
                "additionalContext": context,
            }
        }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''
