"""Workspace-facing helpers for the interactive wizard application layer."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_wizard.orchestration.wizard.phase1_generator import _bundled_spec_dir
from providence_wizard.orchestration.wizard.selector_bridge import (
    load_selector_selection,
)


def load_selector_selection_ids(
    selector_output_path: Path,
    *,
    available_ids: set[str] | None = None,
) -> list[str]:
    """Load selector IDs when an export artifact is present."""
    if not selector_output_path.exists():
        return []
    return load_selector_selection(selector_output_path, available_ids=available_ids)


def build_selector_selection_config(selector_output_path: Path) -> dict[str, Any]:
    """Return selector metadata when an export artifact exists."""
    selected_ids = load_selector_selection_ids(selector_output_path)
    if not selected_ids:
        return {}
    return {
        "selected_ids": selected_ids,
        "resolved_ids": selected_ids,
        "source_path": str(selector_output_path),
    }


def emit_selector_phase1_hint(
    emitter: Any,
    *,
    selector_output_path: Path,
    selector_site_path: Path,
    selector_selection: dict[str, Any],
) -> None:
    """Emit selector discovery guidance without changing phase semantics."""
    if selector_selection:
        resolved = selector_selection.get("resolved_ids", [])
        emitter(
            f"   Loaded selector selection: {len(resolved)} item(s) from {selector_output_path}"
        )
        return
    if selector_site_path.exists():
        emitter(f"    Optional pre-filter available at {selector_site_path}")


def build_selector_discovery_config(
    *,
    selector_output_path: Path,
    selector_site_path: Path,
    selector_selection: dict[str, Any],
) -> dict[str, Any]:
    """Persist selector discovery context for auditability."""
    discovery: dict[str, Any] = {
        "selection_artifact_path": str(selector_output_path),
        "selection_loaded": bool(selector_selection),
    }
    if selector_site_path.exists():
        discovery["published_site_path"] = str(selector_site_path)
    if selector_selection:
        discovery["selected_count"] = len(selector_selection.get("selected_ids", []))
        discovery["resolved_count"] = len(selector_selection.get("resolved_ids", []))
        discovery["source_path"] = selector_selection.get(
            "source_path", str(selector_output_path)
        )
    return discovery


def docs_meta_ready(client_build_dir: Path) -> bool:
    """Return True when legacy docs-meta contains mandate and guideline files."""
    docs_meta = client_build_dir / "docs-meta"
    has_mandate = any(
        (docs_meta / name).exists() for name in ("mandate.spec", "mandate.md")
    )
    has_guidelines = any(
        (docs_meta / name).exists() for name in ("guidelines.dsl", "guidelines.md")
    )
    return has_mandate and has_guidelines


def source_spec_ready(paths: dict[str, Any], client_build_dir: Path) -> bool:
    """Return True when unified source_spec contains mandate and guideline files."""
    source_spec = Path(paths.get("source_spec", client_build_dir / "docs-meta"))
    has_mandate = any(
        (source_spec / name).exists() for name in ("mandate.spec", "mandate.md")
    )
    has_guidelines = any(
        (source_spec / name).exists() for name in ("guidelines.dsl", "guidelines.md")
    )
    return has_mandate and has_guidelines


def ensure_onboarding_scaffold(
    *,
    client_build_dir: Path,
    phase1_choices_dir: Path,
    phase2_input_dir: Path,
    baseline_mandate: str,
    baseline_guidelines: str,
    emit: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Create the minimal scaffold required for first-run onboarding.

    Prefers copying the bundled canonical mandate.spec/guidelines.dsl (shipped as
    providence_core package data) into docs-meta over the single-mandate placeholder
    stub; the stub is a genuine last resort and is logged visibly when used.
    """
    emit = emit or print
    try:
        client_build_dir.mkdir(parents=True, exist_ok=True)
        phase1_choices_dir.mkdir(parents=True, exist_ok=True)
        phase2_input_dir.mkdir(parents=True, exist_ok=True)
        docs_meta = client_build_dir / "docs-meta"
        docs_meta.mkdir(parents=True, exist_ok=True)
        bundled = _bundled_spec_dir()

        mandate_missing = not any(
            (docs_meta / name).exists() for name in ("mandate.spec", "mandate.md")
        )
        if mandate_missing and bundled and (bundled / "mandate.spec").exists():
            shutil.copyfile(bundled / "mandate.spec", docs_meta / "mandate.spec")
            mandate_missing = False
        if mandate_missing:
            emit(
                "WARN: canonical governance spec not found; generating minimal "
                "placeholder mandate.md  customize before production use"
            )
            (docs_meta / "mandate.md").write_text(baseline_mandate, encoding="utf-8")

        guidelines_missing = not any(
            (docs_meta / name).exists() for name in ("guidelines.dsl", "guidelines.md")
        )
        if guidelines_missing and bundled and (bundled / "guidelines.dsl").exists():
            shutil.copyfile(bundled / "guidelines.dsl", docs_meta / "guidelines.dsl")
            guidelines_missing = False
        if guidelines_missing:
            emit(
                "WARN: canonical governance spec not found; generating minimal "
                "placeholder guidelines.dsl  customize before production use"
            )
            (docs_meta / "guidelines.dsl").write_text(
                baseline_guidelines,
                encoding="utf-8",
            )
        return True, ""
    except OSError as exc:
        return False, f"Failed to create onboarding scaffold: {exc}"


def ensure_docs_meta_ready(
    *,
    paths: dict[str, Any],
    client_build_dir: Path,
    phase1_choices_dir: Path,
    phase2_input_dir: Path,
    baseline_mandate: str,
    baseline_guidelines: str,
) -> tuple[bool, str]:
    """Ensure Phase 1 inputs exist in docs-meta or unified source_spec."""
    scaffold_ok, scaffold_reason = ensure_onboarding_scaffold(
        client_build_dir=client_build_dir,
        phase1_choices_dir=phase1_choices_dir,
        phase2_input_dir=phase2_input_dir,
        baseline_mandate=baseline_mandate,
        baseline_guidelines=baseline_guidelines,
    )
    if not scaffold_ok:
        return False, scaffold_reason
    if docs_meta_ready(client_build_dir) or source_spec_ready(paths, client_build_dir):
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


def _display_cleaned_path(path: Path, *, repo_root: Path) -> str:
    """Return a repo-relative cleanup path when possible, otherwise absolute."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def cleanup_post_generation_artifacts(
    *,
    repo_root: Path,
    client_build_dir: Path,
    client_compiled_dir: Path,
    final_template_dir: Path,
    wizard_config_path: Path,
    temp_build_dirs: tuple[str, ...],
    temp_compiled_dirs: tuple[str, ...],
) -> list[str]:
    """Remove wizard temporary artifacts while preserving final-template."""
    cleaned: list[str] = []
    candidates: list[Path] = []
    candidates.extend(client_build_dir / name for name in temp_build_dirs)
    candidates.append(wizard_config_path)
    candidates.extend(client_compiled_dir / name for name in temp_compiled_dirs)
    for path in candidates:
        if path == final_template_dir or final_template_dir in path.parents:
            continue
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            cleaned.append(_display_cleaned_path(path, repo_root=repo_root))
        except OSError:
            continue
    return cleaned
