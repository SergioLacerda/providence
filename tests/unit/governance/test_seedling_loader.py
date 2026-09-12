from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.governance.seedling_loader import SeedlingLoader

pytestmark = pytest.mark.unit


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_runtime_overlay_prereqs(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".providence" / "skills" / "registry.json",
        {
            "skills": [
                {
                    "name": "sdd-ask",
                    "skill_yaml": ".providence/skills/sdd-ask/skill.yaml",
                }
            ]
        },
    )
    _write_json(
        tmp_path / ".providence" / "commands" / "registry.json",
        {"commands": [{"id": "sdd-ask"}]},
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
    local_skill = tmp_path / ".agents" / "skills" / "local" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text("# local\n", encoding="utf-8")


def test_execute_prepare_personal_overlay_creates_runtime_state(tmp_path: Path) -> None:
    _make_runtime_overlay_prereqs(tmp_path)
    loader = SeedlingLoader(tmp_path)
    seed = {
        "auto_activate": True,
        "required_context": [
            ".providence/skills/registry.json",
            ".providence/commands/registry.json",
        ],
        "on_load": "prepare_personal_overlay",
        "triggers": ["on_project_load"],
    }

    assert loader.execute_seed(seed) is True
    state_file = tmp_path / ".providence" / "runtime" / "personal-overlay-state.json"
    assert state_file.exists()
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert "effective_skills" in payload
    assert "effective_commands" in payload


def test_invalid_seed_shape_does_not_break_load_all(tmp_path: Path) -> None:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    (seedlings_dir / "broken.seed.json").write_text(
        json.dumps({"on_load": "prepare_personal_overlay"}),
        encoding="utf-8",
    )
    loader = SeedlingLoader(tmp_path)
    assert loader.load_all() == []
