"""Tests for runtime handbook consultation in `providence ask` snapshots."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from providence_cli.commands._ask_backend._phase_timer import PhaseTimer
from providence_cli.commands._ask_backend._pipeline_snapshot import (
    build_governed_ask_snapshot,
)


def _write_runtime_handbook(root: Path) -> None:
    handbook_dir = root / ".providence" / "source" / "handbook"
    item_path = handbook_dir / "context-loading" / "context-flow.yaml"
    item_path.parent.mkdir(parents=True)
    item_path.write_text(
        yaml.safe_dump(
            {
                "id": "HBK-CONTEXT-LOADING",
                "title": "Context Flow",
                "source_doc": "docs/cognition/context-loading/context_flow.md",
                "mandate_refs": ["M003", "M005"],
                "task_types": ["planning", "implementation", "diagnosis"],
                "operation_phases": ["context_loading", "planning"],
                "load_policy": {"mode": "selective", "max_tokens": 700},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (handbook_dir / "index.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1",
                "items": [
                    {
                        "id": "HBK-CONTEXT-LOADING",
                        "title": "Context Flow",
                        "source_doc": "docs/cognition/context-loading/context_flow.md",
                        "runtime_doc": ".providence/source/handbook/context-loading/context-flow.yaml",
                        "mandate_refs": ["M003", "M005"],
                        "task_types": ["planning", "implementation", "diagnosis"],
                        "operation_phases": ["context_loading", "planning"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_build_governed_ask_snapshot_adds_runtime_handbook_match(
    tmp_path: Path,
) -> None:
    _write_runtime_handbook(tmp_path)
    with (
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._load_compiled_governance",
            return_value=("compiled", "fp-1", 16, True, False, "", "verified"),
        ),
        patch(
            "providence_cli.commands._ask_backend._runtime_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._root_seed_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._pipeline_snapshot._collect_learning_signals",
            return_value={},
        ),
    ):
        snapshot = build_governed_ask_snapshot(
            query="plan implementation",
            skill=None,
            organize_used=False,
            workspace_root=tmp_path,
        )

    lookup = snapshot["handbook_lookup"]
    assert lookup["status"] == "matched"
    assert lookup["diagnostic"] == "handbook_match=1"
    assert lookup["matches"][0]["id"] == "HBK-CONTEXT-LOADING"


def test_build_governed_ask_snapshot_records_runtime_handbook_phase(
    tmp_path: Path,
) -> None:
    """When a PhaseTimer is supplied, the handbook lookup is measured as its
    own ask.runtime.handbook phase (design.md 2, T-02)."""
    _write_runtime_handbook(tmp_path)
    timer = PhaseTimer()
    with (
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._load_compiled_governance",
            return_value=("compiled", "fp-1", 16, True, False, "", "verified"),
        ),
        patch(
            "providence_cli.commands._ask_backend._runtime_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._root_seed_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._pipeline_snapshot._collect_learning_signals",
            return_value={},
        ),
    ):
        build_governed_ask_snapshot(
            query="plan implementation",
            skill=None,
            organize_used=False,
            workspace_root=tmp_path,
            phase_timer=timer,
        )

    phase_ids = [r.phase_id for r in timer.records()]
    assert phase_ids == ["ask.runtime.handbook"]
    assert timer.records()[0].latency_domain == "governance"


def test_build_governed_ask_snapshot_without_phase_timer_records_nothing(
    tmp_path: Path,
) -> None:
    """phase_timer is optional  omitting it must not change behavior or
    error (backward compatibility for every other caller)."""
    _write_runtime_handbook(tmp_path)
    with (
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._load_compiled_governance",
            return_value=("compiled", "fp-1", 16, True, False, "", "verified"),
        ),
        patch(
            "providence_cli.commands._ask_backend._runtime_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._root_seed_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._pipeline_snapshot._collect_learning_signals",
            return_value={},
        ),
    ):
        snapshot = build_governed_ask_snapshot(
            query="plan implementation",
            skill=None,
            organize_used=False,
            workspace_root=tmp_path,
        )

    assert snapshot["handbook_lookup"]["status"] == "matched"


def test_load_ask_snapshot_records_both_governance_snapshot_and_handbook_phases(
    tmp_path: Path,
) -> None:
    """End-to-end through _load_ask_snapshot (the real caller): the outer
    ask.governance.snapshot span (owned by the caller, per
    test_ask_telemetry_phase_events.py's mocking contract) and the inner
    ask.runtime.handbook span (owned by build_governed_ask_snapshot) must
    both appear  nested, by design (see _pipeline.py docstring)."""
    from providence_cli.commands._ask_backend._pipeline_session import (
        _load_ask_snapshot,
    )
    from providence_cli.services.ask_types import _AskInputs, _AskSessionContext

    _write_runtime_handbook(tmp_path)

    with (
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._load_compiled_governance",
            return_value=("compiled", "fp-1", 16, True, False, "", "verified"),
        ),
        patch(
            "providence_cli.commands._ask_backend._runtime_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._root_seed_drift_check",
            return_value=False,
        ),
        patch(
            "providence_cli.commands._ask_backend._pipeline_snapshot._collect_learning_signals",
            return_value={},
        ),
    ):
        inputs = _AskInputs(
            query="plan implementation",
            dossier=False,
            skill=None,
            budget=None,
            full=False,
            log_path=None,
            log_format="jsonl",
            tokens_input=None,
            tokens_output=None,
        )
        session = _AskSessionContext(
            workspace_root=tmp_path,
            organize_used=False,
            organize_reason="light_input",
            organize_artifact_path="",
            organize_chunks=0,
            organize_retrieval="indexed_only",
            cached_handbook_task_type=None,
            profile="client",
            state="HEALTHY",
            agent_id="agent-1",
            trace_id="trace-1",
            start_mono=0.0,
            start_ts="2026-07-30T00:00:00Z",
        )
        _load_ask_snapshot(inputs, session)

    phase_ids = [r.phase_id for r in session.phase_timer.records()]
    assert phase_ids == ["ask.runtime.handbook", "ask.governance.snapshot"]
