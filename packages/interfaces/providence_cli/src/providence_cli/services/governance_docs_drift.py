"""Docs-source registry validation: drift detection against runtime outputs.

Split out of `governance_docs_sources.py` (T7,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.services.governance_docs_sources import (
    DEFAULT_HANDBOOK_DIR,
    DEFAULT_REGISTRY,
    DocsSourceReport,
    _active,
    _collect_active_source_ids,
    _load_runtime_ids,
    _load_yaml,
    _metadata_mandate_ids,
    _source_entries,
)


def _source_output_path(output: object) -> Path | None:
    raw = str(output).replace("\\", "/")
    if not raw.startswith(".providence/source/"):
        return None
    return Path(*raw.split("/"))


def _display_path(path: Path) -> str:
    return path.as_posix()


def _append_id_drift_error(
    errors: list[str],
    *,
    label: str,
    registry_ids: set[str],
    runtime_ids: set[str],
) -> None:
    if runtime_ids and registry_ids != runtime_ids:
        errors.append(
            f"{label}: "
            f"missing={sorted(runtime_ids - registry_ids)} "
            f"extra={sorted(registry_ids - runtime_ids)}"
        )


def _declared_handbook_outputs(entries: list[dict[str, Any]]) -> set[Path]:
    outputs: set[Path] = set()
    for entry in entries:
        if str(entry.get("type", "")).lower() != "handbook" or not _active(entry):
            continue
        outputs.add(DEFAULT_HANDBOOK_DIR / "index.yaml")
        for output in entry.get("outputs", []):
            output_path = _source_output_path(output)
            if output_path is not None and output_path.as_posix().startswith(
                ".providence/source/handbook/"
            ):
                outputs.add(output_path)
    return outputs


def _declared_readable_source_outputs(entries: list[dict[str, Any]]) -> set[Path]:
    outputs: set[Path] = set()
    for entry in entries:
        if str(entry.get("type", "")).lower() == "handbook" and _active(entry):
            outputs.add(DEFAULT_HANDBOOK_DIR / "index.yaml")
        for output in entry.get("outputs", []):
            output_path = _source_output_path(output)
            if output_path is not None:
                outputs.add(output_path)
    return outputs


def _append_handbook_output_drift(
    root: Path, entries: list[dict[str, Any]], errors: list[str], warnings: list[str]
) -> None:
    declared = _declared_handbook_outputs(entries)
    for output in sorted(declared):
        if not (root / output).exists():
            errors.append(f"handbook runtime output missing: {_display_path(output)}")

    handbook_root = root / DEFAULT_HANDBOOK_DIR
    if not handbook_root.exists():
        return
    actual = {
        path.relative_to(root)
        for path in handbook_root.rglob("*.yaml")
        if path.is_file()
    }
    for output in sorted(actual - declared):
        warnings.append(
            f"stale handbook runtime output is not declared: {_display_path(output)}"
        )


def _append_readable_source_output_drift(
    root: Path, entries: list[dict[str, Any]], warnings: list[str]
) -> None:
    source_root = root / ".providence" / "source"
    if not source_root.exists():
        return
    declared = _declared_readable_source_outputs(entries)
    actual = {
        path.relative_to(root)
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix != ".sig"
    }
    for output in sorted(declared - actual):
        warnings.append(
            f"declared readable runtime output missing: {_display_path(output)}"
        )
    for output in sorted(actual - declared):
        warnings.append(
            f"stale readable runtime output is not declared: {_display_path(output)}"
        )


def validate_governance_sources(
    root: Path, registry_path: Path | None = None
) -> DocsSourceReport:
    """Validate docs-source registry and compare active IDs with runtime output."""
    registry_file = root / (registry_path or DEFAULT_REGISTRY)
    errors: list[str] = []
    warnings: list[str] = []
    if not registry_file.exists():
        return DocsSourceReport(
            False, [f"missing registry: {registry_file}"], [], [], [], []
        )

    registry = _load_yaml(registry_file)
    entries = _source_entries(registry)
    if str(registry.get("schema_version")) != "1":
        errors.append("governance source registry schema_version must be '1'")

    mandate_seen, guideline_seen, handbook_ids = _collect_active_source_ids(
        root, entries, errors, warnings
    )

    registry_mandates = set(mandate_seen)
    registry_guidelines = set(guideline_seen)
    registry_handbooks = set(handbook_ids)
    metadata_mandates = _metadata_mandate_ids(root)
    compiled_mandates = _load_runtime_ids(
        root, ".providence/compiled/governance-core.json", "MANDATE"
    )
    compiled_guidelines = _load_runtime_ids(
        root, ".providence/compiled/governance-client.json", "GUIDELINE"
    )

    _append_id_drift_error(
        errors,
        label="mandate registry drift vs .providence/metadata.json",
        registry_ids=registry_mandates,
        runtime_ids=metadata_mandates,
    )
    _append_id_drift_error(
        errors,
        label="mandate registry drift vs compiled governance-core.json",
        registry_ids=registry_mandates,
        runtime_ids=compiled_mandates,
    )
    _append_id_drift_error(
        errors,
        label="guideline registry drift vs compiled governance-client.json",
        registry_ids=registry_guidelines,
        runtime_ids=compiled_guidelines,
    )
    handbook_collisions = registry_handbooks & (registry_mandates | registry_guidelines)
    if handbook_collisions:
        errors.append(f"handbook id collision: {sorted(handbook_collisions)}")
    _append_handbook_output_drift(root, entries, errors, warnings)
    _append_readable_source_output_drift(root, entries, warnings)

    return DocsSourceReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        mandate_ids=sorted(registry_mandates),
        guideline_ids=sorted(registry_guidelines),
        handbook_ids=sorted(set(handbook_ids)),
    )
