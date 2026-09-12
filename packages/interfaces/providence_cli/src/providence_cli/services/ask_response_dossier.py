"""ask_response_dossier  dossier line construction for the `providence ask` JSON path.

Split out of `ask_response_json.py` (T4,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_cli.services.ask_dossier import estimate_budget_utilization_pct
from providence_cli.services.ask_types import _AskInputs, _AskSessionContext


def build_json_dossier_lines(
    inputs: _AskInputs,
    session: _AskSessionContext,
    mandates_count: int,
    *,
    resolve_dossier_budget_fn: Callable[[int | None], int],
    load_dossier_artifact_fn: Callable[[Path], Any | None],
    build_dossier_lines_fn: Callable[..., list[str]],
    handle_dossier_error_fn: Callable[[Exception], None],
    prefer_full_summary_fn: Callable[[], bool],
) -> list[str]:
    """Build dossier lines for the JSON response, or [] if not requested."""
    if not inputs.dossier:
        return []
    try:
        from providence_runtime.context import ContextLoader, ContextRequest

        dossier_budget = resolve_dossier_budget_fn(inputs.budget)
        artifact = load_dossier_artifact_fn(session.workspace_root)
        prefer_full_summary = prefer_full_summary_fn()
        loader = ContextLoader()
        # Probe pass at 0% utilization: measures real bytes_loaded without
        # triggering compression or breach (see ask_dossier.build_and_output_dossier
        # for the text-mode twin of this logic).
        probe_result = loader.load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=0.0,
                prefer_full_summary=prefer_full_summary,
            )
        )
        budget_utilization_pct = estimate_budget_utilization_pct(
            probe_result.bytes_loaded, dossier_budget
        )
        context_result = loader.load_result(
            ContextRequest(
                query=inputs.query,
                artifact=artifact,
                max_items=mandates_count,
                budget_utilization_pct=budget_utilization_pct,
                prefer_full_summary=prefer_full_summary,
            )
        )
        return build_dossier_lines_fn(
            query=inputs.query,
            skill=inputs.skill,
            budget=dossier_budget,
            mandates_count=mandates_count,
            budget_utilization_pct=budget_utilization_pct,
            context_result=context_result,
        )
    except Exception as exc:
        handle_dossier_error_fn(exc)
        return []
