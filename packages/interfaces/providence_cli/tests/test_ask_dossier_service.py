from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_cli.services.ask_dossier import (
    build_and_output_dossier,
    estimate_budget_utilization_pct,
    load_dossier_artifact,
)


def test_estimate_budget_utilization_pct_scales_with_bytes_vs_token_budget() -> None:
    # 400 bytes / (100 tokens * 4 bytes/token) = 100% exactly.
    assert estimate_budget_utilization_pct(400, 100) == pytest.approx(100.0)
    # Half the budget consumed.
    assert estimate_budget_utilization_pct(200, 100) == pytest.approx(50.0)


def test_estimate_budget_utilization_pct_caps_at_100() -> None:
    assert estimate_budget_utilization_pct(10_000, 10) == 100.0


def test_estimate_budget_utilization_pct_handles_zero_budget() -> None:
    # budget_tokens=0 must not raise ZeroDivisionError.
    assert estimate_budget_utilization_pct(100, 0) == 100.0


def test_build_and_output_dossier_computes_real_percentage_not_hardcoded(
    tmp_path: Path,
) -> None:
    """The dossier's displayed percentage must reflect actual bytes_loaded,
    not the old hardcoded 50.0 constant  regression guard for the fix."""
    from providence_runtime.context import ContextResult

    probe_result = ContextResult(
        items=[], source="artifact", matched=0, truncated=False, bytes_loaded=40
    )
    real_result = ContextResult(
        items=["M001"], source="artifact", matched=1, truncated=False, bytes_loaded=40
    )
    typer_module = MagicMock()

    with patch(
        "providence_runtime.context.ContextLoader.load_result",
        side_effect=[probe_result, real_result],
    ):
        build_and_output_dossier(
            query="status?",
            skill=None,
            budget=100,  # 100 tokens * 4 bytes/token = 400 byte budget
            mandates_count=1,
            workspace_root=tmp_path,
            resolve_workspace_root_fn=lambda: tmp_path,
            compiled_active_dir_fn=lambda _root: tmp_path,
            logger=logging.getLogger(__name__),
            typer_module=typer_module,
        )

    printed = typer_module.echo.call_args[0][0]
    # 40 / 400 * 100 = 10.0%  not the old hardcoded 50.0%.
    assert "10.0%" in printed
    assert "50.0%" not in printed


def test_build_and_output_dossier_raises_on_breach(tmp_path: Path) -> None:
    """When measured bytes exceed the token budget, BudgetBreachError must
    actually propagate to the caller's error handler  previously
    unreachable because the percentage was hardcoded below the 100% breach
    threshold regardless of real dossier size."""
    from providence_runtime.context import ContextResult
    from providence_runtime.exceptions import BudgetBreachError

    probe_result = ContextResult(
        items=[],
        source="artifact",
        matched=0,
        truncated=False,
        bytes_loaded=1_000,  # far exceeds a tiny budget below
    )
    typer_module = MagicMock()

    with (
        patch(
            "providence_runtime.context.ContextLoader.load_result",
            side_effect=[probe_result, BudgetBreachError(utilization_pct=100.0)],
        ),
        pytest.raises(SystemExit),
    ):
        build_and_output_dossier(
            query="status?",
            skill=None,
            budget=1,  # 1 token * 4 bytes/token = 4 byte budget  trivially breached
            mandates_count=1,
            workspace_root=tmp_path,
            resolve_workspace_root_fn=lambda: tmp_path,
            compiled_active_dir_fn=lambda _root: tmp_path,
            logger=logging.getLogger(__name__),
            typer_module=typer_module,
        )
    # handle_dossier_error prints the breach message before exiting
    # confirms the breach was actually surfaced, not silently swallowed.
    assert typer_module.echo.called
    assert "Budget breach" in str(typer_module.echo.call_args_list[0])


def test_load_dossier_artifact_passes_compiled_path(tmp_path: Path) -> None:
    compiled_dir = tmp_path / ".providence" / "compiled"
    compiled_dir.mkdir(parents=True)
    artifact_path = compiled_dir / "governance-core.json"
    artifact_path.write_text('{"items": [], "version": "3.0"}', encoding="utf-8")

    def _compiled_active_dir(_workspace_root: Path) -> Path:
        return compiled_dir

    with patch(
        "providence_runtime.artifacts.CompiledArtifact.from_governance_json"
    ) as mock_loader:
        mock_loader.return_value = object()
        result = load_dossier_artifact(
            tmp_path, compiled_active_dir_fn=_compiled_active_dir
        )

    assert result is not None
    mock_loader.assert_called_once_with(artifact_path)
