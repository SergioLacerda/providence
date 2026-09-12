"""Phase 4 governance input resolution and loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .phase4_governance_loader import GovernanceLoader
from .wizard.models import Phase456RunResult


def _resolve_governance_inputs(
    repo_root: Path, paths: dict[str, Any], output_base: Path
) -> tuple[Path, Path]:
    """Resolve governance input files with .providence-first precedence."""
    core_candidates = [
        repo_root / ".providence" / "compiled" / "governance-core.json",
        repo_root / ".providence" / "source" / "governance-core.json",
        paths["client_compiled"] / "source" / "governance-core.json",
        output_base / ".providence" / "source" / "governance-core.json",
    ]
    client_candidates = [
        repo_root / ".providence" / "compiled" / "governance-client.json",
        repo_root / ".providence" / "source" / "governance-client.json",
        paths["client_compiled"] / "source" / "governance-client.json",
        output_base / ".providence" / "source" / "governance-client.json",
    ]
    core_path = next((p for p in core_candidates if p.exists()), core_candidates[0])
    client_path = next(
        (p for p in client_candidates if p.exists()), client_candidates[0]
    )
    return core_path, client_path


def _load_governance(
    core_path: Path,
    client_path: Path,
    verbose: bool,
    sdd_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    Phase456RunResult,
]:
    """Load governance data (Phase 4)."""
    loader = GovernanceLoader(
        governance_core_path=core_path,
        governance_client_path=client_path,
        verbose=verbose,
    )
    result: Phase456RunResult = {
        "success": False,
        "phase": "Phase 4-6",
        "output_path": str(sdd_dir),
        "mandates": 0,
        "guidelines": 0,
        "categories": [],
        "errors": [],
    }
    if not loader.load():
        result["errors"].append("Failed to load governance")
        return [], {}, {}, result
    return loader.mandates, loader.guidelines, loader.guidelines_by_category, result
