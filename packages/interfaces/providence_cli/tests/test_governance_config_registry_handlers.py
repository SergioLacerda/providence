from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_config_handlers import run_governance_load
from providence_cli.services.governance_registry_handlers import (
    run_reconcile_registries,
)
from providence_cli.services.governance_validate_handlers import run_governance_validate
from providence_cli.services.registry_reconciliation import ReconciliationError


def test_reconcile_registries_json_error_on_exception() -> None:
    with (
        patch(
            "providence_cli.services.governance_registry_handlers.reconcile_registries",
            side_effect=ReconciliationError("boom"),
        ),
        pytest.raises(typer.Exit),
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=True,
            json_output=True,
            console=Console(),
        )


def test_reconcile_registries_json_drift_exits() -> None:
    summary = SimpleNamespace(
        drift_detected=True,
        commands={"added": 1, "removed": 0, "unchanged": 2},
        skills={"added": 0, "removed": 1, "unchanged": 3},
        as_json=lambda: {"drift_detected": True},
    )
    with (
        patch(
            "providence_cli.services.governance_registry_handlers.reconcile_registries",
            return_value=summary,
        ),
        pytest.raises(typer.Exit),
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=True,
            json_output=True,
            console=Console(),
        )


def test_reconcile_registries_text_error_exits() -> None:
    with (
        patch(
            "providence_cli.services.governance_registry_handlers.reconcile_registries",
            side_effect=ReconciliationError("fail"),
        ),
        pytest.raises(typer.Exit),
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=False,
            json_output=False,
            console=Console(),
        )


def test_reconcile_registries_json_success() -> None:
    summary = SimpleNamespace(
        drift_detected=False,
        commands={"added": 0, "removed": 0, "unchanged": 2},
        skills={"added": 0, "removed": 0, "unchanged": 3},
        as_json=lambda: {"drift_detected": False},
    )
    with patch(
        "providence_cli.services.governance_registry_handlers.reconcile_registries",
        return_value=summary,
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=True,
            json_output=True,
            console=Console(),
        )


def test_reconcile_registries_text_success() -> None:
    summary = SimpleNamespace(
        drift_detected=False,
        commands={"added": 0, "removed": 0, "unchanged": 2},
        skills={"added": 0, "removed": 0, "unchanged": 3},
        as_json=lambda: {"drift_detected": False},
    )
    with patch(
        "providence_cli.services.governance_registry_handlers.reconcile_registries",
        return_value=summary,
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=False,
            json_output=False,
            console=Console(),
        )


def test_reconcile_registries_text_drift_branch() -> None:
    summary = SimpleNamespace(
        drift_detected=True,
        commands={"added": 1, "removed": 0, "unchanged": 2},
        skills={"added": 0, "removed": 1, "unchanged": 3},
        as_json=lambda: {"drift_detected": True},
    )
    with patch(
        "providence_cli.services.governance_registry_handlers.reconcile_registries",
        return_value=summary,
    ):
        run_reconcile_registries(
            ws_root=Path("."),
            check=True,
            json_output=False,
            console=Console(),
        )


def test_governance_load_invalid_path_exits() -> None:
    with pytest.raises(typer.Exit):
        run_governance_load(
            path="bad",
            output_json=True,
            console=Console(),
            validate_path=lambda _p: False,
            load_config=lambda _p: {},
            get_summary=lambda _p, config: {},
        )


def test_governance_load_success_json() -> None:
    with patch(
        "providence_cli.services.governance_config_handlers.emit_json"
    ) as emit_json:
        run_governance_load(
            path=".providence/compiled",
            output_json=True,
            console=Console(),
            validate_path=lambda _p: True,
            load_config=lambda _p: {"items": []},
            get_summary=lambda _p, config: {"Total Items": 0},
        )
    payload = emit_json.call_args.args[0]
    assert payload["ok"] is True
    assert payload["command"] == "governance load"


def test_governance_load_success_text() -> None:
    run_governance_load(
        path=".providence/compiled",
        output_json=False,
        console=Console(),
        validate_path=lambda _p: True,
        load_config=lambda _p: {"items": []},
        get_summary=lambda _p, config: {"Total Items": 0},
    )


