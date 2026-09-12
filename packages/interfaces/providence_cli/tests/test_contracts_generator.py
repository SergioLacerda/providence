"""Tests for `providence_cli.generators._contracts`."""

from __future__ import annotations

from pathlib import Path

from providence_cli.generators._contracts import generate_contracts


def test_generate_contracts_writes_expected_files(tmp_path: Path) -> None:
    report = generate_contracts(str(tmp_path), {})

    contracts_dir = tmp_path / ".providence" / "contracts"
    assert report["contracts_dir"] == str(contracts_dir)
    assert report["files_written"] == 3
    assert len(report["files"]) == 3

    expected_files = {
        "analysis-provider.schema.yaml",
        "mission-contract.schema.yaml",
        "mission-result.schema.yaml",
    }
    assert {path.name for path in contracts_dir.iterdir()} == expected_files
    assert "analysis_orchestrator" in (
        contracts_dir / "analysis-provider.schema.yaml"
    ).read_text(encoding="utf-8")
