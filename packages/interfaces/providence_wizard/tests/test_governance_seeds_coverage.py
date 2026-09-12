"""Coverage tests for governance_seeds.py exception paths and guard clauses."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from providence_wizard.orchestration.seedlings.governance_seeds import (
    GovernanceSeedsGenerator,
)


def _make_gen(
    tmp_path: Path, config: dict[str, Any] | None = None
) -> GovernanceSeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True)
    return GovernanceSeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config=config or {"language": "Python", "enforcement_mode": "warn_mode"},
        spec_fingerprint="abc12345",
        mandate_ids=["M001", "M002"],
        active_categories=["testing", "security"],
        generated_at="2026-05-19T00:00:00Z",
        verbose=False,
    )


class TestGovernanceSeedsStrictMode:
    def test_strict_mode_includes_review_architecture(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path, config={"enforcement_mode": "strict_mode"})
        skills = gen._resolve_skill_set()
        assert "sdd-review-architecture" in skills

    def test_warn_mode_excludes_review_architecture(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        skills = gen._resolve_skill_set()
        assert "sdd-review-architecture" not in skills


class TestGovernanceSeedsExceptionPaths:
    def test_generate_minimal_prompt_commands_exception_returns_false(
        self, tmp_path: Path
    ) -> None:
        gen = _make_gen(tmp_path)
        # Patch write_text at the Path level for this specific module
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            result = gen._generate_minimal_prompt_commands()
        assert result is False

    def test_generate_ai_instructions_is_deprecated_no_op(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        # Deprecated method: no files written, always returns True
        result = gen.generate_ai_instructions()
        assert result is True

    def test_generate_openai_instructions_is_noop(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        # generate_openai_instructions is a deprecated no-op  always returns True
        # without creating any files, even when disk operations would fail
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            result = gen.generate_openai_instructions()
        assert result is True
        assert not (tmp_path / ".openai").exists()

    def test_generate_agents_md_exception_returns_false(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            result = gen.generate_agents_md()
        assert result is False


class TestGovernanceSeedsGetSummary:
    def test_summary_includes_agents_md_when_present(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Agents", encoding="utf-8")
        status = gen.get_summary()
        assert any("AGENTS.md" in f for f in status.get("files", []))

    def test_summary_includes_prompt_commands_when_set(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        gen._prompt_commands_outputs = ["prompt-commands/ask.md"]  # type: ignore[attr-defined]
        status = gen.get_summary()
        assert any("prompt commands" in f for f in status.get("files", []))