def test_governance_validate_json_failure_exits() -> None:
    preflight = SimpleNamespace(passed=False, reason="missing", details={})
    with pytest.raises(typer.Exit):
        run_governance_validate(
            path=".providence/compiled",
            skip_handshake=True,
            output_json=True,
            console=Console(),
            validate_path=lambda _p: False,
            load_config=lambda _p: None,
            check_files_accessible=lambda _p: False,
            check_fingerprints_valid=lambda _c: False,
            check_no_conflicts=lambda _c: False,
            check_artifact_consistency=lambda _p: (False, "bad"),
            run_runtime_preflight_fn=lambda _p: preflight,
        )


def test_governance_validate_json_success() -> None:
    preflight = SimpleNamespace(passed=True, reason="", details={})
    with patch(
        "providence_cli.services.governance_validate_handlers.emit_json"
    ) as emit_json:
        run_governance_validate(
            path=".providence/compiled",
            skip_handshake=True,
            output_json=True,
            console=Console(),
            validate_path=lambda _p: True,
            load_config=lambda _p: {
                "items": [{"id": "M011", "type": "MANDATE"}],
            },
            check_files_accessible=lambda _p: True,
            check_fingerprints_valid=lambda _c: True,
            check_no_conflicts=lambda _c: True,
            check_artifact_consistency=lambda _p: (True, ""),
            run_runtime_preflight_fn=lambda _p: preflight,
        )
    payload = emit_json.call_args.args[0]
    assert payload["ok"] is True
    assert "advisories" in payload["data"]


def test_governance_validate_advisories_include_analysis_classification(
    tmp_path: Path,
) -> None:
    workspace = tmp_path
    compiled = workspace / ".providence" / "compiled"
    compiled.mkdir(parents=True)
    (workspace / ".analysis").mkdir()
    (workspace / ".analysis" / "README.md").write_text(
        "# Analysis Workspace\n", encoding="utf-8"
    )
    (workspace / "docs").mkdir()
    (workspace / "docs" / "README.md").write_text(
        "Documentao estruturada por papel no sistema.\n", encoding="utf-8"
    )
    (workspace / ".providence" / "source").mkdir(parents=True)
    (workspace / ".providence" / "source" / "guidelines.dsl").write_text(
        "guideline G021 {}\nguideline G022 {}\n", encoding="utf-8"
    )

    preflight = SimpleNamespace(passed=True, reason="", details={})
    with patch(
        "providence_cli.services.governance_validate_handlers.emit_json"
    ) as emit_json:
        run_governance_validate(
            path=str(compiled),
            skip_handshake=True,
            output_json=True,
            console=Console(),
            validate_path=lambda _p: True,
            load_config=lambda _p: {
                "items": [{"id": "M011", "type": "MANDATE"}],
            },
            check_files_accessible=lambda _p: True,
            check_fingerprints_valid=lambda _c: True,
            check_no_conflicts=lambda _c: True,
            check_artifact_consistency=lambda _p: (True, ""),
            run_runtime_preflight_fn=lambda _p: preflight,
        )
    advisories = emit_json.call_args.args[0]["data"]["advisories"]
    checks = {item["check"]: item for item in advisories}
    assert (
        checks["Analysis workspace classification"]["surface"] == "workspace_local_docs"
    )
    assert checks["Mandatory docs surface language drift"]["status"] == "warn"


def test_governance_validate_text_success() -> None:
    preflight = SimpleNamespace(passed=True, reason="", details={})
    run_governance_validate(
        path=".providence/compiled",
        skip_handshake=True,
        output_json=False,
        console=Console(),
        validate_path=lambda _p: True,
        load_config=lambda _p: {"items": []},
        check_files_accessible=lambda _p: True,
        check_fingerprints_valid=lambda _c: True,
        check_no_conflicts=lambda _c: True,
        check_artifact_consistency=lambda _p: (True, ""),
        run_runtime_preflight_fn=lambda _p: preflight,
    )


def test_governance_validate_text_failure_with_handshake_guidance() -> None:
    preflight = SimpleNamespace(passed=False, reason="missing", details={})
    protocol = SimpleNamespace(is_handshake_valid=lambda: False)
    with (
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            return_value=protocol,
        ),
        pytest.raises(typer.Exit),
    ):
        run_governance_validate(
            path=".providence/compiled",
            skip_handshake=False,
            output_json=False,
            console=Console(),
            validate_path=lambda _p: True,
            load_config=lambda _p: {"items": []},
            check_files_accessible=lambda _p: True,
            check_fingerprints_valid=lambda _c: True,
            check_no_conflicts=lambda _c: True,
            check_artifact_consistency=lambda _p: (False, "bad"),
            run_runtime_preflight_fn=lambda _p: preflight,
        )
