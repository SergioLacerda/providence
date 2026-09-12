"""Full-pipeline wall-time regression test for Phase 4-6 generation.

Guards the BigBang refactor's Day 8/9 performance target: generating a
complete `.providence/` project structure (governance sources, compiled artifacts,
IDE templates, seedlings, adapters, output validation) for a typical-sized
spec must stay well under the 250ms budget.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from tests.perf.wizard_pipeline_fixtures import (
    WIZARD_PIPELINE_CONFIG,
    generate_governance_items,
    write_governance_inputs,
)

from providence_wizard.orchestration.phase_4_5_6_generator import (
    run_phase_4_5_6_generator,
)

pytestmark = [pytest.mark.unit, pytest.mark.perf]

_FULL_PIPELINE_BUDGET_MS = 250


def test_full_pipeline_completes_under_budget(tmp_path: Path) -> None:
    """Phase 4-6 generation for a typical spec must complete in < 250ms."""
    mandates, guidelines = generate_governance_items(num_mandates=10, num_guidelines=10)
    write_governance_inputs(tmp_path, mandates, guidelines)
    output_base = tmp_path / "out"

    start = time.perf_counter()
    result = run_phase_4_5_6_generator(tmp_path, output_base, WIZARD_PIPELINE_CONFIG)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result["success"] is True, result["errors"]
    assert result["mandates"] == 10
    assert result["guidelines"] == 10
    assert elapsed_ms < _FULL_PIPELINE_BUDGET_MS, (
        f"Full pipeline took {elapsed_ms:.2f}ms, exceeding the "
        f"{_FULL_PIPELINE_BUDGET_MS}ms budget"
    )
