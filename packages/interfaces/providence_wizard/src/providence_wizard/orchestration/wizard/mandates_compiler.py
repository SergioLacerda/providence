"""Mandates source-file compiler for Phase 3 output."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


class MandatesCompiler:
    """Write the AI-optimised mandates.md source file."""

    def __init__(
        self,
        output_path: Path,
        language: str = "Python",
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._output_path = output_path
        self._language = language
        self._emit = emitter or print

    def write(self, mandates: list[dict[str, Any]]) -> bool:
        """Generate mandates.md under output_path/source/mandates/."""
        try:
            mandates_dir = self._output_path / "source" / "mandates"
            mandates_dir.mkdir(parents=True, exist_ok=True)

            lines = [
                "# Mandates - SDD v3.0",
                "",
                " IA-FIRST DESIGN NOTICE",
                "- **Status**: Architecture-level governance rules",
                "- **Optimization**: Optimized for AI agent parsing",
                "- **Version**: 3.0",
                f"- **Language**: {self._language}",
                f"- **Generated**: {datetime.now().isoformat()}",
                "",
                "## Core Mandates",
                "",
                "Mandatory rules that CANNOT be customized or skipped.",
                "",
            ]

            for mandate in mandates:
                description = (
                    mandate.get("description")
                    or mandate.get("content")
                    or mandate.get("summary_runtime")
                    or mandate.get("summary_minimal")
                    or "No description available"
                )
                lines += [
                    f"## {mandate['id']}: {mandate['title']}",
                    "",
                    f"**Criticality**: {mandate.get('criticality', 'MANDATORY')}",
                    "**Customizable**: No",
                    "",
                    description,
                    "",
                ]

            (mandates_dir / "mandates.md").write_text(
                "\n".join(lines), encoding="utf-8"
            )
            return True
        except Exception as exc:
            self._emit(f"   Error generating mandates.md: {exc}")
            traceback.print_exc()
            return False
