"""Bootstrap PHASE 1 source specs in clean environments."""

import logging
import re
from collections.abc import Callable
from pathlib import Path

from providence_core.governance._bootstrap_guidelines import (
    UNIVERSAL_LANGUAGE_GUIDELINES,
)

logger = logging.getLogger(__name__)


class SourceSpecBootstrapper:
    """Bootstraps governance source specs in clean environments."""

    def __init__(
        self,
        spec_path: Path,
        repo_root: Path,
        emit: Callable[[str], None] | None = None,
    ):
        """
        Initialize bootstrapper.

        Args:
            spec_path: Path to source spec directory.
            repo_root: Root of the repository.
            emit: Optional callback for status messages.
        """
        self.spec = spec_path
        self.repo_root = repo_root
        self._emit = emit

    def _out(self, message: str) -> None:
        """Emit status message via logger and optional callback."""
        logger.info(message)
        if self._emit is not None:
            self._emit(message)

    def has_source_specs(self) -> bool:
        """Return True when PHASE 1 source files are available."""
        return any(
            (self.spec / name).exists() for name in ("mandate.spec", "mandate.md")
        )

    def bootstrap(self) -> None:
        """
        Best-effort bootstrap for source specs in clean environments.

        Falls back to lightweight extraction from docs markdown when source
        specs are missing (e.g., CI, Docker, fresh clone).
        """
        if self.has_source_specs():
            return

        self.spec.mkdir(parents=True, exist_ok=True)
        self._bootstrap_from_markdown()

    def _extract_canonical_titles(self) -> dict[str, str]:
        """Extract canonical mandate titles from `docs/spec/canonical/`."""
        canonical_root = self.repo_root / "docs" / "spec" / "canonical"
        title_map: dict[str, str] = {}
        if not canonical_root.exists():
            return title_map
        id_pattern = re.compile(r"^\*\*ID:\*\*\s*(M\d{3})", re.MULTILINE)
        title_pattern = re.compile(r"^#\s+(?:Mandate:)?\s*(.+)$", re.MULTILINE)
        for md_file in sorted(canonical_root.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # nosec B112
                continue
            id_match = id_pattern.search(content)
            title_match = title_pattern.search(content)
            if id_match and title_match:
                mid = id_match.group(1)
                title = title_match.group(1).strip()
                if mid not in title_map:
                    title_map[mid] = title
        return title_map

    def _bootstrap_from_markdown(self) -> None:
        """Generate `mandate.md` from canonical docs when available, and always
        seed the `guidelines.dsl` fallback.

        `guidelines.dsl`'s content (`UNIVERSAL_LANGUAGE_GUIDELINES`) is a fixed
        constant, independent of whether a `docs/` tree exists — it must not be
        gated behind the same `docs_root`/mandate-scan precondition that
        `mandate.md` depends on. A client workspace (no `docs/` directory,
        e.g. a real standalone install) never has that tree, which previously
        made this method a permanent no-op there and left client governance
        compiled with zero guideline items.
        """
        guidelines_dsl = self.spec / "guidelines.dsl"
        if not guidelines_dsl.exists():
            guidelines_dsl.write_text(UNIVERSAL_LANGUAGE_GUIDELINES, encoding="utf-8")

        docs_root = self.repo_root / "docs"
        if not docs_root.exists():
            return

        canonical_titles = self._extract_canonical_titles()
        mandate_ids = set(canonical_titles.keys())

        if not mandate_ids:
            return

        # A wizard-deployed `mandates/mandates.md` is already a correct,
        # non-leaked source for this workspace's own core items. Writing a
        # top-level `mandate.md` here is unnecessary and, under
        # a repo_root that resolved to an unrelated checkout (e.g. an
        # editable/dev install of providence-cli initializing a separate client
        # project), would leak that checkout's own mandate titles into this
        # workspace instead.
        if (self.spec / "mandates" / "mandates.md").exists():
            return

        mandate_md = self.spec / "mandate.md"
        if not mandate_md.exists():
            lines = ["# Mandates - SDD v3.0", ""]
            for mandate_id in sorted(mandate_ids):
                title = canonical_titles.get(mandate_id, mandate_id)
                lines.append(f"## {mandate_id}: {title}")
                lines.append("")
            mandate_md.write_text("\n".join(lines), encoding="utf-8")

        if self.has_source_specs():
            self._out("  ℹ️  Bootstrapped docs-meta from markdown scan")
