"""Module-level helper functions for the interactive wizard flow."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from providence_wizard.orchestration.wizard.models import (
    FinalTemplateConsolidationResult,
)

from ._interactive_wizard_constants import (
    _FINAL_TEMPLATE_AUDIT_FILES,
    _FINAL_TEMPLATE_COMPILED_FILES,
    _FINAL_TEMPLATE_CONTEXT_CACHE_FILE,
    _FINAL_TEMPLATE_MANIFEST_FILE,
)


def _build_phase1_status(
    status: str, reason: str = "", artifacts: list[str] | None = None
) -> dict[str, Any]:
    """Build phase-1 status block persisted to wizard-config.json."""
    return {
        "status": status,
        "reason": reason,
        "artifacts": artifacts or [],
        "updated_at": datetime.now().isoformat(),
    }


def _save_config(output_dir: Path, config_path: Path, config: dict[str, Any]) -> Path:
    """Persist config dict to wizard-config.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return config_path


def _ensure_docs_meta_ready(
    scaffold_ok: bool,
    scaffold_reason: str,
    docs_meta_ready_val: bool,
    source_spec_ready_val: bool,
    client_build_dir: Path,
    paths: dict[str, Any],
) -> tuple[bool, str]:
    """Ensure Phase 1 inputs exist (legacy docs-meta or unified source_spec)."""
    if not scaffold_ok:
        return False, scaffold_reason
    if docs_meta_ready_val or source_spec_ready_val:
        return True, ""
    docs_meta = client_build_dir / "docs-meta"
    source_spec = Path(paths.get("source_spec", client_build_dir / "docs-meta"))
    locations = [str(docs_meta)]
    if source_spec != docs_meta:
        locations.append(str(source_spec))
    return (
        False,
        f"Phase 1 source artifacts are missing at {', '.join(locations)}. "
        "Run 'providence governance compile' to regenerate governance artifacts.",
    )


def _do_consolidate_final_template(
    client_compiled_dir: Path,
    final_template_dir: Path,
    emit: Callable[[str], None],
    consolidate_fn: Callable[..., FinalTemplateConsolidationResult],
) -> FinalTemplateConsolidationResult:
    """Move all compiled artifacts into build/final-template for user handoff."""
    result = consolidate_fn(
        source_dir=client_compiled_dir,
        target_dir=final_template_dir,
        compiled_files=_FINAL_TEMPLATE_COMPILED_FILES,
        audit_files=_FINAL_TEMPLATE_AUDIT_FILES,
        manifest_file=_FINAL_TEMPLATE_MANIFEST_FILE,
        context_cache_relative_file=_FINAL_TEMPLATE_CONTEXT_CACHE_FILE,
    )
    if result["success"]:
        emit(
            f"   Consolidated {result['moved_items']} artifact(s) into {final_template_dir}"
        )
    return result
