"""Shared fixtures for `providence_wizard` Phase 4-6 pipeline benchmarks and tests.

Provides synthetic governance payloads and a typical wizard config so both
the regression test (`packages/interfaces/providence_wizard/tests/test_full_pipeline_performance.py`)
and the standalone benchmark script (`tests/perf/benchmark_wizard_pipeline.py`)
exercise `run_phase_4_5_6_generator` against the same inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WIZARD_PIPELINE_CONFIG: dict[str, Any] = {
    "language": "Python",
    "adoption_level": "FULL",
    "locale": "en",
    "docs_language": "English",
    "docs_locale": "en",
    "enforcement_mode": "warn_mode",
    "language_context": {
        "preferred_human_language": "English",
        "preferred_chat_language": "English",
        "preferred_ui_language": "English",
        "preferred_local_docs_language": "English",
    },
}

_GUIDELINE_CATEGORIES = (
    "testing",
    "style",
    "docs",
    "security",
    "performance",
    "naming",
)


def generate_governance_items(
    num_mandates: int, num_guidelines: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate synthetic mandate/guideline items for Phase 4-6 benchmarking."""
    mandates = [
        {
            "id": f"M{i:04d}",
            "type": "MANDATE",
            "title": f"Mandate {i}",
            "criticality": "OBRIGATÓRIO",
            "category": "architecture",
            "content": f"This is mandate {i} content.",
        }
        for i in range(1, num_mandates + 1)
    ]
    guidelines = [
        {
            "id": f"G{i:04d}",
            "type": "GUIDELINE",
            "title": f"Guideline {i}",
            "criticality": "OPCIONAL",
            "category": _GUIDELINE_CATEGORIES[i % len(_GUIDELINE_CATEGORIES)],
            "customizable": True,
            "content": f"This is guideline {i} content.",
        }
        for i in range(1, num_guidelines + 1)
    ]
    return mandates, guidelines


def write_governance_inputs(
    repo_root: Path, mandates: list[dict[str, Any]], guidelines: list[dict[str, Any]]
) -> None:
    """Write governance-core.json/governance-client.json under `repo_root/.providence/source`."""
    sdd_source = repo_root / ".providence" / "source"
    sdd_source.mkdir(parents=True, exist_ok=True)
    (sdd_source / "governance-core.json").write_text(
        json.dumps({"items": mandates}), encoding="utf-8"
    )
    (sdd_source / "governance-client.json").write_text(
        json.dumps({"items": guidelines}), encoding="utf-8"
    )
