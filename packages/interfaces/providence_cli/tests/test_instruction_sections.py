"""Tests for generators/_instruction_sections.py."""

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.generators._instruction_sections import (
    build_instruction_targets,
    guard_repo_root_mutation,
    write_instruction_files,
)

FINGERPRINT = "21b6f7d81c88d0c0"


def test_guard_repo_root_mutation_noop_without_test_output_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SDD_TEST_OUTPUT_DIR", raising=False)
    guard_repo_root_mutation(tmp_path)


def test_guard_repo_root_mutation_blocks_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
    with (
        patch(
            "providence_cli.generators._instruction_sections.is_repo_root",
            return_value=True,
        ),
        pytest.raises(PermissionError, match="SDD_ISOLATION_ERROR"),
    ):
        guard_repo_root_mutation(tmp_path)


def test_guard_repo_root_mutation_allows_non_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
    with patch(
        "providence_cli.generators._instruction_sections.is_repo_root",
        return_value=False,
    ):
        guard_repo_root_mutation(tmp_path)


def test_build_instruction_targets_includes_all_ides(tmp_path: Path) -> None:
    outputs = build_instruction_targets(tmp_path, FINGERPRINT, 2)
    labels = [label for label, *_ in outputs]
    assert labels == [
        "GitHub Copilot",
        "VS Code",
        "Claude",
        "Gemini",
        "Cursor",
        "Antigravity",
    ]

    copilot = next(o for o in outputs if o[0] == "GitHub Copilot")
    assert "Items: 2" in "\n".join(copilot[3])
    assert FINGERPRINT in "\n".join(copilot[3])


def test_write_instruction_files_writes_copilot_redirector(tmp_path: Path) -> None:
    outputs = build_instruction_targets(tmp_path, FINGERPRINT, 1)
    written = write_instruction_files(outputs, FINGERPRINT, ["M001"])

    written_paths = dict(written)
    copilot_path = written_paths["GitHub Copilot"]
    content = copilot_path.read_text(encoding="utf-8")
    assert ".providence/agent-instructions.md" in content
    assert "GitHub Copilot Governance Bootstrap" in content


def test_write_instruction_files_writes_redirector_for_other_tools(
    tmp_path: Path,
) -> None:
    outputs = build_instruction_targets(tmp_path, FINGERPRINT, 1)
    written = write_instruction_files(outputs, FINGERPRINT, ["M001"])

    written_paths = dict(written)
    claude_path = written_paths["Claude"]
    content = claude_path.read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "Active mandates: 1 (M001)" in content
