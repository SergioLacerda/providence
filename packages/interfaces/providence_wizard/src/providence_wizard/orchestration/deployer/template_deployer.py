"""TemplateDeployer  copy IDE/CI config templates to the output directory."""

from __future__ import annotations

import contextlib
import os
import shutil
from importlib import resources
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger
from providence_wizard.constants import RUNTIME_DIRNAME

from ..wizard.seedling_catalog import resolve_selection

logger = get_logger(__name__)


class TemplateDeployer:
    """Copy IDE config templates from providence_integration to the output directory."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        config: dict[str, Any] | None = None,
        verbose: bool = False,
        selected_seedlings: set[str] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.output_base = output_base
        self.config = config or {}
        self.verbose = verbose
        self.selection = resolve_selection(selected_seedlings)

        if os.environ.get("SDD_TEST_OUTPUT_DIR"):
            with contextlib.suppress(OSError, ValueError):
                if self.output_base.resolve() == self.repo_root.resolve():
                    msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                    print(f"   {msg}")  # noqa: T201
                    raise PermissionError(msg)

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    @property
    def _template_base(self) -> Path:
        for candidate in self._template_base_candidates():
            if candidate.exists():
                return candidate
        return self._template_base_candidates()[-1]

    def _resolve_template_path(self, relative_path: Path) -> Path | None:
        """Return the first template candidate that contains the requested path."""
        for candidate in self._template_base_candidates():
            path = candidate / relative_path
            if path.exists():
                return path
        return None

    def _template_base_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        with contextlib.suppress(ModuleNotFoundError, TypeError, AttributeError):
            pkg_root = resources.files("providence_integration")
            candidates.append(Path(str(pkg_root)) / "templates")
        candidates.append(
            self.repo_root
            / "packages"
            / "features"
            / "providence_integration"
            / "src"
            / "providence_integration"
            / "templates"
        )
        candidates.append(
            Path(__file__).resolve().parent.parent.parent
            / "templates"
            / "bootstrap-fallback"
        )
        return candidates

    def _ci_enabled(self) -> bool:
        return "ci" in self.selection

    def _ensure_cursor_rule_aliases(self) -> None:
        cursor_rules_dir = self.output_base / ".cursor" / "rules"
        spec_file = cursor_rules_dir / "spec.mdc"
        governance_file = cursor_rules_dir / "sdd-governance.mdc"
        if spec_file.exists() and not governance_file.exists():
            shutil.copy2(spec_file, governance_file)
            self._log("Created Cursor governance alias from spec.mdc")
        elif governance_file.exists() and not spec_file.exists():
            shutil.copy2(governance_file, spec_file)
            self._log("Created Cursor spec alias from sdd-governance.mdc")

    def _prune_github_dir(self, github_dir: Path) -> None:
        """Remove `.github` artifacts belonging to options that were not selected."""
        if "copilot" not in self.selection:
            copilot_file = github_dir / "copilot-instructions.md"
            if copilot_file.exists():
                copilot_file.unlink()
        if not self._ci_enabled():
            workflow_file = github_dir / "workflows" / "sdd-validation.yml"
            if workflow_file.exists():
                workflow_file.unlink()

    def copy_templates(self) -> bool:
        """Copy base templates to .github/workflows (only when `ci` is selected)."""
        self._log("Copying templates")
        try:
            if not self._ci_enabled():
                self._log("Skipping sdd-validation.yml: `ci` not selected")
                return True
            workflow_rel = Path(".github") / "workflows" / "sdd-validation.yml"
            src_workflow = self._resolve_template_path(workflow_rel)
            dst_workflow = (
                self.output_base / ".github" / "workflows" / "sdd-validation.yml"
            )
            dst_workflow.parent.mkdir(parents=True, exist_ok=True)
            if src_workflow is not None:
                shutil.copy2(src_workflow, dst_workflow)
                self._log("Copied sdd-validation.yml to .github/workflows/")
            else:
                self._log(f"Template not found: {workflow_rel}")
            return True
        except Exception as e:
            print(f"   Failed to copy templates: {e}")  # noqa: T201
            return False

    def create_ide_templates(self) -> bool:  # noqa: C901
        """Copy configuration templates from providence_integration to output directory."""
        self._log("Copying IDE templates and project files")
        try:
            template_base = self._template_base
            if not template_base.exists():
                attempted = ", ".join(
                    str(path) for path in self._template_base_candidates()
                )
                print(f"   Template base not found: {template_base}")  # noqa: T201
                self._log(f"Attempted template bases: {attempted}")
                return False

            copied_count = 0
            github_needed = "copilot" in self.selection or self._ci_enabled()
            dir_mappings: list[tuple[Path, Path, bool]] = [
                (
                    template_base / ".github",
                    self.output_base / ".github",
                    github_needed,
                ),
                (
                    template_base / ".vscode",
                    self.output_base / ".vscode",
                    "vscode" in self.selection,
                ),
                (
                    template_base / ".cursor",
                    self.output_base / ".cursor",
                    "cursor" in self.selection,
                ),
                (
                    template_base / ".claude",
                    self.output_base / ".claude",
                    "claude" in self.selection,
                ),
                (
                    template_base / ".gemini",
                    self.output_base / ".gemini",
                    "gemini" in self.selection or "antigravity" in self.selection,
                ),
                (
                    template_base / ".providence" / "templates",
                    self.output_base / RUNTIME_DIRNAME / "templates",
                    True,
                ),
            ]

            missing_needed: list[str] = []
            for src, dst, needed in dir_mappings:
                if not needed:
                    self._log(f"Skipping {src.name}/: not selected")
                    continue
                try:
                    source = self._resolve_template_path(src.relative_to(template_base))
                    if source is not None and source.is_dir():
                        shutil.copytree(source, dst, dirs_exist_ok=True)
                        if dst == self.output_base / ".github":
                            self._prune_github_dir(dst)
                        self._log(f"Copied {source.name}/ directory")
                        copied_count += 1
                    else:
                        missing_needed.append(src.name)
                        print(  # noqa: T201
                            f"   Required template directory not found: {src.name}/"
                        )
                except Exception as e:
                    missing_needed.append(src.name)
                    print(f"   Failed to copy {src.name}/: {e}")  # noqa: T201

            if missing_needed:
                return False

            if copied_count == 0:
                print("   No template files were copied")  # noqa: T201
                return False

            self._ensure_cursor_rule_aliases()
            self._log(f"Copied {copied_count} configuration files and project files")
            return True
        except Exception as e:
            print(f"   Failed to copy IDE templates: {e}")  # noqa: T201
            import traceback

            traceback.print_exc()
            return False
