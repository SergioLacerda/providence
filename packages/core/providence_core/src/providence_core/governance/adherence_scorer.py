"""Governance adherence scoring engine."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ._adherence_scorer_support import (
    compute_behavioral,
    compute_freshness,
    compute_structural,
    get_compiled_fingerprint,
    read_all_events,
    workspace_root_or_none,
)

logger = logging.getLogger(__name__)


class GovernanceAdherenceScorer:
    """Compute governance adherence scores from runtime and compliance evidence."""

    @staticmethod
    def compute(
        *,
        workspace_root: Path | None = None,
        log_path: Path | None = None,
        state_path: Path | None = None,
        window_hours: int = 24,
    ) -> dict[str, Any]:
        """Return a weighted adherence summary for the active workspace."""
        now = datetime.now()
        root = workspace_root_or_none(workspace_root)
        resolved_state = state_path or (
            root / ".providence" / "runtime" / "governance-state.json" if root else None
        )
        all_events = GovernanceAdherenceScorer._read_all_events(
            workspace_root=workspace_root, log_path=log_path
        )
        beh = GovernanceAdherenceScorer._compute_behavioral(
            all_events, now - timedelta(hours=window_hours)
        )
        struct = GovernanceAdherenceScorer._compute_structural(
            resolved_state, workspace_root
        )
        fresh = GovernanceAdherenceScorer._compute_freshness(struct["state_data"], now)
        return {
            "score": beh["score"] + struct["score"] + fresh["score"],
            "behavioral": beh["ratio"],
            "structural": struct["match"],
            "freshness": fresh["ratio"],
            "details": {
                "allows": beh["allows"],
                "warns": beh["warns"],
                "blocks": beh["blocks"],
                "window_events": beh["window_events"],
                "window_hours": window_hours,
                "structural_status": struct["detail"],
                "freshness_status": fresh["detail"],
                "behavioral_score": beh["score"],
                "structural_score": struct["score"],
                "freshness_score": fresh["score"],
            },
        }

    @staticmethod
    def _read_all_events(
        *, workspace_root: Path | None = None, log_path: Path | None = None
    ) -> list[dict[str, Any]]:
        return read_all_events(workspace_root=workspace_root, log_path=log_path)

    @staticmethod
    def _get_compiled_fingerprint(workspace_root: Path | None = None) -> str:
        return get_compiled_fingerprint(workspace_root)

    @staticmethod
    def _compute_behavioral(
        all_events: list[dict[str, Any]], cutoff: datetime
    ) -> dict[str, Any]:
        return compute_behavioral(all_events, cutoff)

    @staticmethod
    def _compute_structural(
        resolved_state: Path | None, workspace_root: Path | None
    ) -> dict[str, Any]:
        return compute_structural(
            resolved_state,
            workspace_root,
            GovernanceAdherenceScorer._get_compiled_fingerprint,
        )

    @staticmethod
    def _compute_freshness(state_data: dict[str, Any], now: datetime) -> dict[str, Any]:
        return compute_freshness(state_data, now)
