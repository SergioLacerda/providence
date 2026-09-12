from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration._phase456_governance_io import (
    _load_governance,
    _resolve_governance_inputs,
)


def test_resolve_governance_inputs_falls_back_to_first_candidate(
    tmp_path: Path,
) -> None:
    paths = {"client_compiled": tmp_path / "client_compiled"}
    output_base = tmp_path / "out"

    core_path, client_path = _resolve_governance_inputs(tmp_path, paths, output_base)

    assert core_path == tmp_path / ".providence" / "compiled" / "governance-core.json"
    assert (
        client_path == tmp_path / ".providence" / "compiled" / "governance-client.json"
    )


def test_load_governance_returns_error_result_when_core_missing(
    tmp_path: Path,
) -> None:
    core_path = tmp_path / "missing-core.json"
    client_path = tmp_path / "missing-client.json"
    sdd_dir = tmp_path / ".providence"

    mandates, guidelines, guidelines_by_category, result = _load_governance(
        core_path, client_path, verbose=False, sdd_dir=sdd_dir
    )

    assert mandates == []
    assert guidelines == {}
    assert guidelines_by_category == {}
    assert result["errors"] == ["Failed to load governance"]
    assert result["success"] is False
    assert result["output_path"] == str(sdd_dir)
