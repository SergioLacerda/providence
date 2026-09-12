"""Unit tests for `providence governance adherence` command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.unit

runner = CliRunner()


def _make_adherence_result(
    score: int = 80,
    behavioral: float = 1.0,
    structural: bool = True,
    freshness: float = 1.0,
) -> dict[str, Any]:
    return {
        "score": score,
        "behavioral": behavioral,
        "structural": structural,
        "freshness": freshness,
        "details": {
            "allows": 5,
            "warns": 0,
            "blocks": 0,
            "window_events": 5,
            "window_hours": 24,
            "structural_status": "match" if structural else "drift_detected",
            "freshness_status": "elapsed=0s ttl=1800s",
            "behavioral_score": round(behavioral * 50),
            "structural_score": 30 if structural else 0,
            "freshness_score": round(freshness * 20),
        },
    }


class TestAdherenceCommand:
    """providence governance adherence exits with correct code per score vs threshold."""

    def test_exits_0_when_score_above_threshold(self, tmp_path: Path) -> None:
        result_data = _make_adherence_result(score=85)
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                return_value=result_data,
            ),
        ):
            from typer.testing import CliRunner

            from providence_cli.commands import governance as gov_mod

            r = CliRunner().invoke(gov_mod.app, ["adherence", "--threshold", "80"])
        assert r.exit_code == 0
        assert "85/100" in r.output

    def test_exits_1_when_score_below_threshold(self, tmp_path: Path) -> None:
        result_data = _make_adherence_result(score=60)
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                return_value=result_data,
            ),
        ):
            from providence_cli.commands import governance as gov_mod

            r = CliRunner().invoke(gov_mod.app, ["adherence", "--threshold", "80"])
        assert r.exit_code == 1
        assert "60/100" in r.output

    def test_verbose_shows_breakdown_table(self, tmp_path: Path) -> None:
        result_data = _make_adherence_result(
            score=90, behavioral=1.0, structural=True, freshness=1.0
        )
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                return_value=result_data,
            ),
        ):
            from providence_cli.commands import governance as gov_mod

            r = CliRunner().invoke(gov_mod.app, ["adherence", "--verbose"])
        assert r.exit_code == 0
        assert "Behavioral" in r.output
        assert "Structural" in r.output
        assert "Freshness" in r.output

    def test_structural_failure_shown_in_verbose(self, tmp_path: Path) -> None:
        result_data = _make_adherence_result(score=70, structural=False)
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                return_value=result_data,
            ),
        ):
            from providence_cli.commands import governance as gov_mod

            r = CliRunner().invoke(
                gov_mod.app, ["adherence", "--verbose", "--threshold", "0"]
            )
        assert r.exit_code == 0
        assert "0" in r.output  # structural_score = 0

    def test_error_in_compute_exits_1(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                side_effect=RuntimeError("disk full"),
            ),
        ):
            from providence_cli.commands import governance as gov_mod

            r = CliRunner().invoke(gov_mod.app, ["adherence"])
        assert r.exit_code == 1

    def test_custom_window_passed_through(self, tmp_path: Path) -> None:
        """--window is forwarded to compute_governance_adherence."""
        called_with: list[dict[str, Any]] = []

        def _capture(**kwargs: Any) -> dict[str, Any]:
            called_with.append(kwargs)
            return _make_adherence_result(score=100)

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                side_effect=_capture,
            ),
        ):
            from providence_cli.commands import governance as gov_mod

            CliRunner().invoke(gov_mod.app, ["adherence", "--window", "48"])

        assert called_with[0]["window_hours"] == 48
