"""Tests for seedlings generators - base, AI, governance seeds.

Covers:
- BaseSeedlingGenerator initialization
- AISeedsGenerator gemini/antigravity seed generation
- GovernanceSeedsGenerator governance seed generation
- IDE seeds generator IDE file generation
- File creation and content validation
- Error handling and logging
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from providence_wizard.orchestration.seedlings.ai_seeds import AISeedsGenerator
from providence_wizard.orchestration.seedlings.base_generator import (
    BaseSeedlingGenerator,
)
from providence_wizard.orchestration.seedlings.governance_seeds import (
    GovernanceSeedsGenerator,
)
from providence_wizard.orchestration.seedlings.ide_seeds import IDESeedsGenerator
from providence_wizard.orchestration.wizard.messages import phase3_completed_message

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_seedlings_dir(tmp_path: Path) -> Path:
    """Create a temporary seedlings directory."""
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return seedlings_dir


@pytest.fixture
def base_config() -> dict[str, Any]:
    """Create a base config dict."""
    return {
        "project_name": "Test Project",
        "language": "python",
    }


def _create_base_generator(
    tmp_path: Path,
    seedlings_dir: Path,
    config: dict[str, Any],
) -> BaseSeedlingGenerator:
    """Create a BaseSeedlingGenerator instance."""
    return BaseSeedlingGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config=config,
        spec_fingerprint="abc12345",
        mandate_ids=["M001", "M002"],
        active_categories=["testing", "performance"],
        generated_at="2026-05-12T00:00:00Z",
        verbose=False,
    )


# ---------------------------------------------------------------------------
# BaseSeedlingGenerator Tests
# ---------------------------------------------------------------------------


class TestBaseSeedlingGenerator:
    def test_initialization(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """BaseSeedlingGenerator should initialize with all attributes."""
        gen = _create_base_generator(tmp_path, tmp_seedlings_dir, base_config)
        assert gen.output_base == tmp_path
        assert gen.seedlings_dir == tmp_seedlings_dir
        assert gen.spec_fingerprint == "abc12345"
        assert gen.mandate_ids == ["M001", "M002"]
        assert gen.active_categories == ["testing", "performance"]
        assert gen.verbose is False

    def test_log_method_silent_when_verbose_false(
        self,
        tmp_path: Path,
        tmp_seedlings_dir: Path,
        base_config: dict[str, Any],
        capsys,
    ) -> None:
        """log() should not print when verbose is False."""
        gen = BaseSeedlingGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.log("test message")
        captured = capsys.readouterr()
        assert "test message" not in captured.out

    def test_log_method_prints_when_verbose_true(
        self,
        tmp_path: Path,
        tmp_seedlings_dir: Path,
        base_config: dict[str, Any],
        capsys,
    ) -> None:
        """log() should print when verbose is True."""
        gen = BaseSeedlingGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=True,
        )
        gen.log("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_mandates_list_initialized_empty(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """mandates list should be initialized as empty."""
        gen = _create_base_generator(tmp_path, tmp_seedlings_dir, base_config)
        assert gen.mandates == []

    def test_mandates_list_can_be_set(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should allow setting mandates list."""
        gen = _create_base_generator(tmp_path, tmp_seedlings_dir, base_config)
        test_mandates = [{"id": "M001", "title": "Test"}]
        gen.mandates = test_mandates
        assert gen.mandates == test_mandates


# ---------------------------------------------------------------------------
# AISeedsGenerator Tests
# ---------------------------------------------------------------------------


