"""Prompt-submit governance hook generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from providence_core.utils.text_io import write_text_utf8
from providence_wizard.constants import RUNTIME_DIRNAME
from providence_wizard.orchestration.prompt_submit_hook_script import (
    PROMPT_SUBMIT_HOOK_SCRIPT,
)

SUPPORTED_PROMPT_HOOK_AGENTS = frozenset({"claude", "codex", "gemini", "copilot"})
CENTRAL_PROMPT_SUBMIT_HOOK = (
    Path(RUNTIME_DIRNAME) / "runtime" / "hooks" / "prompt-submit.py"
)
COPILOT_HOOK_FILE = Path(".github") / "hooks" / "providence-prompt-submit.json"
# The launcher must run under every shell an agent may use (sh, cmd.exe,
# PowerShell 5.1), so it is a single Python one-liner: only single quotes
# inside, and no `$`, `%`, backtick, `&`, `|` or `^`.  It walks up from the
# cwd (or PROVIDENCE_WORKSPACE_ROOT) to the workspace and runs the central hook
# in-process (stdin/stdout are shared); a missing hook exits 0 silently.  The
# walk stops at the first `.git` (the project boundary): a project without its
# own `.providence/` must not inherit governance from a parent directory.
_LAUNCHER_CODE = (
    "import os,runpy,pathlib as P;"
    "p=P.Path(os.environ.get('PROVIDENCE_WORKSPACE_ROOT') or os.getcwd()).resolve();"
    "a=[p,*p.parents];"
    "a=a[:next((i for i,d in enumerate(a) if (d/'.git').exists()),len(a))+1];"
    "r=next((d for d in a if (d/'.providence'/'metadata.json').is_file()),None);"
    "h=r and r/'.providence/runtime/hooks/prompt-submit.py';"
    "h and h.is_file() and runpy.run_path(str(h),run_name='__main__')"
)
# Windows installs expose `python`/`py`; `python3` is often a Store stub there.
_LAUNCHER_PYTHON = "python" if os.name == "nt" else "python3"
PROMPT_SUBMIT_LAUNCHER = f'{_LAUNCHER_PYTHON} -c "{_LAUNCHER_CODE}"'
CENTRAL_PROMPT_SUBMIT_COMMAND = PROMPT_SUBMIT_LAUNCHER


def central_prompt_submit_command(output_base: Path) -> str:
    """Return a relocatable command for the generated central hook.

    ``output_base`` remains part of the API because callers use it to generate
    the hook itself.  The adapter command must not embed that path: the wizard
    consolidates and deploys the output into another project location.
    """
    del output_base
    return PROMPT_SUBMIT_LAUNCHER


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
_PROVIDENCE_HOOK_MARKERS = (
    CENTRAL_PROMPT_SUBMIT_HOOK.as_posix(),
    "sdd-governance-inject.py",  # pre-rebrand central hook
)


def codex_prompt_submit_config(command: str) -> str:
    """Return the managed Codex hook TOML block for the generated central hook."""
    escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
    return f'''{CODEX_BLOCK_BEGIN}
[[hooks.UserPromptSubmit]]

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{escaped_command}"
timeout = 10
{CODEX_BLOCK_END}
'''


def merge_codex_config(existing: str, command: str) -> str:
    """Insert or refresh the managed hook block, keeping the user's other TOML.

    Older generators wrote the bare hook block as the whole file; that legacy
    shape is replaced, anything else the user wrote is preserved.
    """
    block = codex_prompt_submit_config(command)
    begin = existing.find(CODEX_BLOCK_BEGIN)
    end = existing.find(CODEX_BLOCK_END, begin) if begin != -1 else -1
    if begin != -1 and end != -1:
        return (
            existing[:begin]
            + block
            + existing[end + len(CODEX_BLOCK_END) :].lstrip("\r\n")
        )
    is_legacy = (
        existing.lstrip().startswith("[[hooks.UserPromptSubmit]]")
        and existing.count("[[") == 2
        and any(marker in existing for marker in _PROVIDENCE_HOOK_MARKERS)
    )
    if not existing.strip() or is_legacy:
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
            marker in str(hook.get("command", ""))
            for marker in _PROVIDENCE_HOOK_MARKERS
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


def gemini_prompt_submit_hooks(command: str) -> dict[str, list[object]]:
    """Return Gemini hook settings pointing at the generated central hook."""
    return {"BeforeAgent": [{"hooks": [{"type": "command", "command": command}]}]}


def copilot_prompt_submit_hooks(command: str) -> dict[str, object]:
    """Return VS Code / GitHub Copilot agent-hook settings for the central hook."""
    return {
        "hooks": {
            "UserPromptSubmit": [{"type": "command", "command": command, "timeout": 10}]
        }
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
        if "copilot" in self.agents:
            self._write_copilot_adapter()
        return True

    def _write_claude_adapter(self) -> None:
        settings_path = self.output_base / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = self._load_json_object(settings_path)
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        # Merge only our entry under the "UserPromptSubmit" key — other hook
        # event types (e.g. "PreToolUse", written by ai_seeds.generate_claude_seed)
        # and the user's own UserPromptSubmit hooks must survive this write.
        hooks["UserPromptSubmit"] = upsert_hook_entries(
            hooks.get("UserPromptSubmit"),
            claude_user_prompt_submit_hook_entries(self.central_command),
        )
        write_text_utf8(settings_path, json.dumps(settings, indent=2) + "\n")

    def _write_codex_adapter(self) -> None:
        config_path = self.output_base / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        )
        write_text_utf8(config_path, merge_codex_config(existing, self.central_command))

    def _write_gemini_adapter(self) -> None:
        settings_path = self.output_base / ".gemini" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = self._load_json_object(settings_path)
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        hooks["BeforeAgent"] = upsert_hook_entries(
            hooks.get("BeforeAgent"),
            gemini_prompt_submit_hooks(self.central_command)["BeforeAgent"],
        )
        write_text_utf8(settings_path, json.dumps(settings, indent=2) + "\n")

    def _write_copilot_adapter(self) -> None:
        hook_path = self.output_base / COPILOT_HOOK_FILE
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(
            hook_path,
            json.dumps(copilot_prompt_submit_hooks(self.central_command), indent=2)
            + "\n",
        )

    def _load_json_object(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
