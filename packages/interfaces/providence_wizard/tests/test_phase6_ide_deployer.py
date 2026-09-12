from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from providence_wizard.orchestration.deployer.template_deployer import TemplateDeployer


def test_template_base_prefers_existing_candidate(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(repo_root=tmp_path, output_base=output_base)

    preferred = tmp_path / "preferred" / "templates"
    preferred.mkdir(parents=True)

    fallback = tmp_path / "fallback" / "templates"
    fallback.mkdir(parents=True)

    deployer._template_base_candidates = lambda: [preferred, fallback]  # type: ignore[method-assign]
    assert deployer._template_base == preferred


def test_create_ide_templates_reports_missing_base(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(repo_root=tmp_path, output_base=output_base)
    deployer._template_base_candidates = lambda: [  # type: ignore[method-assign]
        tmp_path / "missing-a",
        tmp_path / "missing-b",
    ]
    assert deployer.create_ide_templates() is False


def test_create_ide_templates_does_not_create_precommit_hooks(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path,
        output_base=output_base,
    )
    template_base = tmp_path / "templates"
    (template_base / ".github").mkdir(parents=True)
    (template_base / ".github" / "copilot-instructions.md").write_text(
        "copilot", encoding="utf-8"
    )
    (template_base / ".vscode").mkdir(parents=True)
    (template_base / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
    (template_base / ".cursor" / "rules").mkdir(parents=True)
    (template_base / ".cursor" / "spec.mdc").write_text("x", encoding="utf-8")
    (template_base / ".claude").mkdir(parents=True)
    (template_base / ".claude" / "claude-instructions.md").write_text(
        "x", encoding="utf-8"
    )
    (template_base / ".gemini").mkdir(parents=True)
    (template_base / ".gemini" / "gemini-instructions.md").write_text(
        "x", encoding="utf-8"
    )
    (template_base / ".providence" / "templates").mkdir(parents=True)
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True
    assert not (output_base / ".github" / "setup-precommit-hook.sh").exists()
    assert not (output_base / ".pre-commit-config.yaml").exists()


def test_create_ide_templates_merges_template_candidates(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(repo_root=tmp_path, output_base=output_base)
    primary = tmp_path / "primary" / "templates"
    fallback = tmp_path / "fallback" / "templates"
    (primary / ".github" / "workflows").mkdir(parents=True)
    (primary / ".github" / "workflows" / "sdd-validation.yml").write_text(
        "workflow", encoding="utf-8"
    )
    (primary / ".github" / "copilot-instructions.md").write_text(
        "copilot", encoding="utf-8"
    )
    (fallback / ".vscode").mkdir(parents=True)
    (fallback / ".vscode" / "ai-rules.md").write_text("vscode", encoding="utf-8")
    (fallback / ".cursor" / "rules").mkdir(parents=True)
    (fallback / ".cursor" / "rules" / "spec.mdc").write_text("cursor", encoding="utf-8")
    (fallback / ".claude").mkdir(parents=True)
    (fallback / ".claude" / "claude-instructions.md").write_text(
        "claude", encoding="utf-8"
    )
    (fallback / ".gemini").mkdir(parents=True)
    (fallback / ".gemini" / "gemini-instructions.md").write_text(
        "gemini", encoding="utf-8"
    )
    (fallback / ".providence" / "templates").mkdir(parents=True)
    deployer._template_base_candidates = lambda: [primary, fallback]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert (output_base / ".github" / "copilot-instructions.md").exists()
    assert (output_base / ".vscode" / "ai-rules.md").exists()
    assert (output_base / ".cursor" / "rules" / "spec.mdc").exists()
    assert (output_base / ".claude" / "claude-instructions.md").exists()
    assert (output_base / ".gemini" / "gemini-instructions.md").exists()


def test_init_reports_isolation_error_when_output_base_equals_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "1")

    TemplateDeployer(repo_root=tmp_path, output_base=tmp_path)

    assert "SDD_ISOLATION_ERROR" in capsys.readouterr().out


def test_ensure_cursor_rule_aliases_creates_governance_from_spec(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, verbose=True
    )
    rules_dir = output_base / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "spec.mdc").write_text("spec", encoding="utf-8")

    deployer._ensure_cursor_rule_aliases()

    assert (rules_dir / "sdd-governance.mdc").read_text(encoding="utf-8") == "spec"


def test_ensure_cursor_rule_aliases_creates_spec_from_governance(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, verbose=True
    )
    rules_dir = output_base / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "sdd-governance.mdc").write_text("gov", encoding="utf-8")

    deployer._ensure_cursor_rule_aliases()

    assert (rules_dir / "spec.mdc").read_text(encoding="utf-8") == "gov"


def test_copy_templates_logs_when_workflow_missing(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, verbose=True
    )
    template_base = tmp_path / "templates"
    template_base.mkdir()
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True


def test_copy_templates_returns_false_on_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"ci"}
    )
    template_base = tmp_path / "templates"
    workflow_dir = template_base / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "sdd-validation.yml").write_text("x", encoding="utf-8")
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("boom")

    monkeypatch.setattr(
        "providence_wizard.orchestration.deployer.template_deployer.shutil.copy2", boom
    )

    assert deployer.copy_templates() is False


