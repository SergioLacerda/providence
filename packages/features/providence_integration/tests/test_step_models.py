"""Tests for Pydantic step model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from providence_integration.engine.types import (
    CommandExecInputs,
    ConfigValidateInputs,
    FilesystemCopyInputs,
    FilesystemCreateStructureInputs,
    GitCommitInputs,
)


class TestCommandExecInputs:
    """Validation tests for CommandExecInputs."""

    def test_accepts_valid_command(self) -> None:
        inputs = CommandExecInputs(command="pytest -q")
        assert inputs.command == "pytest -q"

    def test_rejects_empty_command(self) -> None:
        with pytest.raises(ValidationError):
            CommandExecInputs(command="")

    def test_rejects_whitespace_only_command(self) -> None:
        with pytest.raises(ValidationError):
            CommandExecInputs(command="   ")

    def test_rejects_non_string_command(self) -> None:
        with pytest.raises(ValidationError):
            CommandExecInputs(command=123)  # type: ignore[arg-type]


class TestFilesystemCreateStructureInputs:
    """Validation tests for FilesystemCreateStructureInputs."""

    def test_accepts_valid_directories(self) -> None:
        inputs = FilesystemCreateStructureInputs(directories=["a", "b", "c"])
        assert inputs.directories == ["a", "b", "c"]

    def test_rejects_mixed_type_list(self) -> None:
        with pytest.raises(ValidationError):
            FilesystemCreateStructureInputs(directories=["a", 1])  # type: ignore[list-item]

    def test_rejects_non_list(self) -> None:
        with pytest.raises(ValidationError):
            FilesystemCreateStructureInputs(directories="a")  # type: ignore[arg-type]


class TestFilesystemCopyInputs:
    """Validation tests for FilesystemCopyInputs."""

    def test_parses_from_alias(self) -> None:
        """Test that 'from' (reserved keyword) is aliased to 'from_' field."""
        inputs = FilesystemCopyInputs.model_validate({"from": "src", "to": "dst"})
        assert inputs.from_ == "src"
        assert inputs.to == "dst"

    def test_accepts_direct_from_field(self) -> None:
        """Test that populate_by_name allows both 'from' and 'from_' in model_validate."""
        inputs = FilesystemCopyInputs.model_validate({"from_": "src", "to": "dst"})
        assert inputs.from_ == "src"

    def test_rejects_non_string_from(self) -> None:
        with pytest.raises(ValidationError):
            FilesystemCopyInputs.model_validate({"from": 123, "to": "dst"})  # type: ignore[dict-item]

    def test_rejects_non_string_to(self) -> None:
        with pytest.raises(ValidationError):
            FilesystemCopyInputs.model_validate({"from": "src", "to": 123})  # type: ignore[dict-item]


class TestConfigValidateInputs:
    """Validation tests for ConfigValidateInputs."""

    def test_accepts_valid_file(self) -> None:
        inputs = ConfigValidateInputs(file=".providence/profile")
        assert inputs.file == ".providence/profile"

    def test_accepts_none_file(self) -> None:
        inputs = ConfigValidateInputs(file=None)
        assert inputs.file is None

    def test_accepts_default_none(self) -> None:
        inputs = ConfigValidateInputs()
        assert inputs.file is None

    def test_rejects_non_string_file(self) -> None:
        with pytest.raises(ValidationError):
            ConfigValidateInputs(file=123)  # type: ignore[arg-type]


class TestGitCommitInputs:
    """Validation tests for GitCommitInputs."""

    def test_accepts_valid_message(self) -> None:
        inputs = GitCommitInputs(message="init commit")
        assert inputs.message == "init commit"

    def test_defaults_message_to_init(self) -> None:
        inputs = GitCommitInputs()
        assert inputs.message == "init"

    def test_accepts_empty_message_override(self) -> None:
        """Empty string is valid; defaults only apply if field not provided."""
        inputs = GitCommitInputs(message="")
        assert inputs.message == ""

    def test_rejects_non_string_message(self) -> None:
        with pytest.raises(ValidationError):
            GitCommitInputs(message=123)  # type: ignore[arg-type]
