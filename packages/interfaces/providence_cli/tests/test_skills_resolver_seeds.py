"""Unit tests for providence_cli.services.skills_resolver  registry/seed reconciliation and adapters."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.services.skills_resolver import (
    _generate_adapters,
    _read_registry_ids,
    _reconcile_root_seed_artifacts,
)


class TestReadRegistryIds:
    def test_raises_on_non_list_value(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({"commands": "not-a-list"}), encoding="utf-8")
        with pytest.raises(ValueError, match=r"invalid registry format for "):
            _read_registry_ids(reg, "commands", "id")

    def test_skips_non_dict_rows(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(
            json.dumps({"commands": ["string-row", {"id": "sdd-ask"}]}),
            encoding="utf-8",
        )
        result = _read_registry_ids(reg, "commands", "id")
        assert result == ["sdd-ask"]


class TestReconcileRootSeedArtifacts:
    def test_prunes_stale_files(self, tmp_path: Path) -> None:
        commands_registry = tmp_path / ".providence" / "commands"
        skills_registry = tmp_path / ".providence" / "skills"
        commands_registry.mkdir(parents=True, exist_ok=True)
        skills_registry.mkdir(parents=True, exist_ok=True)
        (commands_registry / "registry.json").write_text(
            json.dumps(
                {
                    "commands": [
                        {"id": "sdd-ask"},
                        {"id": "sdd-pipeline"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (skills_registry / "registry.json").write_text(
            json.dumps({"skills": [{"name": "sdd-ask"}, {"name": "sdd-diagnose"}]}),
            encoding="utf-8",
        )

        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "sdd-ask.prompt.md").write_text("ok", encoding="utf-8")
        (prompts / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

        codex_skills = tmp_path / ".codex" / "skills"
        codex_skills.mkdir(parents=True, exist_ok=True)
        (codex_skills / "sdd-pipeline.prompt.md").write_text("ok", encoding="utf-8")
        (codex_skills / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True, exist_ok=True)
        (claude_cmds / "sdd-ask.md").write_text("ok", encoding="utf-8")
        (claude_cmds / "sdd-legacy.md").write_text("stale", encoding="utf-8")

        gemini_skills = tmp_path / ".gemini" / "antigravity" / "skills"
        gemini_skills.mkdir(parents=True, exist_ok=True)
        (gemini_skills / "sdd-ask").mkdir()
        (gemini_skills / "sdd-governance").mkdir()
        (gemini_skills / "sdd-legacy").mkdir()
        stats = _reconcile_root_seed_artifacts(tmp_path)

        assert stats["deleted"] == 4
        assert (prompts / "sdd-legacy.prompt.md").exists() is False
        assert (codex_skills / "sdd-legacy.prompt.md").exists() is False
        assert (claude_cmds / "sdd-legacy.md").exists() is False
        assert (gemini_skills / "sdd-legacy").exists() is False
        assert (gemini_skills / "sdd-governance").exists() is True

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        commands_registry = tmp_path / ".providence" / "commands"
        skills_registry = tmp_path / ".providence" / "skills"
        commands_registry.mkdir(parents=True, exist_ok=True)
        skills_registry.mkdir(parents=True, exist_ok=True)
        (commands_registry / "registry.json").write_text(
            json.dumps({"commands": [{"id": "sdd-ask"}]}),
            encoding="utf-8",
        )
        (skills_registry / "registry.json").write_text(
            json.dumps({"skills": [{"name": "sdd-ask"}]}),
            encoding="utf-8",
        )
        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        stale = prompts / "sdd-legacy.prompt.md"
        stale.write_text("stale", encoding="utf-8")

        stats = _reconcile_root_seed_artifacts(tmp_path, dry_run=True)
        assert stats["would_delete"] == 1
        assert stats["deleted"] == 0
        assert stale.exists() is True

    def test_fails_without_registries(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _reconcile_root_seed_artifacts(tmp_path)


class TestGenerateAdapters:
    def test_returns_zero_on_import_error(self) -> None:
        with patch(
            "providence_adapters.adapter_generator.AdapterGenerator",
            side_effect=ImportError("no adapters"),
        ):
            count, err = _generate_adapters(Path("/tmp"))
        assert count == 0
        assert err is not None

    def test_returns_count_on_success(self, tmp_path: Path) -> None:
        with patch(
            "providence_adapters.adapter_generator.AdapterGenerator"
        ) as mock_cls:
            mock_cls.return_value.generate.return_value = [1, 2, 3]
            count, err = _generate_adapters(tmp_path)
        assert count == 3
        assert err is None