def test_create_ide_templates_logs_missing_and_failed_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, verbose=True
    )
    template_base = tmp_path / "templates"
    (template_base / ".vscode").mkdir(parents=True)
    (template_base / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    original_copytree = shutil.copytree

    def fake_copytree(src: Path, dst: Path, dirs_exist_ok: bool = False) -> Path:
        if src.name == ".vscode":
            raise OSError("copy failed")
        return original_copytree(src, dst, dirs_exist_ok=dirs_exist_ok)

    monkeypatch.setattr(
        "providence_wizard.orchestration.deployer.template_deployer.shutil.copytree",
        fake_copytree,
    )

    assert deployer.create_ide_templates() is False


def test_create_ide_templates_returns_false_on_outer_exception(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    deployer = TemplateDeployer(repo_root=tmp_path, output_base=output_base)
    template_base = tmp_path / "templates"
    (template_base / ".vscode").mkdir(parents=True)
    (template_base / ".vscode" / "ai-rules.md").write_text("x", encoding="utf-8")
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    def boom() -> None:
        raise RuntimeError("boom")

    deployer._ensure_cursor_rule_aliases = boom  # type: ignore[method-assign]

    assert deployer.create_ide_templates() is False


def _write_full_template_tree(template_base: Path) -> None:
    (template_base / ".github" / "workflows").mkdir(parents=True)
    (template_base / ".github" / "workflows" / "sdd-validation.yml").write_text(
        "workflow", encoding="utf-8"
    )
    (template_base / ".github" / "copilot-instructions.md").write_text(
        "copilot", encoding="utf-8"
    )
    (template_base / ".vscode").mkdir(parents=True)
    (template_base / ".vscode" / "ai-rules.md").write_text("vscode", encoding="utf-8")
    (template_base / ".cursor" / "rules").mkdir(parents=True)
    (template_base / ".cursor" / "rules" / "spec.mdc").write_text(
        "cursor", encoding="utf-8"
    )
    (template_base / ".claude").mkdir(parents=True)
    (template_base / ".claude" / "claude-instructions.md").write_text(
        "claude", encoding="utf-8"
    )
    (template_base / ".gemini").mkdir(parents=True)
    (template_base / ".gemini" / "gemini-instructions.md").write_text(
        "gemini", encoding="utf-8"
    )
    (template_base / ".providence" / "templates").mkdir(parents=True)


def test_vscode_only_selection_copies_vscode_and_nothing_else(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    _write_full_template_tree(template_base)
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"vscode"}
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert (output_base / ".vscode" / "ai-rules.md").exists()
    assert not (output_base / ".cursor").exists()
    assert not (output_base / ".claude").exists()
    assert not (output_base / ".gemini").exists()
    assert not (output_base / ".github" / "workflows" / "sdd-validation.yml").exists()
    assert not (output_base / ".github" / "copilot-instructions.md").exists()
    assert not (output_base / ".pre-commit-config.yaml").exists()


def test_cursor_only_selection_copies_cursor_and_nothing_else(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    _write_full_template_tree(template_base)
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"cursor"}
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert (output_base / ".cursor" / "rules" / "spec.mdc").exists()
    assert not (output_base / ".vscode").exists()
    assert not (output_base / ".claude").exists()
    assert not (output_base / ".gemini").exists()


def test_antigravity_only_selection_copies_gemini_dir_without_gemini_agent(
    tmp_path: Path,
) -> None:
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    _write_full_template_tree(template_base)
    deployer = TemplateDeployer(
        repo_root=tmp_path,
        output_base=output_base,
        selected_seedlings={"antigravity"},
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert (output_base / ".gemini" / "gemini-instructions.md").exists()
    assert not (output_base / ".vscode").exists()
    assert not (output_base / ".cursor").exists()
    assert not (output_base / ".claude").exists()


def test_ci_not_selected_does_not_copy_workflow(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    _write_full_template_tree(template_base)
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"vscode"}
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert not (output_base / ".github" / "workflows" / "sdd-validation.yml").exists()


def test_ci_selected_copies_workflow(tmp_path: Path) -> None:
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    _write_full_template_tree(template_base)
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"ci"}
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.copy_templates() is True
    assert deployer.create_ide_templates() is True

    assert (output_base / ".github" / "workflows" / "sdd-validation.yml").exists()


def test_create_ide_templates_fails_when_selected_template_dir_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A selected adapter with no template dir must fail generation explicitly

    instead of silently succeeding because an unrelated always-needed
    mapping (.providence/templates) was copied.
    """
    output_base = tmp_path / "out"
    template_base = tmp_path / "templates"
    (template_base / ".providence" / "templates").mkdir(parents=True)
    deployer = TemplateDeployer(
        repo_root=tmp_path, output_base=output_base, selected_seedlings={"claude"}
    )
    deployer._template_base_candidates = lambda: [template_base]  # type: ignore[method-assign]

    assert deployer.create_ide_templates() is False
    assert "Required template directory not found: .claude/" in capsys.readouterr().out
    assert not (output_base / ".claude").exists()
