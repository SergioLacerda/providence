"""Context builders shared across skill handlers."""

from __future__ import annotations

from ._archive import (
    _archive_context_candidates,
    _resolve_project_root_from_context,
    _safe_slug,
)
from ._compression import (
    _compress_context,
    _estimate_payload_size,
    _summarize_context_value,
)
from ._contracts import (
    _build_convergence_delta_report,
    _build_diagnosis_attestation,
    _build_diagnosis_report,
    _build_execution_contract,
)

__all__ = [
    "_archive_context_candidates",
    "_build_convergence_delta_report",
    "_build_diagnosis_attestation",
    "_build_diagnosis_report",
    "_build_execution_contract",
    "_compress_context",
    "_estimate_payload_size",
    "_resolve_project_root_from_context",
    "_safe_slug",
    "_summarize_context_value",
]
