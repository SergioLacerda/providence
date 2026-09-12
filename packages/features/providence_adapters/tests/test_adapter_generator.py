"""Tests for AdapterGenerator."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from providence_adapters.adapter_generator import AdapterGenerator, AdapterResult


def test_generate_collects_results_for_all_targets(tmp_path: Path, monkeypatch) -> None:
    generator = AdapterGenerator()

    def _fake_generate(target: str, output_dir: Path) -> AdapterResult:
        return AdapterResult(target=target, files_written=[str(output_dir / target)])

    monkeypatch.setattr(generator, "_generate_for_target", _fake_generate)

    results = generator.generate(tmp_path)

    assert set(results) == {"claude", "codex", "copilot", "antigravity"}
    assert results["claude"].success is True


def test_generate_captures_target_exception(tmp_path: Path, monkeypatch) -> None:
    generator = AdapterGenerator()

    def _fake_generate(target: str, _output_dir: Path) -> AdapterResult:
        if target == "codex":
            raise RuntimeError("boom")
        return AdapterResult(target=target)

    monkeypatch.setattr(generator, "_generate_for_target", _fake_generate)

    results = generator.generate(tmp_path)

    assert results["codex"].success is False
    assert results["codex"].errors == ["boom"]


def test_generate_for_target_writes_skills_and_filtered_commands(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(
        generator.skill_loader,
        "load_skills",
        lambda _sdd_dir: [{"name": "diagnose"}],
    )
    monkeypatch.setattr(
        generator.skill_loader,
        "load_commands",
        lambda _sdd_dir: [
            {"id": "allowed", "targets": ["claude"]},
            {"id": "blocked", "targets": ["codex"]},
        ],
    )
    monkeypatch.setattr(
        generator,
        "_render_skill_adapter",
        lambda target, skill, agent_dir: agent_dir / f"{skill['name']}-{target}",
    )
    monkeypatch.setattr(
        generator,
        "_render_command_adapter",
        lambda target, command, agent_dir: agent_dir / f"{command['id']}-{target}",
    )

    result = generator._generate_for_target("claude", tmp_path)

    assert result.success is True
    assert any("diagnose-claude" in path for path in result.files_written)
    assert any("allowed-claude" in path for path in result.files_written)
    assert all("blocked-claude" not in path for path in result.files_written)
    assert (tmp_path / ".claude" / "commands").exists()


def test_generate_for_antigravity_writes_targeted_command_surface(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(generator.skill_loader, "load_skills", lambda _sdd_dir: [])
    monkeypatch.setattr(
        generator.skill_loader,
        "load_commands",
        lambda _sdd_dir: [
            {
                "id": "sdd-organize",
                "adapter_targets": ["antigravity"],
                "routes_to": {"type": "cli", "command": "providence organize"},
            }
        ],
    )

    result = generator._generate_for_target("antigravity", tmp_path)

    assert result.success is True
    target = (
        tmp_path / ".gemini" / "antigravity" / "skills" / "sdd-organize" / "SKILL.md"
    )
    assert str(target) in result.files_written
    content = target.read_text(encoding="utf-8")
    assert "name: sdd-organize" in content
    assert ".providence/commands/sdd-organize/command.yaml" in content
    assert "`providence organize`" in content
    assert "intake_index_mode: none" in content


def test_generate_for_antigravity_keeps_registry_command_targets_truthful(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".providence"
    commands_dir = sdd_dir / "commands" / "sdd-organize"
    skills_dir = sdd_dir / "skills" / "sdd-ask"
    commands_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    (sdd_dir / "commands" / "registry.json").write_text(
        json.dumps(
            {
                "commands": [
                    {
                        "id": "sdd-organize",
                        "slash": "/sdd-organize",
                        "routes_to": {"type": "cli", "command": "providence organize"},
                        "adapter_targets": ["antigravity"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (commands_dir / "command.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "sdd-organize",
                "slash": "/sdd-organize",
                "routes_to": {"type": "cli", "command": "providence organize"},
                "adapter_targets": ["antigravity"],
            }
        ),
        encoding="utf-8",
    )
    (sdd_dir / "skills" / "registry.json").write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "name": "sdd-ask",
                        "description": "Ask governance.",
                        "risk_score": "controlled",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (skills_dir / "skill.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "sdd-ask",
                "description": "Ask governance.",
                "when_to_use": ["governance query"],
                "allowed_tools": ["providence ask"],
                "risk_score": "controlled",
            }
        ),
        encoding="utf-8",
    )

    result = AdapterGenerator()._generate_for_target("antigravity", tmp_path)

    command_surface = (
        tmp_path / ".gemini" / "antigravity" / "skills" / "sdd-organize" / "SKILL.md"
    )
    skill_surface = (
        tmp_path / ".gemini" / "antigravity" / "skills" / "sdd-ask" / "SKILL.md"
    )
    assert result.success is True
    assert command_surface.exists()
    assert skill_surface.exists()
    assert (
        ".providence/commands/sdd-organize/command.yaml"
        in command_surface.read_text(encoding="utf-8")
    )


def test_generate_for_target_marks_skill_render_error(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(
        generator.skill_loader,
        "load_skills",
        lambda _sdd_dir: [{"name": "diagnose"}],
    )
    monkeypatch.setattr(generator.skill_loader, "load_commands", lambda _sdd_dir: [])

    def _boom(*_args, **_kwargs):
        raise RuntimeError("skill fail")

    monkeypatch.setattr(generator, "_render_skill_adapter", _boom)

    result = generator._generate_for_target("claude", tmp_path)

    assert result.success is False
    assert result.errors == ["Failed to render skill diagnose: skill fail"]


def test_generate_for_target_marks_command_render_error(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(generator.skill_loader, "load_skills", lambda _sdd_dir: [])
    monkeypatch.setattr(
        generator.skill_loader,
        "load_commands",
        lambda _sdd_dir: [{"id": "diagnose", "targets": ["claude"]}],
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("cmd fail")

    monkeypatch.setattr(generator, "_render_command_adapter", _boom)

    result = generator._generate_for_target("claude", tmp_path)

    assert result.success is False
    assert result.errors == ["Failed to render command diagnose: cmd fail"]


def test_render_command_adapter_claude_uses_command_template(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    captured: dict[str, object] = {}

    def _render(target: str, template_name: str, **context: object) -> str:
        captured["target"] = target
        captured["template_name"] = template_name
        captured["context"] = context
        return "content"

    monkeypatch.setattr(generator.renderer, "render", _render)

    output = generator._render_command_adapter("claude", {"id": "diag"}, tmp_path)

    assert output.read_text(encoding="utf-8") == "content"
    assert captured["template_name"] == "command.md"
    assert "skill" in captured["context"]


def test_render_command_adapter_codex_uses_command_context(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    captured: dict[str, object] = {}

    def _render(target: str, template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "content"

    monkeypatch.setattr(generator.renderer, "render", _render)

    output = generator._render_command_adapter("codex", {"id": "diag"}, tmp_path)

    assert output.name == "diag.prompt.md"
    assert captured["template_name"] == "command.prompt.md"
    assert "command" in captured["context"]


def test_render_command_adapter_antigravity_creates_subdir(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(
        generator.renderer, "render", lambda *_args, **_kwargs: "content"
    )

    output = generator._render_command_adapter("antigravity", {"id": "diag"}, tmp_path)

    assert output == tmp_path / "diag" / "SKILL.md"
    assert output.read_text(encoding="utf-8") == "content"


def test_render_skill_adapter_creates_antigravity_subdir(
    tmp_path: Path, monkeypatch
) -> None:
    generator = AdapterGenerator()
    monkeypatch.setattr(generator.renderer, "render", lambda *_args, **_kwargs: "skill")

    output = generator._render_skill_adapter(
        "antigravity", {"name": "diagnose"}, tmp_path
    )

    assert output == tmp_path / "diagnose" / "SKILL.md"
    assert output.read_text(encoding="utf-8") == "skill"


def test_render_skill_adapter_uses_codex_template(tmp_path: Path, monkeypatch) -> None:
    generator = AdapterGenerator()
    captured: dict[str, object] = {}

    def _render(target: str, template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "skill"

    monkeypatch.setattr(generator.renderer, "render", _render)

    output = generator._render_skill_adapter("codex", {"name": "diagnose"}, tmp_path)

    assert output.name == "diagnose.prompt.md"
    assert captured["template_name"] == "skill.prompt.md"
    assert "skill" in captured["context"]
