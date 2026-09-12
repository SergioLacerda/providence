"""Tests for providence_cli.services.governance_scoring_output."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_scoring_output import (
    render_governance_adherence_output,
    render_governance_score_output,
    run_governance_adherence_cmd,
    run_governance_score_cmd,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestRenderGovernanceScoreOutput:
    def test_verbose_table_above_threshold(self) -> None:
        checks = [("check a", True, 50), ("check b", False, 50)]
        render_governance_score_output(
            checks=checks,
            final_score=50,
            threshold=50,
            verbose=True,
            console=_console(),
        )

    def test_non_verbose_above_threshold(self) -> None:
        render_governance_score_output(
            checks=[], final_score=80, threshold=50, verbose=False, console=_console()
        )

    def test_below_threshold_raises_exit(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            render_governance_score_output(
                checks=[],
                final_score=40,
                threshold=50,
                verbose=False,
                console=_console(),
            )
        assert exc_info.value.exit_code == 1


class TestRenderGovernanceAdherenceOutput:
    _RESULT = {
        "score": 80,
        "details": {
            "behavioral_score": 40,
            "allows": 10,
            "warns": 1,
            "blocks": 0,
            "structural_score": 25,
            "structural_status": "ok",
            "freshness_score": 15,
            "freshness_status": "fresh",
        },
    }

    def test_verbose_table_above_threshold(self) -> None:
        render_governance_adherence_output(
            result=self._RESULT,
            threshold=50,
            window=24,
            verbose=True,
            console=_console(),
        )

    def test_non_verbose_above_threshold(self) -> None:
        render_governance_adherence_output(
            result=self._RESULT,
            threshold=50,
            window=24,
            verbose=False,
            console=_console(),
        )

    def test_below_threshold_raises_exit(self) -> None:
        result = {**self._RESULT, "score": 10}
        with pytest.raises(typer.Exit) as exc_info:
            render_governance_adherence_output(
                result=result,
                threshold=50,
                window=24,
                verbose=False,
                console=_console(),
            )
        assert exc_info.value.exit_code == 1


class TestRunGovernanceScoreCmd:
    def test_no_workspace_exits_1(self) -> None:
        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=None,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_governance_score_cmd(verbose=False, threshold=50, console=_console())
        assert exc_info.value.exit_code == 1

    def test_resolves_workspace_and_delegates(self, tmp_path: Path) -> None:
        captured: dict = {}

        def _capture_run(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.utils.providence_authority.enforce_path_policy",
                side_effect=lambda root, **_: root,
            ),
            patch(
                "providence_cli.services.governance_scoring_output.run_governance_score",
                side_effect=_capture_run,
            ),
        ):
            run_governance_score_cmd(verbose=True, threshold=70, console=_console())

        assert captured["ws_root"] == tmp_path
        assert captured["verbose"] is True
        assert captured["threshold"] == 70


class TestRunGovernanceAdherenceCmd:
    def test_success_renders_result(self, tmp_path: Path) -> None:
        result = {
            "score": 80,
            "details": {
                "behavioral_score": 40,
                "allows": 10,
                "warns": 1,
                "blocks": 0,
                "structural_score": 25,
                "structural_status": "ok",
                "freshness_score": 15,
                "freshness_status": "fresh",
            },
        }
        captured: dict = {}

        def _capture_render(**kwargs):
            captured.update(kwargs)

        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                return_value=result,
            ),
            patch(
                "providence_cli.services.governance_scoring_output.render_governance_adherence_output",
                side_effect=_capture_render,
            ),
        ):
            run_governance_adherence_cmd(
                verbose=False, threshold=50, window=24, console=_console()
            )

        assert captured["result"] == result
        assert captured["threshold"] == 50
        assert captured["window"] == 24

    def test_exception_exits_1(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.utils.providence_authority.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.compliance.compute_governance_adherence",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_governance_adherence_cmd(
                verbose=False, threshold=50, window=24, console=_console()
            )
        assert exc_info.value.exit_code == 1
