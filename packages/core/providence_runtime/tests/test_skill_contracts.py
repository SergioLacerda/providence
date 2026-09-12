from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from providence_runtime import _skill_contracts as sc
from providence_runtime._skill_contracts import SkillDefinition


def test_is_deprecation_due_none_invalid_and_past() -> None:
    assert sc._is_deprecation_due(None) is False
    assert sc._is_deprecation_due("not-a-date") is False
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert sc._is_deprecation_due(past) is True
    assert sc._is_deprecation_due(future) is False


def test_skill_definition_to_dict_sets_schema_and_due_flag() -> None:
    sd = SkillDefinition(
        name="s1",
        version="1.0.0",
        category="analysis",
        description="d",
        when_to_use=["x"],
        outcomes=["o"],
        allowed_tools=["t"],
        cli_fallback=["c"],
        required_permissions=["p"],
        deprecated_after="1900-01-01T00:00:00Z",
    )
    payload = sd.to_dict()
    assert payload["schema_version"] == "1.1.0"
    assert payload["deprecation_due"] is True


def test_skill_definition_capability_id_defaults_to_none() -> None:
    sd = SkillDefinition(
        name="s1",
        version="1.0.0",
        category="analysis",
        description="d",
        when_to_use=["x"],
        outcomes=["o"],
        allowed_tools=["t"],
        cli_fallback=["c"],
        required_permissions=["p"],
    )
    assert sd.capability_id is None
    assert sd.to_dict()["capability_id"] is None


def test_skill_definition_capability_id_roundtrips_through_to_dict() -> None:
    sd = SkillDefinition(
        name="s1",
        version="1.0.0",
        category="analysis",
        description="d",
        when_to_use=["x"],
        outcomes=["o"],
        allowed_tools=["t"],
        cli_fallback=["c"],
        required_permissions=["p"],
        capability_id="diagnose",
    )
    assert sd.capability_id == "diagnose"
    assert sd.to_dict()["capability_id"] == "diagnose"


def test_skill_definition_to_yaml_success_and_missing_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sd = SkillDefinition(
        name="s1",
        version="1.0.0",
        category="analysis",
        description="d",
        when_to_use=["x"],
        outcomes=["o"],
        allowed_tools=["t"],
        cli_fallback=["c"],
        required_permissions=["p"],
    )
    text = sd.to_yaml()
    assert "schema_version" in text
    monkeypatch.setattr(sc, "yaml", None)
    with pytest.raises(ImportError, match="PyYAML is required"):
        sd.to_yaml()
