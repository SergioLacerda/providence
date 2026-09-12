"""Standalone benchmark for `providence_wizard`'s Phase 4-6 generation pipeline.

Measures `run_phase_4_5_6_generator` wall time across multiple spec sizes.
Useful for ad-hoc profiling when investigating the `< 250ms` full-pipeline
performance target documented in
`.analysis/refined/2026-06-08-providence-wizard-final-refactor/benchmark-results.md`.

Usage:
    python tests/perf/benchmark_wizard_pipeline.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _src in (
    _REPO_ROOT,
    _REPO_ROOT / "packages/interfaces/providence_wizard/src",
    _REPO_ROOT / "packages/interfaces/providence_cli/src",
    _REPO_ROOT / "packages/core/providence_core/src",
    _REPO_ROOT / "packages/features/providence_integration/src",
    _REPO_ROOT / "packages/features/providence_adapters/src",
):
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from providence_wizard.orchestration.phase_4_5_6_generator import (  # noqa: E402
    run_phase_4_5_6_generator,
)
from tests.perf.wizard_pipeline_fixtures import (  # noqa: E402
    WIZARD_PIPELINE_CONFIG,
    generate_governance_items,
    write_governance_inputs,
)

_SCALES = (
    (10, 10),
    (100, 100),
    (1000, 1000),
)


def _run_once(num_mandates: int, num_guidelines: int) -> tuple[float, bool]:
    mandates, guidelines = generate_governance_items(num_mandates, num_guidelines)
    with tempfile.TemporaryDirectory() as td:
        repo_root = Path(td)
        write_governance_inputs(repo_root, mandates, guidelines)

        start = time.perf_counter()
        result = run_phase_4_5_6_generator(
            repo_root, repo_root / "out", WIZARD_PIPELINE_CONFIG
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

    return elapsed_ms, result["success"]


def main() -> None:
    print(f"{'mandates':>10} {'guidelines':>10} {'elapsed_ms':>12} {'success':>8}")
    for num_mandates, num_guidelines in _SCALES:
        elapsed_ms, success = _run_once(num_mandates, num_guidelines)
        print(
            f"{num_mandates:>10} {num_guidelines:>10} {elapsed_ms:>12.2f} {success!s:>8}"
        )


if __name__ == "__main__":
    main()
