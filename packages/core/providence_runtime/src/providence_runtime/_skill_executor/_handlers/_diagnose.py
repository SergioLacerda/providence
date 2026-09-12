"""DiagnoseHandler — diagnosis artifacts calibrated from failure history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ...learning import FailureLedgerEntry
from .._base import Handler, PreRunOutcome
from .._constants import _FooterFn
from .._context_builders import _build_diagnosis_attestation, _build_diagnosis_report
from .._stabilization import _is_retryable_error


class DiagnoseHandler(Handler):
    """Prepare diagnosis artifacts and calibrate confidence from history.

    Example:
        Recurrent failures with the same symptom can increase diagnosis
        confidence before the diagnose fallback commands run.
    """

    def can_retry(
        self,
        context: dict[str, Any],
        *,
        exit_code: int,
        error: str,
        attempt_count: int,
    ) -> bool:
        del context, attempt_count
        return _is_retryable_error(exit_code=exit_code, error=error)

    def pre_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        skill: Any,
        profile: str,
        footer_fn: _FooterFn,
    ) -> PreRunOutcome:
        report = _build_diagnosis_report(context)
        similar_failures = []
        if (
            report.get("hypothesis") != "unknown"
            and learning is not None
            and hasattr(learning, "find_similar_failures")
        ):
            similar_failures = learning.find_similar_failures(
                symptom=str(report.get("hypothesis", "unknown")),
                root_cause=str(report.get("root_cause", "inconclusive")),
                limit=5,
            )
            confidence = report.get("confidence", 0.0)
            if isinstance(confidence, int | float) and similar_failures:
                recurrence_factor = min(len(similar_failures), 5) * 0.2
                report["confidence"] = min(
                    1.0, float(confidence) * (1.0 + recurrence_factor)
                )
                report["historical_matches"] = len(similar_failures)
        attestation = _build_diagnosis_attestation(
            {**context, "diagnosis_report": report}
        )
        return PreRunOutcome(
            artifacts={
                "diagnosis_report": report,
                "diagnosis_attestation": attestation,
            }
        )

    def post_run(
        self,
        context: dict[str, Any],
        *,
        learning: Any,
        exit_code: int,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        report = artifacts.get("diagnosis_report", context.get("diagnosis_report", {}))
        if not isinstance(report, dict):
            return {}
        if learning is None or not hasattr(learning, "append_failure"):
            return {}
        learning.append_failure(
            FailureLedgerEntry(
                symptom=str(report.get("hypothesis", "unknown")),
                root_cause=str(report.get("root_cause", "inconclusive")),
                fix="sdd-diagnose",
                validation="postcheck",
                regression=exit_code != 0,
                tags=["diagnose", "executed" if exit_code == 0 else "failed"],
                evidence_refs=[
                    ref
                    for ref in report.get("evidence_refs", [])
                    if isinstance(ref, str)
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return {}
