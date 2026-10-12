"""Prompt-submit governance hook generation.

The generator lives here; the platform constants, the launcher and the adapter
payloads live in `_hook_platforms`, `_hook_launcher` and `_hook_adapters` and
are re-exported so this module stays the single import surface.
"""

from __future__ import annotations

import json
from pathlib import Path

from providence_core.utils.text_io import write_text_utf8
from providence_wizard.orchestration._hook_adapters import (
    CODEX_BLOCK_BEGIN,
    CODEX_BLOCK_END,
    RETIRED_HOOK_MARKERS,
    claude_prompt_submit_settings,
    claude_user_prompt_submit_hook_entries,
    codex_prompt_submit_config,
    copilot_prompt_submit_hooks,
    devin_prompt_submit_hooks,
    gemini_prompt_submit_hooks,
    is_providence_hook_entry,
    load_json_settings,
    merge_codex_config,
    retired_codex_config_reason,
    upsert_hook_entries,
)
from providence_wizard.orchestration._hook_launcher import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    HOST_LAUNCHER_PYTHON,
    PROMPT_SUBMIT_LAUNCHER,
    PROMPT_SUBMIT_LAUNCHER_POSIX,
    PROMPT_SUBMIT_LAUNCHER_WINDOWS,
    central_prompt_submit_command,
    launcher_command,
)
from providence_wizard.orchestration._hook_platforms import (
    CENTRAL_PROMPT_SUBMIT_HOOK,
    COPILOT_HOOK_FILE,
    DEVIN_HOOK_FILE,
    DEVIN_PROJECT_DIR_ENV,
    HOOK_INTERNAL_TIMEOUT_SECONDS,
    PLATFORM_HOOK_TIMEOUT_SECONDS,
    PLATFORM_NOTICES,
    SUPPORTED_PROMPT_HOOK_AGENTS,
    HookGenerationError,
)
from providence_wizard.orchestration.prompt_submit_hook_script import (
    PROMPT_SUBMIT_HOOK_SCRIPT,
)

__all__ = [
    "CENTRAL_PROMPT_SUBMIT_COMMAND",
    "CENTRAL_PROMPT_SUBMIT_HOOK",
    "CODEX_BLOCK_BEGIN",
    "CODEX_BLOCK_END",
    "COPILOT_HOOK_FILE",
    "DEVIN_HOOK_FILE",
    "DEVIN_PROJECT_DIR_ENV",
    "HOOK_INTERNAL_TIMEOUT_SECONDS",
    "PLATFORM_HOOK_TIMEOUT_SECONDS",
    "PLATFORM_NOTICES",
    "PROMPT_SUBMIT_LAUNCHER",
    "PROMPT_SUBMIT_LAUNCHER_POSIX",
    "PROMPT_SUBMIT_LAUNCHER_WINDOWS",
    "SUPPORTED_PROMPT_HOOK_AGENTS",
    "HookGenerationError",
    "PromptSubmitHookGenerator",
    "central_prompt_submit_command",
    "claude_prompt_submit_settings",
    "claude_user_prompt_submit_hook_entries",
    "codex_prompt_submit_config",
    "copilot_prompt_submit_hooks",
    "devin_prompt_submit_hooks",
    "gemini_prompt_submit_hooks",
    "is_providence_hook_entry",
    "launcher_command",
    "load_json_settings",
    "merge_codex_config",
    "resolve_prompt_submit_hook_agents",
    "retired_codex_config_reason",
    "upsert_hook_entries",
]


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
        self.central_command = central_prompt_submit_command()
        self.devin_command = launcher_command(
            HOST_LAUNCHER_PYTHON, DEVIN_PROJECT_DIR_ENV
        )
        self.notices: list[str] = []

    def generate(self) -> bool:
        """Generate the central hook and configured agent adapters."""
        if not self.agents:
            return False
        self._preflight()
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
        if "devin" in self.agents:
            self._write_devin_adapter()
        self.notices = [
            f"{agent}: {PLATFORM_NOTICES[agent]}"
            for agent in sorted(self.agents)
            if agent in PLATFORM_NOTICES
        ]
        if {"devin", "claude"} <= self.agents:
            self.notices.append(
                f"devin: no {DEVIN_HOOK_FILE.as_posix()} entry is written; Devin "
                "loads .claude/settings.json by default, so a second "
                "registration could run the hook twice per prompt"
            )
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
            json.dumps(copilot_prompt_submit_hooks(), indent=2) + "\n",
        )

    def _write_devin_adapter(self) -> None:
        """Keep exactly one Devin registration of the central hook.

        Devin loads `.claude/settings.json` by default, so when the Claude
        adapter is generated it already reaches Devin; a second entry in
        `.devin/hooks.v1.json` would risk a double run (merge behavior is
        undocumented). Any managed entry left there is removed instead.
        """
        path = self.output_base / DEVIN_HOOK_FILE
        settings = self._load_devin_settings(path)
        existing = settings.get("UserPromptSubmit")
        if "claude" in self.agents:
            if not path.exists():
                return
            kept = (
                [e for e in existing if not is_providence_hook_entry(e)]
                if isinstance(existing, list)
                else existing
            )
            if kept:
                settings["UserPromptSubmit"] = kept
            else:
                settings.pop("UserPromptSubmit", None)
            if settings:
                write_text_utf8(path, json.dumps(settings, indent=2) + "\n")
            else:
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        settings["UserPromptSubmit"] = upsert_hook_entries(
            existing, devin_prompt_submit_hooks(self.devin_command)["UserPromptSubmit"]
        )
        write_text_utf8(path, json.dumps(settings, indent=2) + "\n")

    def _load_devin_settings(self, path: Path) -> dict[str, object]:
        settings = self._load_json_object(path)
        if "hooks" in settings:
            raise HookGenerationError(
                f"{path} uses a 'hooks' wrapper key; .devin/hooks.v1.json takes "
                "the events at its top level (fix or remove it and rerun)"
            )
        return settings

    def _preflight(self) -> None:
        """Validate every selected adapter before anything is written.

        A file that cannot be parsed, or that holds retired input, is the
        user's: generation stops and nothing is created or changed.
        """
        if "claude" in self.agents:
            self._preflight_json(self.output_base / ".claude" / "settings.json")
        if "gemini" in self.agents:
            self._preflight_json(self.output_base / ".gemini" / "settings.json")
        if "devin" in self.agents:
            devin_path = self.output_base / DEVIN_HOOK_FILE
            self._load_devin_settings(devin_path)
            self._preflight_json(devin_path)
        if "codex" in self.agents:
            config_path = self.output_base / ".codex" / "config.toml"
            if config_path.exists():
                reason = retired_codex_config_reason(
                    config_path.read_text(encoding="utf-8")
                )
                if reason is not None:
                    raise HookGenerationError(
                        f"{config_path} {reason}; remove it and rerun the generator"
                    )

    def _preflight_json(self, path: Path) -> None:
        self._load_json_object(path)
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        for marker in RETIRED_HOOK_MARKERS:
            if marker in text:
                raise HookGenerationError(
                    f"{path} references the retired hook {marker!r}; "
                    "remove the entry and rerun the generator"
                )

    def _load_json_object(self, path: Path) -> dict[str, object]:
        return load_json_settings(path)