class TestAISeedsGeneratorGemini:
    def test_generate_gemini_seed_creates_file(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create gemini-instructions.md, GEMINI.md, settings.json and gemini.seed.json."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_gemini_seed()
        assert success is True
        assert (tmp_path / ".gemini" / "gemini-instructions.md").exists()
        assert (tmp_path / "GEMINI.md").exists()
        assert (tmp_path / ".gemini" / "settings.json").exists()
        assert (tmp_seedlings_dir / "gemini.seed.json").exists()

    def test_generate_gemini_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated gemini files should have correct content."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_gemini_seed()
        instructions = (tmp_path / ".gemini" / "gemini-instructions.md").read_text(
            encoding="utf-8"
        )
        assert "Gemini  Providence Governance Bootstrap" in instructions
        assert ".gemini/commands.md" in instructions
        assert ".providence/agent-instructions.md" in instructions

        gemini_md = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert "GEMINI.md" in gemini_md
        assert ".providence/agent-instructions.md" in gemini_md

        settings = json.loads(
            (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
        )
        assert settings.get("contextFileName") == "GEMINI.md"

        seed = json.loads(
            (tmp_seedlings_dir / "gemini.seed.json").read_text(encoding="utf-8")
        )
        assert seed["agent"] == "gemini"
        assert "GEMINI.md" in seed["required_context"]


class TestAISeedsGeneratorCodex:
    def test_generate_codex_seed_creates_file(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_codex_seed()
        assert success is True
        assert (tmp_seedlings_dir / "codex.seed.json").exists()

    def test_generate_codex_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_codex_seed()
        seed = json.loads(
            (tmp_seedlings_dir / "codex.seed.json").read_text(encoding="utf-8")
        )
        assert seed["agent"] == "codex"
        assert seed["commands_ref"] == ".codex/commands.md"
        assert ".codex/commands.md" in seed["required_context"]
        assert ".codex/skills/" not in seed["required_context"]

    def test_generate_codex_seed_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        with patch(
            "providence_wizard.orchestration.seedlings.ai_seeds.write_text_utf8",
            side_effect=OSError("disk full"),
        ):
            assert gen.generate_codex_seed() is False


class TestAISeedsGeneratorCodexHandshakeMode:
    def test_generate_codex_seed_hook_mode_keeps_hook_generation_separate(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        config = {
            "project_name": "Test Project",
            "language": "python",
            "handshake_mode": "hook",
        }
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_codex_seed() is True
        assert not (tmp_path / ".codex" / "config.toml").exists()
        assert not (tmp_path / ".codex" / "sdd-governance-inject.py").exists()

    def test_generate_codex_seed_standard_mode_unchanged(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_codex_seed() is True
        assert not (tmp_path / ".codex" / "config.toml").exists()
        assert not (tmp_path / ".codex" / "sdd-governance-inject.py").exists()


class TestAISeedsGeneratorGeminiHandshakeMode:
    def test_generate_gemini_seed_hook_mode_keeps_hook_generation_separate(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        config = {
            "project_name": "Test Project",
            "language": "python",
            "handshake_mode": "hook",
        }
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_gemini_seed() is True
        settings = json.loads(
            (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
        )
        assert settings.get("contextFileName") == "GEMINI.md"
        assert "hooks" not in settings

    def test_generate_gemini_seed_standard_mode_unchanged(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_gemini_seed() is True
        settings = json.loads(
            (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
        )
        assert settings.get("contextFileName") == "GEMINI.md"
        assert "hooks" not in settings


class TestAISeedsGeneratorCopilot:
    def test_generate_copilot_seed_creates_file(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create .github/copilot-instructions.md file."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_copilot_seed()
        assert success is True
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()

    def test_generate_copilot_seed_uses_sdd_only_redirector(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Copilot bootstrap should reference only .providence governance authority."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_copilot_seed()
        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(
            encoding="utf-8"
        )
        assert ".providence/agent-instructions.md" in content
        assert ".github/prompts/" in content
        assert "providence runtime status" in content
        assert "providence governance validate" in content
        assert ".spec.config" not in content
        assert ".../EXECUTION/" not in content

    def test_copilot_precedence_remains_sdd_only_after_instruction_regeneration(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """When both generators run, final copilot instructions must remain .providence-only."""
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_copilot_seed() is True

        # Simulate second generator pass (governance generate flow)
        generate_agent_instruction_files(
            tmp_path,
            {"items": [{"id": "M001", "type": "MANDATE", "title": "Clean"}]},
        )

        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(
            encoding="utf-8"
        )
        assert ".providence/agent-instructions.md" in content
        assert ".spec.config" not in content
        assert ".../EXECUTION/" not in content


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestIDESeedsGeneratorBasic:
    def test_ide_seeds_generator_initialization(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """IDESeedsGenerator should initialize correctly."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.output_base == tmp_path
        assert gen.config == base_config


class TestGovernanceSeedsGeneratorBasic:
    def test_governance_seeds_generator_initialization(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """GovernanceSeedsGenerator should initialize correctly."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.output_base == tmp_path
        assert gen.mandate_ids == ["M001"]

    def test_generate_governance_seed_creates_file(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create governance.seed.json file."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_governance_seed()
        assert success is True
        assert (tmp_seedlings_dir / "governance.seed.json").exists()

    def test_generate_governance_seed_content_structure(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated governance seed should have correct structure."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing", "performance"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_governance_seed()
        seed_file = tmp_seedlings_dir / "governance.seed.json"
        content = json.loads(seed_file.read_text(encoding="utf-8"))

        assert "auto_activate" in content
        assert "load_compiled_from" in content
        assert content["load_compiled_from"] == ".providence"
        assert ".providence/metadata.json" in content["required_context"]
        assert "project_metadata" in content
        assert content["project_metadata"]["spec_fingerprint"] == "abc12345"
        assert content["project_metadata"]["mandates_selected"] == ["M001", "M002"]
        assert content["schema_version"] == "1.0.0"
        assert "awakening" in content
        assert content["awakening"]["activation_profile"] == "executor"
        assert content["awakening"]["fallback_order"] == ["skills", "cli"]
        assert content["awakening"]["response_footer_policy"] == "always"
        assert "sdd-validate-governance" in content["awakening"]["skill_set"]
        assert "awakening_flow" in content

    def test_generate_compliance_seed_creates_file(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create compliance.seed.json file."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_compliance_seed()
        assert success is True
        assert (tmp_seedlings_dir / "compliance.seed.json").exists()

    def test_generate_compliance_seed_with_enforcement_modes(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate compliance seed with different enforcement modes."""
        for mode in ["silent_mode", "warn_mode", "strict_mode"]:
            config = dict(base_config)
            config["enforcement_mode"] = mode
            gen = GovernanceSeedsGenerator(
                output_base=tmp_path,
                seedlings_dir=tmp_seedlings_dir,
                config=config,
                spec_fingerprint="abc12345",
                mandate_ids=["M001"],
                active_categories=["testing"],
                generated_at="2026-05-12T00:00:00Z",
                verbose=False,
            )
            success = gen.generate_compliance_seed()
            assert success is True

            # Read and verify
            seed_file = tmp_seedlings_dir / "compliance.seed.json"
            content = json.loads(seed_file.read_text(encoding="utf-8"))
            assert "compliance_rules" in content
            assert content["load_compiled_from"] == ".providence"
            assert ".providence/metadata.json" in content["required_context"]


class TestIDESeedsGeneratorMethods:
    def test_generate_agent_prep_seed(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate agent-prep.seed.json file."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_agent_prep_seed()
        assert success is True
        assert (tmp_seedlings_dir / "agent-prep.seed.json").exists()

    def test_generate_agent_prep_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated agent-prep seed should have correct structure."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_agent_prep_seed()
        seed_file = tmp_seedlings_dir / "agent-prep.seed.json"
        content = json.loads(seed_file.read_text(encoding="utf-8"))
        assert "agent_configuration" in content
        assert content["load_compiled_from"] == ".providence"
        assert (
            content["agent_configuration"]["quick_access"]["compiled"] == ".providence"
        )
        assert ".providence/metadata.json" in content["required_context"]
        assert (
            ".providence/seedlings/personal-overlay.seed.json"
            in content["required_context"]
        )
        assert "ide_hooks" in content

    def test_generate_personal_overlay_seed(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate personal-overlay.seed.json file."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_personal_overlay_seed()
        assert success is True
        assert (tmp_seedlings_dir / "personal-overlay.seed.json").exists()

    def test_generate_personal_overlay_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated personal-overlay seed should have correct structure."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_personal_overlay_seed()
        seed_file = tmp_seedlings_dir / "personal-overlay.seed.json"
        content = json.loads(seed_file.read_text(encoding="utf-8"))
        assert content["on_load"] == "prepare_personal_overlay"
        assert ".providence/skills/registry.json" in content["required_context"]
        assert ".providence/commands/registry.json" in content["required_context"]

    def test_generate_vscode_seed(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate vscode.seed.json file."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_vscode_seed()
        assert success is True
        assert (tmp_seedlings_dir / "vscode.seed.json").exists()

    def test_generate_vscode_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated vscode seed should have correct structure."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_vscode_seed()
        seed_file = tmp_seedlings_dir / "vscode.seed.json"
        content = json.loads(seed_file.read_text(encoding="utf-8"))
        assert content["agent"] == "vscode"
        assert content["load_compiled_from"] == ".providence"
        assert content["governance_fingerprint"] == "abc12345"
        assert content["mandates_count"] == 2

    def test_generate_cursor_seed(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate cursor.seed.json file."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_cursor_seed()
        assert success is True
        assert (tmp_seedlings_dir / "cursor.seed.json").exists()

    def test_generate_cursor_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated cursor seed should have correct structure."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_cursor_seed()
        seed_file = tmp_seedlings_dir / "cursor.seed.json"
        content = json.loads(seed_file.read_text(encoding="utf-8"))
        assert content["agent"] == "cursor"
        assert content["load_compiled_from"] == ".providence"
        assert "commands_ref" in content


class TestAISeedsGeneratorClaudeSeed:
    def test_generate_claude_seed(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate CLAUDE.md file."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_claude_seed()
        assert success is True
        assert (tmp_path / "CLAUDE.md").exists()

    def test_generate_claude_seed_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated CLAUDE.md should have correct structure."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_claude_seed()
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "CRITICAL: Governance Source of Truth" in content
        assert ".claude/commands/" in content
        assert ".providence/agent-instructions.md" in content
        assert "Version: 3.0" in content
        assert (tmp_path / ".claude" / "providence-bootstrap.sh").exists()
        assert (tmp_path / ".claude" / "settings.json").exists()


class TestAISeedsGeneratorClaudeHandshakeMode:
    def test_generate_claude_seed_hook_mode_keeps_hook_generation_separate(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """AI seeds stay independent from prompt-submit hook runtime generation."""
        config = {
            "project_name": "Test Project",
            "language": "python",
            "handshake_mode": "hook",
        }
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_claude_seed() is True
        settings = json.loads(
            (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        assert "PreToolUse" in settings["hooks"]
        assert "UserPromptSubmit" not in settings["hooks"]
        assert not (tmp_path / ".claude" / "sdd-governance-inject.py").exists()

    def test_generate_claude_seed_standard_mode_unchanged(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Default config (no handshake_mode) keeps the existing PreToolUse hook."""
        gen = AISeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen.generate_claude_seed() is True
        settings = json.loads(
            (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        assert "PreToolUse" in settings["hooks"]
        assert "UserPromptSubmit" not in settings["hooks"]
        assert not (tmp_path / ".claude" / "sdd-governance-inject.py").exists()


class TestGovernanceSeedsGeneratorMethods:
    def test_generate_activation_guide(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate ACTIVATION_GUIDE.md file."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_activation_guide()
        assert success is True
        assert (tmp_seedlings_dir / "ACTIVATION_GUIDE.md").exists()

    def test_generate_activation_guide_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated activation guide should have correct structure."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_activation_guide()
        content = (tmp_seedlings_dir / "ACTIVATION_GUIDE.md").read_text(
            encoding="utf-8"
        )
        assert "Governance Activation Guide" in content
        assert "Quick Start" in content
        assert "Invocation Playbook (Skills + CLI)" in content
        assert "providence skills run sdd-validate-governance" in content
        assert "providence skills list" in content
        assert "providence skills describe sdd-validate-governance" in content
        assert "providence ask --full" in content
        assert (
            "Copy-Item -Path .providence\\seedlings -Destination . -Recurse" in content
        )
        assert "Activation Checklist" in content
        assert "providence governance hook disable" in content

    def test_generate_verification_script(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate verify.py verification script."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_verification_script()
        assert success is True
        assert (tmp_seedlings_dir / "verify.py").exists()

    def test_generate_verification_script_content(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Generated verify.py should be executable python script."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        gen.generate_verification_script()
        content = (tmp_seedlings_dir / "verify.py").read_text(encoding="utf-8")
        assert "#!/usr/bin/env python3" in content
        assert "GovernanceVerifier" in content
        assert "def main()" in content

    def test_generate_agnostic_agent_instructions(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate .providence/agent-instructions.md file."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_agnostic_agent_instructions()
        assert success is True
        instructions_file = tmp_path / ".providence" / "agent-instructions.md"
        assert instructions_file.exists()
        content = instructions_file.read_text(encoding="utf-8")
        assert "governance_fingerprint" in content

    def test_generate_agent_specific_entrypoint_contracts(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Entry points should include custom-folder + .providence governance contract."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        # Both are deprecated no-ops  verify they return True without creating files
        assert gen.generate_ai_instructions() is True
        assert gen.generate_openai_instructions() is True

        assert not (tmp_path / ".ai" / "ai-instructions.md").exists()
        assert not (tmp_path / ".openai").exists()

    def test_generate_agents_md_contract(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate root AGENTS.md with all supported agent bootstrap paths."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        assert gen.generate_agents_md() is True
        agents_file = tmp_path / "AGENTS.md"
        assert agents_file.exists()
        content = agents_file.read_text(encoding="utf-8")
        assert "## Agent-Specific Paths" in content
        assert "Codex: `./.codex/`" in content
        assert "Claude: `./CLAUDE.md`, `./.claude/commands/`" in content
        assert "Gemini: `./.gemini/`" in content
        assert (
            "GitHub Copilot: `./.github/copilot-instructions.md`, `./.github/prompts/`"
            in content
        )
        assert "OpenAI" not in content
        assert ".openai" not in content
        assert ".providence/agent-instructions.md" in content
        assert ".providence/commands/registry.json" in content
        assert ".providence/skills/registry.json" in content
        assert ".providence/commands/<command-id>/command.yaml" in content
        assert ".providence/skills/<skill-name>/skill.yaml" in content

    def test_should_auto_activate_with_standard_adoption(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """should_auto_activate should return True for standard adoption."""
        config = {"adoption_level": "standard"}
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen._should_auto_activate() is True

    def test_should_auto_activate_with_enterprise_adoption(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """should_auto_activate should return True for enterprise adoption."""
        config = {"adoption_level": "enterprise"}
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen._should_auto_activate() is True

    def test_should_auto_activate_with_lite_adoption(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """should_auto_activate should return False for lite adoption."""
        config = {"adoption_level": "lite"}
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        assert gen._should_auto_activate() is False

    def test_get_summary(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """get_summary should return dict with generation summary."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing", "performance"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        summary = gen.get_summary()
        assert "seedlings_dir" in summary
        assert "count" in summary
        assert "files" in summary
        assert "fingerprint" in summary
        assert summary["fingerprint"] == "abc12345"
        assert summary["mandates"] == ["M001", "M002"]
        assert summary["guidelines"] == ["testing", "performance"]
        assert "awareness_pack" in summary
        assert "prompt_commands_mode" in summary["awareness_pack"]


class TestGovernanceSeedsGeneratorPromptCommands:
    def test_generate_minimal_prompt_commands(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate minimal prompt commands as fallback."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen._generate_minimal_prompt_commands()
        assert success is True
        assert (tmp_path / ".cursor" / "rules" / "sdd-commands.mdc").exists()
        assert (tmp_path / ".gemini" / "commands.md").exists()
        cursor_content = (
            tmp_path / ".cursor" / "rules" / "sdd-commands.mdc"
        ).read_text(encoding="utf-8")
        gemini_content = (tmp_path / ".gemini" / "commands.md").read_text(
            encoding="utf-8"
        )
        assert 'providence ask --full "<question>"' in cursor_content
        assert "ask-full ask-full" not in cursor_content
        assert 'providence ask --full "<question>"' in gemini_content
        assert "ask-full ask-full" not in gemini_content
        summary = gen.get_summary()
        assert summary["awareness_pack"]["prompt_commands_mode"] == "fallback"


class TestIDESeedsGeneratorErrorHandling:
    def test_generate_agent_prep_seed_error_handling(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors gracefully."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            success = gen.generate_agent_prep_seed()
            assert success is False

    def test_generate_vscode_seed_error_handling(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle vscode seed generation errors gracefully."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        with patch("builtins.open", side_effect=OSError("Write failed")):
            success = gen.generate_vscode_seed()
            assert success is False

    def test_generate_cursor_seed_error_handling(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle cursor seed generation errors gracefully."""
        gen = IDESeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        with patch("builtins.open", side_effect=OSError("IO error")):
            success = gen.generate_cursor_seed()
            assert success is False


class TestBaseSeedlingGeneratorIsolation:
    def test_isolation_guard_blocks_repo_root(
        self,
        tmp_path: Path,
        tmp_seedlings_dir: Path,
        base_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Should block initialization when output_base is repo root."""
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "true")

        # Patch to make find_workspace_root return our temp path
        def mock_find_workspace_root():
            return tmp_path

        from providence_core.utils import environment

        original = environment.find_workspace_root
        environment.find_workspace_root = mock_find_workspace_root

        try:
            with pytest.raises(PermissionError, match="SDD_ISOLATION_ERROR"):
                BaseSeedlingGenerator(
                    output_base=tmp_path,  # Same as repo root
                    seedlings_dir=tmp_seedlings_dir,
                    config=base_config,
                    spec_fingerprint="abc12345",
                    mandate_ids=["M001"],
                    active_categories=["testing"],
                    generated_at="2026-05-12T00:00:00Z",
                    verbose=False,
                )
        finally:
            environment.find_workspace_root = original


#
# GovernanceSeedsGenerator  Additional Coverage Tests
#


class TestGovernanceSeedsGeneratorGeneratePromptCommands:
    def test_generate_prompt_commands(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should generate prompt command files."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        # This method tries to import providence_cli, which may not be available
        success = gen.generate_prompt_commands()
        # Should return True even if providence_cli is not available (falls back to minimal)
        assert isinstance(success, bool)

    def test_generate_prompt_commands_creates_files(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create minimal prompt command files when providence_cli unavailable."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        success = gen.generate_prompt_commands()
        assert success is True
        # Check if minimal prompt command files were created
        assert (tmp_path / ".cursor" / "rules" / "sdd-commands.mdc").exists()

    def test_generate_prompt_commands_accepts_tuple_outputs(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Prompt command generator may return list[tuple[str, Path]]."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        out_file = tmp_path / ".codex" / "commands.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("# commands", encoding="utf-8")

        class _FakeModule:
            @staticmethod
            def generate_agent_prompt_commands(*args: Any, **kwargs: Any) -> Any:
                return [("Codex/commands.md", out_file)]

        with patch(
            "providence_wizard.orchestration.seedlings.guideline_seeds.import_module",
            return_value=_FakeModule(),
        ):
            success = gen.generate_prompt_commands()

        assert success is True
        assert gen.prompt_commands_mode == "full"
        outputs = [
            path.replace("\\", "/")
            for path in gen.get_summary()["awareness_pack"]["prompt_commands_outputs"]
        ]
        assert ".codex/commands.md" in outputs


class TestGovernanceSeedsGeneratorExceptionHandling:
    def test_generate_governance_seed_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors in generate_governance_seed."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            success = gen.generate_governance_seed()
            assert success is False

    def test_generate_compliance_seed_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors in generate_compliance_seed."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        with patch("builtins.open", side_effect=OSError("IO error")):
            success = gen.generate_compliance_seed()
            assert success is False

    def test_generate_activation_guide_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors in generate_activation_guide."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        with patch("builtins.open", side_effect=OSError("OS error")):
            success = gen.generate_activation_guide()
            assert success is False

    def test_generate_verification_script_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors in generate_verification_script."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        with patch("builtins.open", side_effect=RuntimeError("Write failed")):
            success = gen.generate_verification_script()
            assert success is False

    def test_generate_agnostic_agent_instructions_handles_write_error(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should handle file write errors in generate_agnostic_agent_instructions."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            success = gen.generate_agnostic_agent_instructions()
            assert success is False


class TestGovernanceSeedsGeneratorWithMandates:
    def test_activation_guide_with_populated_mandates(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should include mandate information in activation guide."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002", "M003"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        # Populate mandates
        gen.mandates = [
            {"id": "M001", "title": "Clean Code"},
            {"id": "M002", "title": "Testing"},
            {"id": "M003", "title": "Documentation"},
        ]

        success = gen.generate_activation_guide()
        assert success is True

        content = (tmp_seedlings_dir / "ACTIVATION_GUIDE.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content or "Clean Code" in content

    def test_verification_script_with_mandate_ids(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Verification script should include mandate IDs."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        success = gen.generate_verification_script()
        assert success is True

        content = (tmp_seedlings_dir / "verify.py").read_text(encoding="utf-8")
        assert "M001" in content
        assert "M002" in content

    def test_agent_instructions_with_mandate_descriptions(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Agent instructions should include mandate descriptions."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        # Populate mandates
        gen.mandates = [
            {
                "id": "M001",
                "title": "Clean Code",
                "description": "Write clean code always",
            },
        ]

        success = gen.generate_agnostic_agent_instructions()
        assert success is True

        content = (tmp_path / ".providence" / "agent-instructions.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content
        assert "metadata-core.json" not in content
        assert "trust the compiled file" not in content
        assert "validate this against `.providence/metadata.json`" in content


class TestGovernanceSeedsGeneratorConfigVariations:
    def test_different_enforcement_modes(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """Should generate compliance seed with different enforcement modes."""
        for mode in ["silent_mode", "warn_mode", "strict_mode"]:
            config = {"enforcement_mode": mode, "language": "python"}
            gen = GovernanceSeedsGenerator(
                output_base=tmp_path / f"test_{mode}",
                seedlings_dir=tmp_seedlings_dir,
                config=config,
                spec_fingerprint="abc12345",
                mandate_ids=["M001"],
                active_categories=["testing"],
                generated_at="2026-05-12T00:00:00Z",
                verbose=False,
            )

            success = gen.generate_compliance_seed()
            assert success is True

            # Verify file was created
            assert (tmp_seedlings_dir / "compliance.seed.json").exists()

    def test_different_adoption_levels(
        self, tmp_path: Path, tmp_seedlings_dir: Path
    ) -> None:
        """Should handle different adoption levels."""
        for adoption in ["lite", "standard", "enterprise"]:
            config = {"adoption_level": adoption, "language": "python"}
            gen = GovernanceSeedsGenerator(
                output_base=tmp_path / f"test_{adoption}",
                seedlings_dir=tmp_seedlings_dir,
                config=config,
                spec_fingerprint="abc12345",
                mandate_ids=["M001"],
                active_categories=["testing"],
                generated_at="2026-05-12T00:00:00Z",
                verbose=False,
            )

            # Check auto-activate logic
            auto_activate = gen._should_auto_activate()
            if adoption == "lite":
                assert auto_activate is False
            else:
                assert auto_activate is True

    def test_different_languages(self, tmp_path: Path, tmp_seedlings_dir: Path) -> None:
        """Should handle different languages in config."""
        for language in ["python", "javascript", "go"]:
            config = {"language": language}
            gen = GovernanceSeedsGenerator(
                output_base=tmp_path / f"test_{language}",
                seedlings_dir=tmp_seedlings_dir,
                config=config,
                spec_fingerprint="abc12345",
                mandate_ids=["M001"],
                active_categories=["testing"],
                generated_at="2026-05-12T00:00:00Z",
                verbose=False,
            )

            success = gen.generate_governance_seed()
            assert success is True


class TestGovernanceSeedsGeneratorMandateVariations:
    def test_agent_instructions_with_mandates_without_descriptions(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Agent instructions should handle mandates without descriptions."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001", "M002"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        # Populate mandates with one missing description
        gen.mandates = [
            {
                "id": "M001",
                "title": "Clean Code",
                "description": "Write clean code always",
            },
            {"id": "M002", "title": "Testing"},  # No description
        ]

        success = gen.generate_agnostic_agent_instructions()
        assert success is True

        content = (tmp_path / ".providence" / "agent-instructions.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content
        assert "M002" in content

    def test_activation_guide_with_mandates_without_descriptions(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Activation guide should handle mandates without descriptions."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )
        # Mandate without description
        gen.mandates = [{"id": "M001", "title": "Clean Code"}]

        success = gen.generate_activation_guide()
        assert success is True

        content = (tmp_seedlings_dir / "ACTIVATION_GUIDE.md").read_text(
            encoding="utf-8"
        )
        assert "M001" in content or "Clean Code" in content


class TestGovernanceSeedsGeneratorPromptCommandsExceptions:
    def test_generate_prompt_commands_import_error_fallback(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should return result from generate_prompt_commands (which uses try/except)."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        # generate_prompt_commands will try to import providence_cli and fall back to minimal
        # Since providence_cli is likely not available, this should succeed by using minimal
        success = gen.generate_prompt_commands()
        assert isinstance(success, bool)

    def test_generate_prompt_commands_creates_fallback_files(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create minimal prompt command files as fallback."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        success = gen.generate_prompt_commands()
        assert success is True
        assert gen.get_summary()["awareness_pack"]["prompt_commands_mode"] in {
            "fallback",
            "full",
        }
        # Verify at least one of the fallback files was created
        assert (tmp_path / ".cursor" / "rules" / "sdd-commands.mdc").exists() or (
            tmp_path / ".gemini" / "commands.md"
        ).exists()

    def test_generate_minimal_prompt_commands_creates_files(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """Should create minimal prompt command files."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        success = gen._generate_minimal_prompt_commands()
        assert success is True

        # Verify files were created
        assert (tmp_path / ".cursor" / "rules" / "sdd-commands.mdc").exists()
        assert (tmp_path / ".gemini" / "commands.md").exists()

    def test_generate_prompt_commands_returns_boolean(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        """generate_prompt_commands should always return a boolean."""
        gen = GovernanceSeedsGenerator(
            output_base=tmp_path,
            seedlings_dir=tmp_seedlings_dir,
            config=base_config,
            spec_fingerprint="abc12345",
            mandate_ids=["M001"],
            active_categories=["testing"],
            generated_at="2026-05-12T00:00:00Z",
            verbose=False,
        )

        result = gen.generate_prompt_commands()
        assert isinstance(result, bool)
        assert result is True


# ---------------------------------------------------------------------------
# IntelligentSeedlingsGenerator Tests
# ---------------------------------------------------------------------------


class TestIntelligentSeedlingsGeneratorFingerprintFallback:
    """Test IntelligentSeedlingsGenerator._compute_fingerprint() exception handling.

    Covers the nosec B110 exception handler at orchestration/intelligent_seedlings_generator.py:83.
    Verifies that missing or corrupted governance-core.json returns the fallback "00000000".
    """

    def test_compute_fingerprint_returns_default_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """_compute_fingerprint() should return "00000000" when governance file doesn't exist."""
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        # governance_core_path points to non-existent file
        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=tmp_path / "nonexistent.json",
            verbose=False,
        )

        # Should return fallback fingerprint
        assert generator.spec_fingerprint == "00000000"


class TestIntelligentSeedlingsGeneratorCodex:
    def test_generate_all_with_codex_selection_creates_codex_seed(
        self, tmp_path: Path
    ) -> None:
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        governance_core_path = tmp_path / "governance-core.json"
        governance_core_path.write_text(
            json.dumps({"version": "3.0", "items": [{"id": "M001"}]}),
            encoding="utf-8",
        )

        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[{"id": "M001", "title": "Clean Code"}],
            guidelines_by_category={},
            config={},
            governance_core_path=governance_core_path,
            verbose=False,
        )

        assert generator.generate_all(selected={"codex"}) is True
        codex_seed = tmp_path / ".providence" / "seedlings" / "codex.seed.json"
        assert codex_seed.exists()
        manifest = json.loads(
            (tmp_path / "DEPLOYMENT_MANIFEST.json").read_text(encoding="utf-8")
        )
        assert ".providence/seedlings/codex.seed.json" in manifest.get("seed_files", {})

    def test_generate_all_full_includes_codex_seed(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        governance_core_path = tmp_path / "governance-core.json"
        governance_core_path.write_text(
            json.dumps(
                {
                    "version": "3.0",
                    "items": [
                        {"id": "M001", "type": "MANDATE", "title": "Clean Code"},
                        {"id": "G001", "type": "GUIDELINE", "title": "Test"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "AGENTS.md").write_text("bootstrap", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("bootstrap", encoding="utf-8")
        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "sdd-ask.prompt.md").write_text("x", encoding="utf-8")
        cursor_dir = tmp_path / ".cursor" / "rules"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        (cursor_dir / "sdd-commands.mdc").write_text("x", encoding="utf-8")
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        (gemini_dir / "commands.md").write_text("x", encoding="utf-8")

        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[{"id": "M001", "title": "Clean Code"}],
            guidelines_by_category={"testing": [{"id": "G001", "title": "Test"}]},
            config={},
            governance_core_path=governance_core_path,
            verbose=False,
        )

        with (
            patch.object(
                generator.gov_gen, "generate_prompt_commands", return_value=True
            ),
            patch.object(
                generator.sovereign_gen,
                "generate_sovereign_factory_seed",
                return_value=True,
            ),
        ):
            assert generator.generate_all(selected=None) is True
        assert (tmp_path / ".providence" / "seedlings" / "codex.seed.json").exists()

    def test_compute_fingerprint_returns_default_when_json_corrupted(
        self, tmp_path: Path
    ) -> None:
        """_compute_fingerprint() should return "00000000" when JSON is malformed."""
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        # Create corrupted JSON file
        governance_core_path = tmp_path / "governance-core.json"
        governance_core_path.write_text("{invalid json{{", encoding="utf-8")

        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=governance_core_path,
            verbose=False,
        )

        # Should catch JSON error and return fallback
        assert generator.spec_fingerprint == "00000000"

    def test_compute_fingerprint_returns_hash_when_valid(self, tmp_path: Path) -> None:
        """_compute_fingerprint() should return SHA256 hash when JSON is valid."""
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        # Create valid governance-core.json
        governance_data = {"version": "3.0", "items": [{"id": "M001"}]}
        governance_core_path = tmp_path / "governance-core.json"
        governance_core_path.write_text(json.dumps(governance_data), encoding="utf-8")

        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=governance_core_path,
            verbose=False,
        )

        # Should compute and return 8-char hex hash (not the fallback)
        assert generator.spec_fingerprint != "00000000"
        assert len(generator.spec_fingerprint) == 8
        assert all(c in "0123456789abcdef" for c in generator.spec_fingerprint)

    def test_awareness_pack_reports_missing_artifacts(self, tmp_path: Path) -> None:
        from providence_wizard.orchestration.intelligent_seedlings_generator import (
            IntelligentSeedlingsGenerator,
        )

        governance_data = {"version": "3.0", "items": [{"id": "M001"}]}
        governance_core_path = tmp_path / "governance-core.json"
        governance_core_path.write_text(json.dumps(governance_data), encoding="utf-8")

        generator = IntelligentSeedlingsGenerator(
            output_base=tmp_path,
            mandates=[],
            guidelines_by_category={},
            config={},
            governance_core_path=governance_core_path,
            verbose=False,
        )
        awareness = generator._validate_awareness_pack()
        assert awareness["status"] == "incomplete"
        assert ".github/prompts/*.prompt.md" in awareness["missing_items"]


class TestWizardMessagesConsistency:
    def test_phase3_message_uses_sdd_seedlings_path_only(self) -> None:
        content = phase3_completed_message()
        assert ".providence/seedlings/" in content
        assert ".ai\\seedlings" not in content  # legacy-path-ok: asserting absence
        assert "STEP 6: PASTE THIS IN YOUR AGENT PROMPT" in content
        assert "Read `AGENTS.md`, `.providence/agent-instructions.md`" in content

    def test_phase3_message_instructs_agent_to_complete_handshake(self) -> None:
        """Regression: the wizard's paste-into-agent prompt must instruct the
        agent to complete the M015 handshake itself (see
        wizard-handshake-init-eval-20260706  wizard-side auto-completion was
        evaluated and rejected; agents must be instructed instead)."""
        content = phase3_completed_message()
        assert "providence governance handshake --init" in content
        assert "providence governance handshake --response" in content
        assert "understood_mandates" in content
        assert "acknowledged_signature" in content


class TestRootReadmeOnboarding:
    def test_readme_contains_agent_onboarding_commands(self) -> None:
        content = Path("README.md").read_text(encoding="utf-8")
        assert "Agent Onboarding After Governance Activation" in content
        assert "providence skills list" in content
        assert "providence skills describe sdd-validate-governance" in content
        assert "providence skills run sdd-validate-governance" in content


# ---------------------------------------------------------------------------
# AISeedsGenerator  exception-path coverage (lines 118-120, 177-179,
# 263-265, 344-346)
# ---------------------------------------------------------------------------


def _ai_gen(tmp_path: Path, seedlings_dir: Path, config: dict) -> AISeedsGenerator:  # type: ignore[type-arg]
    return AISeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config=config,
        spec_fingerprint="abc12345",
        mandate_ids=["M001"],
        active_categories=["testing"],
        generated_at="2026-05-19T00:00:00Z",
        verbose=False,
    )


class TestAISeedsExceptionPaths:
    def test_gemini_exception_returns_false(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = _ai_gen(tmp_path, tmp_seedlings_dir, base_config)
        with patch(
            "providence_wizard.orchestration.seedlings.ai_seeds.write_text_utf8",
            side_effect=OSError("disk full"),
        ):
            result = gen.generate_gemini_seed()
        assert result is False

    def test_copilot_exception_returns_false(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = _ai_gen(tmp_path, tmp_seedlings_dir, base_config)
        with patch(
            "providence_wizard.orchestration.seedlings.ai_seeds.write_text_utf8",
            side_effect=OSError("disk full"),
        ):
            result = gen.generate_copilot_seed()
        assert result is False

    def test_claude_exception_returns_false(
        self, tmp_path: Path, tmp_seedlings_dir: Path, base_config: dict[str, Any]
    ) -> None:
        gen = _ai_gen(tmp_path, tmp_seedlings_dir, base_config)
        with patch(
            "providence_wizard.orchestration.seedlings.ai_seeds.write_text_utf8",
            side_effect=OSError("disk full"),
        ):
            result = gen.generate_claude_seed()
        assert result is False
