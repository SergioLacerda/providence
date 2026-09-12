"""SeedlingInjector  inject governance metadata into deployed bootstrap files."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

logger = get_logger(__name__)


class SeedlingInjector:
    """Inject governance fingerprint/metadata into IDE bootstrap files."""

    def __init__(
        self,
        repo_root: Path,
        output_base: Path,
        verbose: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.output_base = output_base
        self.verbose = verbose

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def _isolation_guard(self) -> None:
        """Raise PermissionError if output_base points to the actual repo root during tests."""
        test_output_dir = os.environ.get("SDD_TEST_OUTPUT_DIR")
        if not test_output_dir:
            return
        with contextlib.suppress(OSError, ValueError):
            if self.output_base.resolve() == self.repo_root.resolve():
                msg = f"SDD_ISOLATION_ERROR: Mutation of repo root blocked ({self.output_base})"
                print(f"   {msg}")  # noqa: T201
                raise PermissionError(msg)

    def inject_bootstrap_metadata(
        self,
        fingerprint: str,
        generated_at: str,
        mandates_count: int,
    ) -> None:
        """Append governance fingerprint block to generated bootstrap markdown files."""
        self._isolation_guard()
        footer = (
            "\n\n<!-- sdd:bootstrap-metadata\n"
            f"governance_fingerprint : {fingerprint}\n"
            f"mandates_count         : {mandates_count}\n"
            f"generated_at           : {generated_at}\n"
            "load_compiled_from     : .providence\n"
            "-->"
        )
        bootstrap_files = [
            self.output_base / ".github" / "copilot-instructions.md",
            self.output_base / ".vscode" / "ai-rules.md",
            self.output_base / ".claude" / "claude-instructions.md",
            self.output_base
            / ".gemini"
            / "antigravity"
            / "antigravity-instructions.md",
            self.output_base / ".ia" / "ia-instructions.md",
            self.output_base / ".ai" / "ai-instructions.md",
        ]
        injected = 0
        for path in bootstrap_files:
            try:
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8")
                if "sdd:bootstrap-metadata" in content:
                    continue
                path.write_text(content + footer, encoding="utf-8")
                injected += 1
            except Exception as e:
                self._log(f"  Failed to inject metadata into {path.name}: {e}")
        if injected:
            self._log(f"Injected governance metadata into {injected} bootstrap files")

    def populate_ide_rules(
        self,
        mandates: list[dict[str, Any]],
        fingerprint: str,
    ) -> None:
        """Populate IDE rule files with governance fingerprint and mandate count."""
        ide_rule_files = [
            self.output_base / ".vscode" / "ai-rules.md",
            self.output_base / ".cursor" / "rules" / "sdd-governance.mdc",
        ]
        for rules_file in ide_rule_files:
            if not rules_file.exists():
                continue
            try:
                content = rules_file.read_text(encoding="utf-8")
                content = content.replace("{FINGERPRINT}", fingerprint)
                content = content.replace("{MANDATES_COUNT}", str(len(mandates)))
                rules_file.write_text(content, encoding="utf-8")
                self._log(
                    f"Populated {rules_file.name} with fingerprint + mandate count"
                )
            except Exception as e:
                self._log(f"  Failed to populate {rules_file.name}: {e}")
