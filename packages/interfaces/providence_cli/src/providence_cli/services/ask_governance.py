"""Governance loading helpers for ask flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.services._ask_governance_support import (
    GovResult,
    compiled_candidates,
    fingerprint_file_content,
    load_via_runtime_injector,
    log_workspace_metadata,
    resolve_signature_mode,
    try_sdd_compiled_artifact,
    try_sdd_compiled_fallback_result,
    validate_artifact_signature_mode,
)

__all__ = [
    "GovResult",
    "fingerprint_file",
    "signature_mode",
    "try_sdd_compiled_dir",
    "validate_signature_for_artifact",
    "load_governance_via_runtime",
    "try_sdd_compiled_fallback",
    "log_sdd_metadata",
    "load_compiled_governance",
]


def _compiled_candidates(
    workspace_root: Path, *, compiled_active_dir_fn: Any
) -> list[Path]:
    return compiled_candidates(
        workspace_root, compiled_active_dir_fn=compiled_active_dir_fn
    )


def fingerprint_file(path: Path) -> str:
    """Return the content fingerprint for the given file."""
    return fingerprint_file_content(path)


def signature_mode() -> str:
    """Return the configured artifact signature verification mode."""
    return resolve_signature_mode()


def try_sdd_compiled_dir(
    sdd_compiled: Path,
    *,
    logger: Any | None = None,
) -> tuple[str, str, int] | None:
    """Try loading governance artifacts from a `.providence/compiled` directory."""
    return try_sdd_compiled_artifact(
        sdd_compiled, logger=logger, fingerprint_file_fn=fingerprint_file
    )


def validate_signature_for_artifact(
    artifact_path: Path,
    *,
    signature_mode_value: str,
) -> tuple[bool, bool, str, str]:
    """Validate an artifact's signature against the configured mode."""
    return validate_artifact_signature_mode(
        artifact_path=artifact_path, signature_mode_value=signature_mode_value
    )


def load_governance_via_runtime(
    workspace_root: Path,
    *,
    compiled_active_dir_fn: Any,
    logger: Any | None = None,
) -> tuple[str, str, int, str, str] | None:
    """Load governance artifacts via the SDD runtime injector, if available."""
    return load_via_runtime_injector(
        workspace_root=workspace_root,
        compiled_active_dir_fn=compiled_active_dir_fn,
        logger=logger,
    )


def try_sdd_compiled_fallback(
    sdd_compiled: Path,
    signature_mode_value: str,
    *,
    logger: Any | None = None,
) -> GovResult | None:
    """Fall back to loading governance artifacts directly from `.providence/compiled`."""
    return try_sdd_compiled_fallback_result(
        sdd_compiled,
        signature_mode_value,
        logger=logger,
        try_sdd_compiled_dir_fn=try_sdd_compiled_dir,
        validate_signature_for_artifact_fn=validate_signature_for_artifact,
    )


def log_sdd_metadata(workspace_root: Path, *, logger: Any | None = None) -> None:
    """Log workspace governance metadata for diagnostics."""
    log_workspace_metadata(workspace_root, logger=logger)


def load_compiled_governance(
    workspace_root: Path,
    *,
    compiled_active_dir_fn: Any,
    logger: Any | None = None,
    load_via_runtime_fn: Any = None,
) -> GovResult:
    """Load compiled governance artifacts, trying runtime then filesystem fallback."""
    mode = signature_mode()
    _load_via_runtime = load_via_runtime_fn or load_governance_via_runtime
    runtime_result = _load_via_runtime(
        workspace_root, compiled_active_dir_fn=compiled_active_dir_fn, logger=logger
    )
    if runtime_result is not None:
        source, fp, count, auth_state, trust_source = runtime_result
        authenticated = auth_state == "verified"
        degraded = auth_state == "degraded"
        return source, fp, count, authenticated, degraded, "", trust_source

    for sdd_compiled in _compiled_candidates(
        workspace_root, compiled_active_dir_fn=compiled_active_dir_fn
    ):
        result = try_sdd_compiled_fallback(sdd_compiled, mode, logger=logger)
        if result is not None:
            return result

    log_sdd_metadata(workspace_root, logger=logger)
    return "none", "", 0, False, False, "no governance artifacts found", "none"
