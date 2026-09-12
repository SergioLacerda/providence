"""Direct-to-root deployment  opt-in alternative to the final-template staging flow.

Copies the wizard's compiled final-template output directly into the project
root, tracking managed files via a side-car manifest so reruns are idempotent:
managed files are updated in place, unmanaged (user-owned) files are never
overwritten, and files no longer present in a later generation are dropped
from the manifest (not deleted from disk, to avoid surprising data loss).

A side-car JSON manifest is used instead of an inline per-file marker comment
because not every generated file is safely commentable text (compiled
mandate/guideline `.bin` artifacts, JSON files without comment support).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from providence_wizard.constants import RUNTIME_DIRNAME

_GENERATOR_ID = "providence_wizard.direct_root_deploy"
_MANIFEST_RELATIVE_PATH = (
    Path(RUNTIME_DIRNAME) / "runtime" / "direct-root-manifest.json"
)


@dataclass(frozen=True)
class DeployToRootResult:
    """Per-file classification of a single direct-to-root deployment run."""

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def _read_fingerprint(final_template_dir: Path) -> str:
    metadata_file = final_template_dir / RUNTIME_DIRNAME / "metadata.json"
    if not metadata_file.exists():
        return "unknown"
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    return str(
        metadata.get("governance_fingerprint")
        or metadata.get("fingerprints", {}).get("combined")
        or "unknown"
    )


def _load_manifest(target_root: Path) -> dict[str, dict[str, str]]:
    manifest_file = target_root / _MANIFEST_RELATIVE_PATH
    if not manifest_file.exists():
        return {}
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    managed = data.get("managed_files", {})
    return managed if isinstance(managed, dict) else {}


def _write_manifest(
    target_root: Path,
    managed_files: dict[str, dict[str, str]],
    fingerprint: str,
) -> None:
    manifest_file = target_root / _MANIFEST_RELATIVE_PATH
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(
            {
                "generator": _GENERATOR_ID,
                "snapshot_fingerprint": fingerprint,
                "managed_files": managed_files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def deploy_to_root(
    *, target_root: Path, final_template_dir: Path
) -> DeployToRootResult:
    """Copy final_template_dir's contents directly into target_root, idempotently.

    Rules:
    - New file  copied, classified "created".
    - Existing file, identical bytes  "unchanged" (no write).
    - Existing file, different bytes, previously managed by this generator
      overwritten, classified "updated".
    - Existing file, different bytes, NOT previously managed  left alone,
      classified "skipped" (never clobber a file this generator doesn't own).
    - Previously-managed file no longer present in the source  dropped from
      the manifest, classified "removed" (the file itself is left on disk).
    """
    fingerprint = _read_fingerprint(final_template_dir)
    previously_managed = _load_manifest(target_root)
    result = DeployToRootResult()
    managed_files: dict[str, dict[str, str]] = {}
    seen_relative: set[str] = set()

    source_files = sorted(p for p in final_template_dir.rglob("*") if p.is_file())

    for source_file in source_files:
        relative = source_file.relative_to(final_template_dir).as_posix()
        seen_relative.add(relative)
        target_file = target_root / relative
        source_bytes = source_file.read_bytes()

        if not target_file.exists():
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(source_bytes)
            result.created.append(relative)
            managed_files[relative] = {
                "generator": _GENERATOR_ID,
                "snapshot_fingerprint": fingerprint,
            }
            continue

        if target_file.read_bytes() == source_bytes:
            result.unchanged.append(relative)
            if relative in previously_managed:
                managed_files[relative] = {
                    "generator": _GENERATOR_ID,
                    "snapshot_fingerprint": fingerprint,
                }
            continue

        if relative in previously_managed:
            target_file.write_bytes(source_bytes)
            result.updated.append(relative)
            managed_files[relative] = {
                "generator": _GENERATOR_ID,
                "snapshot_fingerprint": fingerprint,
            }
        else:
            result.skipped.append(relative)

    for relative in previously_managed:
        if relative not in seen_relative:
            result.removed.append(relative)

    _write_manifest(target_root, managed_files, fingerprint)
    return result
