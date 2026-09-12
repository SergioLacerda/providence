"""
OutputValidator  Phase 6 step: verify the generated output structure is complete.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    CENTRAL_PROMPT_SUBMIT_HOOK,
    SUPPORTED_PROMPT_HOOK_AGENTS,
)
from .wizard.models import ValidationDetail
from .wizard.seedling_catalog import resolve_selection


class OutputValidator:
    """Validate that all expected files and directories were produced."""

    def __init__(
        self,
        output_base: Path,
        sdd_dir: Path,
        source_dir: Path,
        runtime_dir: Path,
        mandates_dir: Path,
        guidelines_dir: Path,
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any] | None = None,
        verbose: bool = False,
        emitter: Callable[[str], None] | None = None,
        selected_seedlings: set[str] | None = None,
    ) -> None:
        self.output_base = output_base
        self.providence_dir = sdd_dir
        self.source_dir = source_dir
        self.runtime_dir = runtime_dir
        self.mandates_dir = mandates_dir
        self.guidelines_dir = guidelines_dir
        self.guidelines_by_category = guidelines_by_category
        self.config = config or {}
        self.verbose = verbose
        self._emit = emitter or print
        self.selection = resolve_selection(selected_seedlings)

    def _log(self, message: str) -> None:
        if self.verbose:
            self._emit(f"    {message}")

    def _path_exists(self, path: Path) -> bool:
        return path.exists()

    def _cursor_rules_exist(self) -> bool:
        cursor_rules_dir = self.output_base / ".cursor" / "rules"
        return any(
            self._path_exists(cursor_rules_dir / filename)
            for filename in ("spec.mdc", "sdd-governance.mdc")
        )

    def _ci_enabled(self) -> bool:
        """Return whether the CI/CD workflow artifact is required."""
        return "ci" in self.selection

    def _prompt_submit_hooks_enabled(self) -> bool:
        """Return whether prompt-submit governance hooks are required."""
        return self.config.get("handshake_mode") == "hook"

    def _prompt_submit_hook_agents(self) -> set[str]:
        configured = self.config.get("prompt_submit_hook_agents")
        if isinstance(configured, list):
            return {
                str(agent)
                for agent in configured
                if str(agent) in SUPPORTED_PROMPT_HOOK_AGENTS
            }
        return set(SUPPORTED_PROMPT_HOOK_AGENTS)

    def _validate_prompt_submit_hook_files(self, result: ValidationDetail) -> None:
        """Validate prompt-submit hook artifacts when handshake_mode=hook."""
        if not self._prompt_submit_hooks_enabled():
            return
        hook_files = [(self.output_base / CENTRAL_PROMPT_SUBMIT_HOOK, "central hook")]
        agents = self._prompt_submit_hook_agents()
        if "claude" in agents:
            hook_files.append(
                (self.output_base / ".claude" / "settings.json", "Claude adapter")
            )
        if "codex" in agents:
            hook_files.append(
                (self.output_base / ".codex" / "config.toml", "Codex adapter")
            )
        if "gemini" in agents:
            hook_files.append(
                (self.output_base / ".gemini" / "settings.json", "Gemini adapter")
            )
        for hook_file, desc in hook_files:
            exists = self._path_exists(hook_file)
            result["checks"][f"hook: {desc}"] = "OK" if exists else "MISSING"
            if not exists:
                result["valid"] = False
                result["errors"].append(
                    f"Missing handshake_mode=hook file: {hook_file}"
                )
                continue
            if desc != "central hook" and CENTRAL_PROMPT_SUBMIT_COMMAND not in (
                hook_file.read_text(encoding="utf-8")
            ):
                result["valid"] = False
                result["checks"][f"hook command: {desc}"] = "MISSING"
                result["errors"].append(
                    f"Missing central prompt-submit command in: {hook_file}"
                )

    def _required_dirs(self) -> list[Path]:
        """Return the directories required for the current selection."""
        required_dirs = [self.mandates_dir, self.guidelines_dir, self.runtime_dir]
        if self._ci_enabled():
            required_dirs.append(self.output_base / ".github" / "workflows")
        return required_dirs

    def _selected_required_files(self) -> list[tuple[Path, str]]:
        """Return the (path, description) pairs required for the current selection."""
        required_files = [
            (self.mandates_dir / "mandates.md", "Mandates"),
            (self.runtime_dir / "README.md", "Runtime README"),
            (self.source_dir / "README.md", "Source README"),
            (self.providence_dir / "metadata.json", "Metadata"),
        ]
        by_selection: list[tuple[str, Path, str]] = [
            (
                "copilot",
                self.output_base / ".github" / "copilot-instructions.md",
                "Copilot Instructions",
            ),
            (
                "vscode",
                self.output_base / ".vscode" / "ai-rules.md",
                "VS Code AI Rules",
            ),
            (
                "claude",
                self.output_base / ".claude" / "claude-instructions.md",
                "Claude Instructions",
            ),
            (
                "gemini",
                self.output_base / ".gemini" / "gemini-instructions.md",
                "Gemini Instructions",
            ),
            (
                "antigravity",
                self.output_base
                / ".gemini"
                / "antigravity"
                / "antigravity-instructions.md",
                "Antigravity Instructions",
            ),
        ]
        required_files.extend(
            (path, desc) for key, path, desc in by_selection if key in self.selection
        )
        return required_files

    def _validate_paths(
        self,
        result: ValidationDetail,
        paths: list[Path],
        label: str,
    ) -> None:
        """Check a batch of required directories, recording checks/errors."""
        for req_dir in paths:
            exists = req_dir.exists()
            result["checks"][str(req_dir.relative_to(self.output_base))] = (
                "OK" if exists else "MISSING"
            )
            if not exists:
                result["valid"] = False
                result["errors"].append(f"Missing {label}: {req_dir}")

    def _validate_files(self, result: ValidationDetail) -> None:
        """Check required files for the current selection, recording checks/errors."""
        for req_file, desc in self._selected_required_files():
            exists = self._path_exists(req_file)
            result["checks"][f"file: {desc}"] = "OK" if exists else "MISSING"
            if not exists:
                result["valid"] = False
                result["errors"].append(f"Missing file: {req_file}")

    def _validate_cursor_rules(self, result: ValidationDetail) -> None:
        """Check Cursor rule files only when `cursor` is selected."""
        if "cursor" not in self.selection:
            return
        cursor_rules_ok = self._cursor_rules_exist()
        result["checks"]["file: Cursor Rules"] = "OK" if cursor_rules_ok else "MISSING"
        if not cursor_rules_ok:
            result["valid"] = False
            result["errors"].append(
                "Missing file: expected one of "
                f"{self.output_base / '.cursor' / 'rules' / 'spec.mdc'} or "
                f"{self.output_base / '.cursor' / 'rules' / 'sdd-governance.mdc'}"
            )

    def _validate_guidelines(self, result: ValidationDetail) -> None:
        """Check that every active guideline category has a compiled file."""
        for category in self.guidelines_by_category:
            guideline_file = self.guidelines_dir / f"{category}.md"
            exists = guideline_file.exists()
            result["checks"][f"guideline: {category}"] = "OK" if exists else "MISSING"
            if not exists:
                result["valid"] = False
                result["errors"].append(f"Missing guideline: {guideline_file}")

    def validate(self) -> tuple[bool, ValidationDetail]:
        """Return (is_valid, detail_dict) after checking all required paths."""
        self._log("Validating output structure")
        result: ValidationDetail = {"valid": True, "checks": {}, "errors": []}

        try:
            self._validate_paths(result, self._required_dirs(), "directory")
            self._validate_files(result)
            self._validate_cursor_rules(result)
            self._validate_prompt_submit_hook_files(result)
            self._validate_guidelines(result)
            return result["valid"], result
        except Exception as e:
            self._emit(f"   Validation failed: {e}")
            result["valid"] = False
            result["errors"].append(str(e))
            return False, result
