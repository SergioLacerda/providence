import json
from pathlib import Path

import pytest

from providence_integration.builders.governance.pipeline_builder import PipelineBuilder


def test_build_with_parsed_items():
    parsed = {
        "mandates": [
            {"id": "M001", "title": "Mandate 1", "status": "required"},
            {"id": "M002", "title": "Mandate 2", "status": "optional"},
        ],
        "guidelines": [{"id": "G001", "title": "Guideline 1", "status": "required"}],
    }
    builder = PipelineBuilder(spec_path="/tmp", parsed_items=parsed)
    result = builder.build()
    assert "governance_core" in result
    assert "governance_client" in result
    assert len(result["core_items"]) == 2
    assert len(result["client_items"]) == 1
    assert result["core_items"][0]["id"] == "M001"
    assert result["client_items"][0]["id"] == "G001"
    assert result["governance_core"]["fingerprint"]
    assert result["governance_client"]["fingerprint"]


def test_generate_fingerprint_empty_and_salt():
    from providence_integration.builders.governance.fingerprinter import (
        GovernanceFingerprinter,
    )

    # Empty items, no salt
    assert GovernanceFingerprinter.generate([], "") == "empty"
    # Empty items, with salt
    fp = GovernanceFingerprinter.generate([], "abc")
    assert fp != "empty"
    assert len(fp) == 64


def test_save_outputs(tmp_path):
    parsed = {"mandates": [{"id": "M001", "title": "Mandate 1"}], "guidelines": []}
    builder = PipelineBuilder(spec_path=str(tmp_path), parsed_items=parsed)
    builder.build()
    out = builder.save_outputs(str(tmp_path))
    assert Path(out["governance_core"]).exists()
    assert Path(out["governance_client"]).exists()
    with open(out["governance_core"], encoding="utf-8") as f:
        data = json.load(f)
        assert data["category"] == "CORE"
        assert data["items"][0]["id"] == "M001"
    with open(out["governance_client"], encoding="utf-8") as f:
        data = json.load(f)
        assert data["category"] == "CLIENT"


def test_build_file_not_found(tmp_path):
    builder = PipelineBuilder(spec_path=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        builder.build()


def test_save_outputs_preserves_non_empty_guideline_title_from_dsl(tmp_path):
    (tmp_path / "mandate.md").write_text("# M001: Mandate\n", encoding="utf-8")
    (tmp_path / "guidelines.dsl").write_text(
        """
guideline G001 {
  title: "Readable naming"
  description: "Prefer explicit names."
}
""".strip(),
        encoding="utf-8",
    )

    builder = PipelineBuilder(spec_path=str(tmp_path))
    builder.build()
    out = builder.save_outputs(str(tmp_path))

    with open(out["governance_client"], encoding="utf-8") as f:
        data = json.load(f)
    guideline = data["items"][0]
    assert guideline["id"] == "G001"
    assert guideline["title"] == "Readable naming"
    assert guideline["description"] == "Prefer explicit names."
