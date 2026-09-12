from __future__ import annotations

from types import SimpleNamespace

import pytest

from providence_core._governance_orchestrator_main import print_pipeline_result


def test_print_pipeline_result_success(capsys) -> None:
    orchestrator = SimpleNamespace(
        get_deployment_summary=lambda: {
            "status": "ready",
            "artifacts": {"core": "/tmp/core.msgpack", "client": "/tmp/client.msgpack"},
            "deployment_location": "/tmp/deploy",
            "next_step": "commit",
        }
    )

    print_pipeline_result(orchestrator, {"full_pipeline_success": True})

    output = capsys.readouterr().out
    assert "PHASE 1 + PHASE 2 COMPLETE" in output
    assert "core.msgpack" in output
    assert "client.msgpack" in output
    assert "deployment_location" not in output
    assert "Ready for: commit" in output


def test_print_pipeline_result_failure_exits(capsys) -> None:
    orchestrator = SimpleNamespace(get_deployment_summary=lambda: {})

    with pytest.raises(SystemExit) as exc:
        print_pipeline_result(orchestrator, {"full_pipeline_success": False})

    assert exc.value.code == 1
    assert "Pipeline failed" in capsys.readouterr().out


def test_print_pipeline_result_empty_result_exits(capsys) -> None:
    orchestrator = SimpleNamespace(get_deployment_summary=lambda: {})

    with pytest.raises(SystemExit):
        print_pipeline_result(orchestrator, {})

    assert "Pipeline failed" in capsys.readouterr().out
