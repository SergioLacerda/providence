"""Tests for OutputValidator (phase6_output_validator.py)."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.phase6_output_validator import OutputValidator
from providence_wizard.orchestration.prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
)


def _make_validator(
    tmp_path: Path,
    categories: list[str] | None = None,
    config: dict | None = None,
    selected_seedlings: set[str] | None = None,
) -> OutputValidator:
    sdd = tmp_path / ".providence"
    return OutputValidator(
        output_base=tmp_path,
        sdd_dir=sdd,
        source_dir=sdd / "source",
        runtime_dir=sdd / "runtime",
        mandates_dir=sdd / "source" / "mandates",
        guidelines_dir=sdd / "source" / "guidelines",
        guidelines_by_category={c: [] for c in (categories or [])},
        config=config or {},
        verbose=False,
        selected_seedlings=selected_seedlings,
    )


def _create_all_required(tmp_path: Path, categories: list[str] | None = None) -> None:
    sdd = tmp_path / ".providence"
    (sdd / "source" / "mandates").mkdir(parents=True)
    (sdd / "source" / "guidelines").mkdir(parents=True)
    (sdd / "runtime").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (sdd / "source" / "mandates" / "mandates.md").write_text("# M", encoding="utf-8")
    (sdd / "runtime" / "README.md").write_text("# R", encoding="utf-8")
    (sdd / "source" / "README.md").write_text("# S", encoding="utf-8")
    (sdd / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".github" / "copilot-instructions.md").write_text("x", encoding="utf-8")
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    (tmp_path / ".cursor" / "rules" / "spec.mdc").write_text("x", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "claude-instructions.md").write_text("x", encoding="utf-8")
    (tmp_path / ".gemini").mkdir()
    (tmp_path / ".gemini" / "gemini-instructions.md").write_text("x", encoding="utf-8")
    for cat in categories or []:
        (sdd / "source" / "guidelines" / f"{cat}.md").write_text(
            f"# {cat}", encoding="utf-8"
        )


def _create_prompt_submit_hooks(tmp_path: Path) -> None:
    (tmp_path / ".providence" / "runtime" / "hooks").mkdir(parents=True)
    (tmp_path / ".providence" / "runtime" / "hooks" / "prompt-submit.py").write_text(
        "#!/usr/bin/env python3\n", encoding="utf-8"
    )
    (tmp_path / ".claude" / "settings.json").write_text(
        CENTRAL_PROMPT_SUBMIT_COMMAND, encoding="utf-8"
    )
    (tmp_path / ".codex").mkdir(exist_ok=True)
    (tmp_path / ".codex" / "config.toml").write_text(
        CENTRAL_PROMPT_SUBMIT_COMMAND, encoding="utf-8"
    )
    (tmp_path / ".gemini" / "settings.json").write_text(
        CENTRAL_PROMPT_SUBMIT_COMMAND, encoding="utf-8"
    )


class TestOutputValidatorAllPresent:
    def test_valid_when_all_files_exist(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path, categories=["git"])
        validator = _make_validator(tmp_path, categories=["git"])
        is_valid, result = validator.validate()
        assert is_valid is True
        assert result["errors"] == []

    def test_checks_dict_populated(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path)
        validator = _make_validator(tmp_path)
        _, result = validator.validate()
        assert len(result["checks"]) > 0

    def test_category_guideline_checked(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path, categories=["testing"])
        validator = _make_validator(tmp_path, categories=["testing"])
        is_valid, _ = validator.validate()
        assert is_valid is True

    def test_legacy_optional_hooks_flag_is_ignored(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path)
        validator = _make_validator(tmp_path, config={"include_optional_hooks": True})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert "optional: setup-precommit-hook.sh" not in result["checks"]

    def test_prompt_submit_hooks_required_in_hook_mode(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path)
        _create_prompt_submit_hooks(tmp_path)
        validator = _make_validator(tmp_path, config={"handshake_mode": "hook"})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert result["checks"]["hook: central hook"] == "OK"
        assert result["checks"]["hook: Codex adapter"] == "OK"

    def test_prompt_submit_hooks_validates_all_three_agents(
        self, tmp_path: Path
    ) -> None:
        """Regression (SQ-001): claude, codex, and gemini adapters are all checked
        together when handshake_mode=hook with no agent restriction  protects
        the default all-supported-agents behavior through future refactors."""
        _create_all_required(tmp_path)
        _create_prompt_submit_hooks(tmp_path)
        validator = _make_validator(tmp_path, config={"handshake_mode": "hook"})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert result["checks"]["hook: central hook"] == "OK"
        assert result["checks"]["hook: Claude adapter"] == "OK"
        assert result["checks"]["hook: Codex adapter"] == "OK"
        assert result["checks"]["hook: Gemini adapter"] == "OK"

    def test_prompt_submit_hooks_can_target_selected_agents(
        self, tmp_path: Path
    ) -> None:
        _create_all_required(tmp_path)
        (tmp_path / ".providence" / "runtime" / "hooks").mkdir(parents=True)
        (
            tmp_path / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
        ).write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (tmp_path / ".codex").mkdir(exist_ok=True)
        (tmp_path / ".codex" / "config.toml").write_text(
            CENTRAL_PROMPT_SUBMIT_COMMAND, encoding="utf-8"
        )
        validator = _make_validator(
            tmp_path,
            config={
                "handshake_mode": "hook",
                "prompt_submit_hook_agents": ["codex"],
            },
        )
        is_valid, result = validator.validate()
        assert is_valid is True
        assert "hook: Claude adapter" not in result["checks"]


class TestOutputValidatorMissingFiles:
    def test_invalid_when_dirs_missing(self, tmp_path: Path) -> None:
        validator = _make_validator(tmp_path)
        is_valid, result = validator.validate()
        assert is_valid is False
        assert len(result["errors"]) > 0

    def test_errors_list_mandatory_dirs(self, tmp_path: Path) -> None:
        validator = _make_validator(tmp_path)
        _, result = validator.validate()
        assert any("Missing directory" in e for e in result["errors"])

    def test_missing_mandatory_file_invalid(self, tmp_path: Path) -> None:
        # Create dirs but no files
        sdd = tmp_path / ".providence"
        (sdd / "source" / "mandates").mkdir(parents=True)
        (sdd / "source" / "guidelines").mkdir(parents=True)
        (sdd / "runtime").mkdir(parents=True)
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        validator = _make_validator(tmp_path)
        is_valid, result = validator.validate()
        assert is_valid is False
        assert any("Missing file" in e for e in result["errors"])

    def test_missing_category_guideline_invalid(self, tmp_path: Path) -> None:
        _create_all_required(tmp_path)  # no "security" category file
        validator = _make_validator(tmp_path, categories=["security"])
        is_valid, result = validator.validate()
        assert is_valid is False
        assert any("security" in e for e in result["errors"])

    def test_legacy_optional_hooks_missing_does_not_invalidate(
        self, tmp_path: Path
    ) -> None:
        _create_all_required(tmp_path)
        validator = _make_validator(tmp_path, config={"include_optional_hooks": True})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert not any("optional-enabled" in e for e in result["errors"])

    def test_prompt_submit_hooks_missing_invalid_in_hook_mode(
        self, tmp_path: Path
    ) -> None:
        _create_all_required(tmp_path)
        validator = _make_validator(tmp_path, config={"handshake_mode": "hook"})
        is_valid, result = validator.validate()
        assert is_valid is False
        assert any("Missing handshake_mode=hook file" in e for e in result["errors"])


def _create_core_required(tmp_path: Path) -> None:
    sdd = tmp_path / ".providence"
    (sdd / "source" / "mandates").mkdir(parents=True)
    (sdd / "source" / "guidelines").mkdir(parents=True)
    (sdd / "runtime").mkdir(parents=True)
    (sdd / "source" / "mandates" / "mandates.md").write_text("# M", encoding="utf-8")
    (sdd / "runtime" / "README.md").write_text("# R", encoding="utf-8")
    (sdd / "source" / "README.md").write_text("# S", encoding="utf-8")
    (sdd / "metadata.json").write_text("{}", encoding="utf-8")


class TestOutputValidatorSelectiveGeneration:
    def test_vscode_only_selection_does_not_require_other_ides_or_agents(
        self, tmp_path: Path
    ) -> None:
        _create_core_required(tmp_path)
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
        validator = _make_validator(tmp_path, selected_seedlings={"vscode"})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert "file: Copilot Instructions" not in result["checks"]
        assert "file: Claude Instructions" not in result["checks"]
        assert "file: Gemini Instructions" not in result["checks"]
        assert "file: Cursor Rules" not in result["checks"]

    def test_cursor_only_selection_requires_only_cursor(self, tmp_path: Path) -> None:
        _create_core_required(tmp_path)
        (tmp_path / ".cursor" / "rules").mkdir(parents=True)
        (tmp_path / ".cursor" / "rules" / "spec.mdc").write_text("x", encoding="utf-8")
        validator = _make_validator(tmp_path, selected_seedlings={"cursor"})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert result["checks"]["file: Cursor Rules"] == "OK"

    def test_antigravity_only_selection_requires_antigravity_instructions(
        self, tmp_path: Path
    ) -> None:
        _create_core_required(tmp_path)
        antigravity_dir = tmp_path / ".gemini" / "antigravity"
        antigravity_dir.mkdir(parents=True)
        (antigravity_dir / "antigravity-instructions.md").write_text(
            "x", encoding="utf-8"
        )
        validator = _make_validator(tmp_path, selected_seedlings={"antigravity"})
        is_valid, result = validator.validate()
        assert is_valid is True
        assert result["checks"]["file: Antigravity Instructions"] == "OK"

    def test_ci_not_selected_does_not_require_workflows_dir(
        self, tmp_path: Path
    ) -> None:
        _create_core_required(tmp_path)
        validator = _make_validator(tmp_path, selected_seedlings={"governance"})
        is_valid, _ = validator.validate()
        assert is_valid is True

    def test_ci_selected_requires_workflows_dir(self, tmp_path: Path) -> None:
        _create_core_required(tmp_path)
        validator = _make_validator(tmp_path, selected_seedlings={"ci"})
        is_valid, result = validator.validate()
        assert is_valid is False
        assert any(".github" in e and "workflows" in e for e in result["errors"])

        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        is_valid, _ = validator.validate()
        assert is_valid is True


class TestOutputValidatorVerbose:
    def test_verbose_mode_emits_log(self, tmp_path: Path, capsys) -> None:
        validator = OutputValidator(
            output_base=tmp_path,
            sdd_dir=tmp_path / ".providence",
            source_dir=tmp_path / ".providence" / "source",
            runtime_dir=tmp_path / ".providence" / "runtime",
            mandates_dir=tmp_path / ".providence" / "source" / "mandates",
            guidelines_dir=tmp_path / ".providence" / "source" / "guidelines",
            guidelines_by_category={},
            verbose=True,
        )
        validator.validate()
        captured = capsys.readouterr()
        assert "Validating" in captured.out
