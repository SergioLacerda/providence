"""Ask-entrypoint environment contract (RFC-019)."""

from __future__ import annotations

import pytest
from providence_runtime.intake.entrypoint import (
    ASK_ENTRYPOINT_ENV,
    resolve_ask_entrypoint,
)

from providence_core.utils._environment_workspace import (
    RetiredEnvironmentVariableError,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROVIDENCE_ASK_ENTRYPOINT", raising=False)
    monkeypatch.delenv("SDD_ASK_ENTRYPOINT", raising=False)


def test_variable_name_is_the_canonical_one() -> None:
    assert ASK_ENTRYPOINT_ENV == "PROVIDENCE_ASK_ENTRYPOINT"


def test_hook_value_resolves_to_the_hook_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVIDENCE_ASK_ENTRYPOINT", "hook")

    assert resolve_ask_entrypoint() == ("hook", None)


def test_unset_resolves_to_an_explicit_command() -> None:
    assert resolve_ask_entrypoint() == ("explicit_command", "sdd-ask")


def test_retired_variable_is_rejected_naming_the_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_ASK_ENTRYPOINT", "hook")

    with pytest.raises(RetiredEnvironmentVariableError) as excinfo:
        resolve_ask_entrypoint()

    assert "PROVIDENCE_ASK_ENTRYPOINT" in str(excinfo.value)
