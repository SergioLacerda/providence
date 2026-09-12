"""Compile governed selector data and static assets."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ._selector_canonical_fallback import _build_items_from_canonical_docs
from ._selector_dsl_parsing import (
    _load_guidelines_metadata,
    _load_metadata,
    _parse_guideline_dsl_sections,
    _parse_mandate_sections,
)
from ._selector_models import (
    SelectorItem,
    _bool_or_default,
    _list_or_default,
    _now,
    _require_text,
    _text_or_default,
    _validate_dependencies,
    _validate_unique_ids,
    _write_json,
)


@dataclass
class SelectorCompiler:
    """Compile selector payload from governed mandate and guideline sources."""

    repo_root: Path
    asset_source_dir: Path | None = None

    def build_payload(self) -> dict[str, object]:
        """Build the selector payload."""
        items = self._build_items()
        return {
            "version": "1.0",
            "generated_at": _now(),
            "items": [item.to_dict() for item in items],
        }

    def build_site(self, output_dir: Path) -> Path:
        """Write data.json and static assets into a site directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "data.json", self.build_payload())
        self._copy_assets(output_dir)
        return output_dir

    # ------------------------------------------------------------------
    # Item building  primary path then fallback
    # ------------------------------------------------------------------

    def _build_items(self) -> list[SelectorItem]:
        # Primary path: governed .providence artifacts exist
        if self._metadata_path().exists() and self._mandates_path().exists():
            return self._build_items_from_sdd()

        # Fallback: scan docs/spec/canonical/**/*.md directly
        docs_items = _build_items_from_canonical_docs(self.repo_root)
        if docs_items:
            print(
                "[selector_compiler] INFO: .providence artifacts not found  "
                "using docs/spec/canonical fallback. "
                "Run 'providence governance generate' to use compiled artifacts.",
                file=sys.stderr,
            )
            return docs_items

        # Nothing available  emit warning and return empty list
        print(
            f"[selector_compiler] WARN: governance artifacts not found at "
            f"{self.repo_root / '.providence'} and no canonical docs found at "
            f"{self.repo_root / 'docs' / 'spec' / 'canonical'}. "
            "Run 'providence governance generate' to populate. Emitting empty selector.",
            file=sys.stderr,
        )
        return []

    def _build_items_from_sdd(self) -> list[SelectorItem]:
        """Build items from governed .providence artifacts (primary path)."""
        metadata = _load_metadata(self._metadata_path())
        sections = _parse_mandate_sections(self._mandates_path())
        mandate_items = [
            self._build_item(item_id, metadata, sections, "mandate")
            for item_id in metadata
        ]

        guideline_items: list[SelectorItem] = []
        if self._guidelines_path().exists():
            g_metadata = _load_guidelines_metadata(self._guidelines_path())
            g_sections = _parse_guideline_dsl_sections(self._guidelines_path())
            guideline_items = [
                self._build_item(gid, g_metadata, g_sections, "guideline")
                for gid in g_metadata
            ]

        all_items = mandate_items + guideline_items
        _validate_unique_ids(all_items)
        _validate_dependencies(all_items)
        return all_items

    # ------------------------------------------------------------------
    # Item builder (used by primary .providence path)
    # ------------------------------------------------------------------

    def _build_item(
        self,
        item_id: str,
        metadata: dict[str, str],
        sections: dict[str, dict[str, object]],
        item_type: str = "mandate",
    ) -> SelectorItem:
        section = sections.get(item_id)
        if section is None:
            raise ValueError(f"Missing selector section for {item_id}")
        return SelectorItem(
            id=item_id,
            title=metadata[item_id],
            description=_require_text(section.get("description"), item_id),
            category=_text_or_default(section.get("category"), item_type),
            mandatory=_bool_or_default(section.get("mandatory"), True),
            tags=_list_or_default(section.get("tags"), [item_type]),
            depends_on=_list_or_default(section.get("depends_on"), []),
            item_type=item_type,
        )

    # ------------------------------------------------------------------
    # Asset helpers
    # ------------------------------------------------------------------

    def _copy_assets(self, output_dir: Path) -> None:
        asset_dir = self._asset_dir()
        for name in (
            "index.html",
            "selector.js",
            "style.css",
            "site-header.js",
            "site-header.css",
        ):
            shutil.copy2(asset_dir / name, output_dir / name)

    def _asset_dir(self) -> Path:
        if self.asset_source_dir is not None:
            return self.asset_source_dir
        asset_root = (
            resources.files("providence_wizard")
            .joinpath("templates")
            .joinpath("selector")
        )
        return Path(str(asset_root))

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _metadata_path(self) -> Path:
        return self.repo_root / ".providence" / "metadata.json"

    def _mandates_path(self) -> Path:
        return self.repo_root / ".providence" / "source" / "mandates" / "mandates.md"

    def _guidelines_path(self) -> Path:
        return self.repo_root / ".providence" / "source" / "guidelines.dsl"
