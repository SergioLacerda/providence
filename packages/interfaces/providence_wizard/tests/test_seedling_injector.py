from __future__ import annotations

from pathlib import Path

from providence_wizard.orchestration.deployer.seedling_injector import SeedlingInjector


def test_isolation_guard_is_non_fatal_when_repo_root_matches(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path))
    injector = SeedlingInjector(repo_root=tmp_path, output_base=tmp_path, verbose=False)

    injector._isolation_guard()


def test_inject_bootstrap_metadata_appends_once(tmp_path: Path) -> None:
    output = tmp_path / "out"
    target = output / ".github" / "copilot-instructions.md"
    target.parent.mkdir(parents=True)
    target.write_text("hello", encoding="utf-8")
    injector = SeedlingInjector(repo_root=tmp_path, output_base=output, verbose=False)

    injector.inject_bootstrap_metadata("fp", "2026-01-01T00:00:00", 3)
    injector.inject_bootstrap_metadata("fp", "2026-01-01T00:00:00", 3)

    content = target.read_text(encoding="utf-8")
    assert content.count("sdd:bootstrap-metadata") == 1
    assert "governance_fingerprint : fp" in content


def test_populate_ide_rules_replaces_placeholders(tmp_path: Path) -> None:
    output = tmp_path / "out"
    vscode = output / ".vscode" / "ai-rules.md"
    cursor = output / ".cursor" / "rules" / "sdd-governance.mdc"
    vscode.parent.mkdir(parents=True)
    cursor.parent.mkdir(parents=True)
    vscode.write_text("{FINGERPRINT} {MANDATES_COUNT}", encoding="utf-8")
    cursor.write_text("{FINGERPRINT} {MANDATES_COUNT}", encoding="utf-8")
    injector = SeedlingInjector(repo_root=tmp_path, output_base=output, verbose=False)

    injector.populate_ide_rules([{"id": "M001"}, {"id": "M002"}], "fingerprint-1")

    assert vscode.read_text(encoding="utf-8") == "fingerprint-1 2"
    assert cursor.read_text(encoding="utf-8") == "fingerprint-1 2"


def test_inject_bootstrap_metadata_skips_missing_files(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    injector = SeedlingInjector(repo_root=tmp_path, output_base=output, verbose=False)

    injector.inject_bootstrap_metadata("fp", "2026-01-01T00:00:00", 1)

    assert list(output.rglob("*")) == []


def test_log_uses_print_when_verbose(tmp_path: Path, capsys) -> None:
    injector = SeedlingInjector(
        repo_root=tmp_path, output_base=tmp_path / "out", verbose=True
    )

    injector._log("hello")

    assert "hello" in capsys.readouterr().out
