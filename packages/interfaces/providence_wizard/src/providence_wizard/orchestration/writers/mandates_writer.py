"""MandatesWriter  generates .providence/source/mandates/mandates.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

from ..language_policy import resolve_language_policy

logger = get_logger(__name__)


class MandatesWriter:
    """Write mandates.md to the mandates output directory."""

    def __init__(
        self,
        mandates_dir: Path,
        mandates: list[dict[str, Any]],
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self._mandates_dir = mandates_dir
        self._mandates = mandates
        self._config = config
        self._verbose = verbose

    def _log(self, message: str) -> None:
        if self._verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def _render_m011_policy_summary(self) -> str:
        policy = resolve_language_policy(self._config)
        mandatory = ", ".join(policy["mandatory_surfaces"])
        contextual = ", ".join(policy["contextual_surfaces"])
        guidelines = ", ".join(policy["guideline_anchors"])
        local_paths = ", ".join(policy["workspace_local_docs_paths"])
        return (
            "\n**Mandatory surfaces**: "
            f"{mandatory}\n\n"
            "**Contextual surfaces**: "
            f"{contextual}\n\n"
            "**Context source**: wizard `language_context` preferences guide "
            "contextual surfaces only and never override M011.\n\n"
            "**Workspace-local docs paths**: "
            f"{local_paths}\n\n"
            "**Guideline anchors**: "
            f"{guidelines}\n\n"
        )

    def generate(self) -> bool:
        """Write mandates.md; return True on success."""
        self._log("Generating mandates.md")
        try:
            mandates_file = self._mandates_dir / "mandates.md"
            content = f"""# Mandates - SDD v3.0

 IA-FIRST DESIGN NOTICE
- **Status**: Architecture-level governance rules
- **Optimization**: Optimized for AI agent parsing
- **Version**: 3.0
- **Generated**: {datetime.now().isoformat()}

## Core Mandates

Mandatory rules that CANNOT be customized or skipped.

"""
            for mandate in self._mandates:
                mandate_id = mandate.get("id", "M000")
                mandate_title = mandate.get("title") or f"Mandate {mandate_id}"
                description = (
                    mandate.get("content")
                    or mandate.get("description")
                    or mandate.get("summary_runtime")
                    or mandate.get("summary_minimal")
                    or "No description available"
                )
                content += f"""## {mandate_id}: {mandate_title}

**Criticality**: {mandate.get("criticality", "MANDATORY")}
**Customizable**: No

{description}

"""
                if mandate_id == "M011":
                    content += self._render_m011_policy_summary()
            with open(mandates_file, "w", encoding="utf-8") as f:
                f.write(content)
            self._log(f"Generated mandates.md ({len(self._mandates)} mandates)")
            return True
        except Exception as e:
            print(f"   Failed to generate mandates.md: {e}")  # noqa: T201
            return False
