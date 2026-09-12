from __future__ import annotations

from pathlib import Path


def test_skills_command_does_not_use_subprocess_engine() -> None:
    skills_cmd = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "providence_cli"
        / "commands"
        / "skills.py"
    )
    content = skills_cmd.read_text(encoding="utf-8")
    assert "subprocess" not in content
    assert "shlex" not in content
    assert "SkillEngine" in content
