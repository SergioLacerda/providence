from __future__ import annotations

from pathlib import Path

from providence_integration.assertions.config import (
    ConfigHasKeyAssertion,
    ConfigIsValidPathAssertion,
)
from providence_integration.assertions.filesystem import FsExistsAssertion
from providence_integration.assertions.process import (
    ProcessExitAssertion,
    ProcessNotAllSkippedAssertion,
)


def test_process_exit_assertion_handles_string_equals() -> None:
    assertion = ProcessExitAssertion(equals="0")
    result = assertion.execute({"last_exit_code": 0})
    assert result.success is True


def test_process_not_all_skipped_fails_when_only_skipped() -> None:
    assertion = ProcessNotAllSkippedAssertion()
    result = assertion.execute({"last_stdout": "3 skipped in 0.10s"})
    assert result.success is False
    assert "all tests skipped" in result.message


def test_config_has_key_uses_string_key(tmp_path: Path) -> None:
    assertion = ConfigHasKeyAssertion(key="repo")
    result = assertion.execute({"config": {"repo": "ok"}, "working_dir": tmp_path})
    assert result.success is True


def test_config_is_valid_path_relative_to_working_dir(tmp_path: Path) -> None:
    target = tmp_path / "workspace"
    target.mkdir()
    assertion = ConfigIsValidPathAssertion(key="root")
    result = assertion.execute(
        {"config": {"root": "workspace"}, "working_dir": tmp_path}
    )
    assert result.success is True


def test_fs_exists_uses_context_working_dir(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    marker.write_text("x", encoding="utf-8")
    assertion = FsExistsAssertion(path="marker.txt")
    result = assertion.execute({"working_dir": tmp_path})
    assert result.success is True
