"""Adapter payloads and merge rules for each platform's hook configuration.

Pure builders: nothing here touches the filesystem except `load_json_settings`,
which only reads. The generator in `prompt_submit_hooks` decides what is written.
"""

from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration._hook_launcher import (
    PROMPT_SUBMIT_LAUNCHER_POSIX,
    PROMPT_SUBMIT_LAUNCHER_WINDOWS,
)
from providence_wizard.orchestration._hook_platforms import (
    CENTRAL_PROMPT_SUBMIT_HOOK,
    PLATFORM_HOOK_TIMEOUT_SECONDS,
    HookGenerationError,
)


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


CODEX_BLOCK_BEGIN = "# >>> providence prompt-submit hook (managed) >>>"
CODEX_BLOCK_END = "# <<< providence prompt-submit hook <<<"
PROVIDENCE_HOOK_MARKERS = (CENTRAL_PROMPT_SUBMIT_HOOK.as_posix(),)
# Inputs retired by the rebrand: recognised only to be rejected, never refreshed.
RETIRED_HOOK_MARKERS = ("sdd-governance-inject.py",)


def codex_prompt_submit_config(command: str) -> str:
    """Return the managed Codex hook TOML block for the generated central hook."""
    escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
    return f'''{CODEX_BLOCK_BEGIN}
[[hooks.UserPromptSubmit]]

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{escaped_command}"
timeout = {PLATFORM_HOOK_TIMEOUT_SECONDS}
{CODEX_BLOCK_END}
'''


def retired_codex_config_reason(existing: str) -> str | None:
    """Return why `existing` holds retired Providence hook input, else None.

    A pre-rebrand reference, or a bare hook block written by an older generator
    (no managed markers) that points at the Providence hook, is retired input.
    Refreshing it silently would interpret it; it is reported instead.
    """
    for marker in RETIRED_HOOK_MARKERS:
        if marker in existing:
            return f"references the retired hook {marker!r}"
    managed = CODEX_BLOCK_BEGIN in existing and CODEX_BLOCK_END in existing
    if (
        not managed
        and "[[hooks.UserPromptSubmit]]" in existing
        and any(marker in existing for marker in PROVIDENCE_HOOK_MARKERS)
    ):
        return "holds an unmanaged Providence hook block from an older generator"
    return None


def merge_codex_config(existing: str, command: str) -> str:
    """Insert or refresh the managed hook block, keeping the user's other TOML.

    Retired input is rejected with `HookGenerationError`, never rewritten.
    """
    reason = retired_codex_config_reason(existing)
    if reason is not None:
        raise HookGenerationError(f"existing Codex config {reason}")
    block = codex_prompt_submit_config(command)
    begin = existing.find(CODEX_BLOCK_BEGIN)
    end = existing.find(CODEX_BLOCK_END, begin) if begin != -1 else -1
    if begin != -1 and end != -1:
        return (
            existing[:begin]
            + block
            + existing[end + len(CODEX_BLOCK_END) :].lstrip("\r\n")
        )
    if not existing.strip():
        return block
    return existing.rstrip("\r\n") + "\n\n" + block


def is_providence_hook_entry(entry: object) -> bool:
    """Return whether a hook-entry dict runs the Providence central hook."""
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(hook, dict)
        and any(
            marker in str(hook.get("command", "")) for marker in PROVIDENCE_HOOK_MARKERS
        )
        for hook in hooks
    )


def upsert_hook_entries(existing: object, ours: list[object]) -> list[object]:
    """Return `ours` plus the user's non-Providence entries (idempotent)."""
    kept = (
        [e for e in existing if not is_providence_hook_entry(e)]
        if isinstance(existing, list)
        else []
    )
    return [*ours, *kept]


def devin_prompt_submit_hooks(command: str) -> dict[str, list[object]]:
    """Return the `.devin/hooks.v1.json` events for the generated central hook."""
    hook = {
        "type": "command",
        "command": command,
        "timeout": PLATFORM_HOOK_TIMEOUT_SECONDS,
    }
    return {"UserPromptSubmit": [{"hooks": [hook]}]}


def gemini_prompt_submit_hooks(command: str) -> dict[str, list[object]]:
    """Return Gemini hook settings pointing at the generated central hook."""
    # Gemini expresses hook timeouts in milliseconds.
    hook = {
        "type": "command",
        "command": command,
        "timeout": PLATFORM_HOOK_TIMEOUT_SECONDS * 1000,
    }
    return {"BeforeAgent": [{"hooks": [hook]}]}


def copilot_prompt_submit_hooks() -> dict[str, object]:
    """Return the Copilot hook settings for the central hook.

    The file is tracked and shared by Linux and Windows machines, so it never
    encodes the OS that generated it: Copilot CLI's documented per-shell keys
    `bash` and `powershell` are both written, and `command` (its documented
    cross-platform fallback) is the POSIX launcher. The keys `windows`, `linux`
    and `osx` of VS Code are not written: whether one entry may carry both key
    families is undocumented and stays an open question.
    """
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "type": "command",
                    "command": PROMPT_SUBMIT_LAUNCHER_POSIX,
                    "bash": PROMPT_SUBMIT_LAUNCHER_POSIX,
                    "powershell": PROMPT_SUBMIT_LAUNCHER_WINDOWS,
                    "timeout": PLATFORM_HOOK_TIMEOUT_SECONDS,
                }
            ]
        }
    }


def load_json_settings(path: Path) -> dict[str, object]:
    """Return the JSON object stored in `path`, `{}` only when it is absent.

    An unparsable file or a non-object payload belongs to the user: it raises
    `HookGenerationError` so no caller overwrites it with `{}` plus its own keys.
    """
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HookGenerationError(
            f"{path} is not valid JSON ({exc}); fix or remove it and rerun "
            "the generator"
        ) from exc
    if not isinstance(payload, dict):
        raise HookGenerationError(
            f"{path} must hold a JSON object, found {type(payload).__name__}; "
            "fix or remove it and rerun the generator"
        )
    return payload
