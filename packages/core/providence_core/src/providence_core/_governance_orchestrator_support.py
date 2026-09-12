from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from providence_core._governance_orchestrator_types import Phase1Result, Phase2Result
from providence_core.utils.compiler_runner import CompilationResult
from providence_core.utils.environment import resolve_profile

logger = logging.getLogger(__name__)


def ensure_spec_mandates(repo_root: Path, workspace_root: Path) -> Path:
    spec_mandates_path = workspace_root / ".providence" / "spec" / "mandates.json"
    canonical_dir = repo_root / "docs" / "spec" / "canonical" / "core" / "mandates"
    if canonical_dir.exists():
        try:
            from providence_integration.builders.governance.pipeline_builder import (
                PipelineBuilder,
            )

            PipelineBuilder.generate_spec_file(canonical_dir, spec_mandates_path)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to auto-generate spec mandates: %s", exc)
    return spec_mandates_path


def copy_build_artifacts(build_dir: Path, compiled_dir: Path) -> None:
    for json_file in ("governance-core.json", "governance-client.json"):
        src = build_dir / json_file
        if src.exists():
            shutil.copy2(src, compiled_dir / json_file)
    audit_dir = compiled_dir / "audit"
    if audit_dir.exists():
        for metadata_file in ("metadata-core.json", "metadata-client-template.json"):
            src = audit_dir / metadata_file
            if src.exists():
                shutil.copy2(src, compiled_dir / metadata_file)


def publish_canonical_artifacts(workspace_root: Path, compiled_dir: Path) -> None:
    audit_dir = compiled_dir / "audit"
    sdd_compiled_dir = workspace_root / ".providence" / "compiled"
    sdd_compiled_dir.mkdir(parents=True, exist_ok=True)
    sdd_audit_dir = sdd_compiled_dir / "audit"
    sdd_audit_dir.mkdir(parents=True, exist_ok=True)
    for filename in [
        "governance-core.compiled.msgpack",
        "governance-client-template.compiled.msgpack",
        "governance-core.json",
        "governance-client.json",
        "metadata-core.json",
        "metadata-client-template.json",
    ]:
        src = compiled_dir / filename
        if src.exists():
            shutil.copy2(src, sdd_compiled_dir / filename)
    for filename in (
        "metadata-core.json",
        "metadata-client-template.json",
        "governance-core.json",
        "governance-client.json",
        "DEPLOYMENT_MANIFEST.json",
    ):
        src = audit_dir / filename
        if src.exists():
            shutil.copy2(src, sdd_audit_dir / filename)


def phase2_result_from_compile(result: CompilationResult) -> Phase2Result:
    phase2_result: Phase2Result = {"success": True}
    for key in (
        "core_msgpack_file",
        "client_msgpack_file",
        "core_fingerprint_salt",
        "client_fingerprint",
    ):
        value = result.get(key)
        if isinstance(value, str):
            phase2_result[key] = value
    return phase2_result


def pipeline_checks(
    phase_1: Phase1Result, phase_2: Phase2Result
) -> list[tuple[str, bool]]:
    phase2_client_fp = phase_2.get("client_fingerprint") or phase_2.get("fingerprint")
    phase2_core_salt = phase_2.get("core_fingerprint_salt") or phase_2.get(
        "fingerprint_core_salt"
    )
    return [
        ("Phase 1 success", phase_1.get("success") is True),
        ("Phase 2 success", phase_2.get("success") is True),
        (
            "Client fingerprint preserved",
            phase_1.get("client_fingerprint") == phase2_client_fp,
        ),
        (
            "Core fingerprint used as salt",
            phase_1.get("core_fingerprint") == phase2_core_salt,
        ),
        (
            "Fingerprints different",
            phase_1.get("core_fingerprint") != phase_1.get("client_fingerprint"),
        ),
        ("Core items > 0", phase_1.get("core_item_count", 0) > 0),
        ("Client items > 0", phase_1.get("client_item_count", 0) > 0),
    ]


def resolve_active_profile(root: Path) -> str:
    try:
        return resolve_profile(root=root).type
    except Exception:
        return "master"


def deployment_summary(compiled_dir: Path) -> dict[str, Any]:
    return {
        "status": "ready_for_deployment",
        "artifacts": {
            "core_msgpack": str(compiled_dir / "governance-core.compiled.msgpack"),
            "client_msgpack": str(
                compiled_dir / "governance-client-template.compiled.msgpack"
            ),
            "core_metadata": str(compiled_dir / "audit" / "metadata-core.json"),
            "client_metadata": str(
                compiled_dir / "audit" / "metadata-client-template.json"
            ),
        },
        "deployment_location": "compiled/",
        "next_step": "PHASE 4: Deploy to runtime/",
    }
