"""Workspace-root environment contract (RFC-019).

`PROVIDENCE_WORKSPACE_ROOT` is the only override. The retired `SDD_WORKSPACE_ROOT`
is rejected with a diagnostic naming the replacement, never read or aliased.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_core.utils._environment_workspace import (
    RETIRED_WORKSPACE_ROOT_ENV,
    WORKSPACE_ROOT_ENV,
    RetiredEnvironmentVariableError,
)
from providence_core.utils.environment import workspace_root_from_env


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(WORKSPACE_ROOT_ENV, raising=False)
    monkeypatch.delenv(RETIRED_WORKSPACE_ROOT_ENV, raising=False)


def test_names_are_the_documented_ones() -> None:
    assert WORKSPACE_ROOT_ENV == "PROVIDENCE_WORKSPACE_ROOT"
    assert RETIRED_WORKSPACE_ROOT_ENV == "SDD_WORKSPACE_ROOT"


def test_unset_means_no_override() -> None:
    assert workspace_root_from_env() is None


def test_reads_the_canonical_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))

    assert workspace_root_from_env() == tmp_path.resolve()


def test_retired_variable_is_rejected_naming_the_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(RETIRED_WORKSPACE_ROOT_ENV, str(tmp_path))

    with pytest.raises(RetiredEnvironmentVariableError) as excinfo:
        workspace_root_from_env()

    message = str(excinfo.value)
    assert "SDD_WORKSPACE_ROOT" in message
    assert "PROVIDENCE_WORKSPACE_ROOT" in message


def test_retired_variable_is_rejected_even_when_the_canonical_one_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No precedence between the two: a retired input is never interpreted."""
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(RETIRED_WORKSPACE_ROOT_ENV, str(tmp_path))

    with pytest.raises(RetiredEnvironmentVariableError):
        workspace_root_from_env()


def test_empty_retired_variable_is_not_an_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RETIRED_WORKSPACE_ROOT_ENV, "   ")

    assert workspace_root_from_env() is None
