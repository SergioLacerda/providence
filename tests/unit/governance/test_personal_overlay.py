from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.governance.personal_overlay import resolve_personal_overlay

pytestmark = pytest.mark.unit


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_sdd(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".providence" / "skills" / "registry.json",
        {
            "schema_version": "1.0.0",
            "skills": [
                {
                    "name": "sdd-ask",
                    "skill_yaml": ".providence/skills/sdd-ask/skill.yaml",
                }
            ],
        },
    )
    _write_json(
        tmp_path / ".providence" / "commands" / "registry.json",
        {
            "schema_version": "1.0.0",
            "commands": [{"id": "sdd-ask", "slash": "/sdd-ask"}],
        },
    )
    (tmp_path / ".providence" / "skills" / "sdd-ask" / "skill.yaml").parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / ".providence" / "skills" / "sdd-ask" / "skill.yaml").write_text(
        "name: sdd-ask\n", encoding="utf-8"
    )
    (tmp_path / ".providence" / "commands" / "sdd-ask" / "command.yaml").parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / ".providence" / "commands" / "sdd-ask" / "command.yaml").write_text(
        "id: sdd-ask\n", encoding="utf-8"
    )


def test_resolves_local_and_sdd_without_conflict(tmp_path: Path) -> None:
    _make_sdd(tmp_path)
    local_skill = tmp_path / ".agents" / "skills" / "local-skill" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text("# local\n", encoding="utf-8")

    result = resolve_personal_overlay(
        project_root=tmp_path,
        personal_root_candidates=[tmp_path / ".agents"],
    )

    assert [item["name"] for item in result["skills_local"]] == ["local-skill"]
    assert [item["name"] for item in result["skills_sdd"]] == ["sdd-ask"]
    assert [item["id"] for item in result["effective_commands"]] == ["sdd-ask"]
    assert result["drift_events"] == []


def test_sdd_wins_when_skill_name_conflicts(tmp_path: Path) -> None:
    _make_sdd(tmp_path)
    local_skill = tmp_path / ".agents" / "skills" / "sdd-ask" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text("# local shadow\n", encoding="utf-8")

    result = resolve_personal_overlay(
        project_root=tmp_path,
        personal_root_candidates=[tmp_path / ".agents"],
    )

    effective = {item["name"]: item for item in result["effective_skills"]}
    assert effective["sdd-ask"]["source"] == ".providence"
    assert result["conflicts"][0]["name"] == "sdd-ask"
    assert result["conflicts"][0]["winner"] == ".providence"


def test_missing_registry_degrades_with_drift(tmp_path: Path) -> None:
    local_skill = tmp_path / ".agents" / "skills" / "solo" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text("# solo\n", encoding="utf-8")

    result = resolve_personal_overlay(
        project_root=tmp_path,
        personal_root_candidates=[tmp_path / ".agents"],
    )

    assert [item["name"] for item in result["effective_skills"]] == ["solo"]
    assert result["effective_commands"] == []
    codes = {item["code"] for item in result["drift_events"]}
    assert "missing_file" in codes


def test_missing_canonical_file_registers_drift_and_continues(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".providence" / "skills" / "registry.json",
        {
            "skills": [
                {
                    "name": "sdd-missing",
                    "skill_yaml": ".providence/skills/sdd-missing/skill.yaml",
                }
            ]
        },
    )
    _write_json(
        tmp_path / ".providence" / "commands" / "registry.json",
        {"commands": [{"id": "sdd-missing"}]},
    )

    result = resolve_personal_overlay(
        project_root=tmp_path,
        personal_root_candidates=[tmp_path / ".agents"],
    )

    assert result["skills_sdd"] == []
    assert result["effective_commands"] == []
    codes = {item["code"] for item in result["drift_events"]}
    assert "missing_canonical_file" in codes
