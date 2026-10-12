"""Guards: inputs retired by the rebrand must not be accepted or cleaned up.

Retired names are rejected (or simply unknown); no compatibility branch keeps
interpreting them. See ADR-025 and ADR-0063 of the sibling Strategist project.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_wizard.orchestration._seedlings_helpers import (
    _validate_awareness_pack,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SOURCE_ROOTS = (
    _REPO_ROOT / "packages" / "interfaces" / "providence_wizard" / "src",
    _REPO_ROOT / "packages" / "interfaces" / "providence_cli" / "src",
)

# Modules whose job is to recognise a retired marker *in order to reject it*.
_REJECTION_MODULES = {
    "_hook_adapters.py",
    "governance_hook_handlers.py",
    "_direct_root_deploy.py",
}


def _python_sources() -> list[Path]:
    return [
        path
        for root in _SOURCE_ROOTS
        for path in root.rglob("*.py")
        if "templates" not in path.parts
    ]


def test_sources_are_discovered() -> None:
    assert len(_python_sources()) > 50


@pytest.mark.parametrize("token", ["sdd-commands.mdc", ".sdd/"])
def test_retired_token_is_absent_from_generator_and_cli_sources(token: str) -> None:
    offenders = [
        f"{path.relative_to(_REPO_ROOT)}:{number}"
        for path in _python_sources()
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if token in line
    ]

    assert offenders == []


def test_pre_rebrand_central_hook_name_only_appears_where_it_is_rejected() -> None:
    offenders = [
        str(path.relative_to(_REPO_ROOT))
        for path in _python_sources()
        if "sdd-governance-inject" in path.read_text(encoding="utf-8")
        and path.name not in _REJECTION_MODULES
    ]

    assert offenders == []


def test_awareness_pack_does_not_accept_the_pre_rebrand_commands_file(
    tmp_path: Path,
) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "sdd-commands.mdc").write_text("legacy", encoding="utf-8")
    seedlings = tmp_path / ".providence" / "seedlings"
    seedlings.mkdir(parents=True)

    result = _validate_awareness_pack(tmp_path, seedlings, "standard")

    assert ".cursor/rules/providence-commands.mdc" in result["missing_items"]


# Where a retired environment variable name may appear in source: only the
# modules that reject it. Tests may name it to prove the rejection.
_ENV_REJECTION_MODULES = {
    "_environment_workspace.py",
    "entrypoint.py",
}


@pytest.mark.parametrize("name", ["SDD_WORKSPACE_ROOT", "SDD_ASK_ENTRYPOINT"])
def test_retired_environment_names_are_never_read_outside_their_rejection(
    name: str,
) -> None:
    """Reading is a quoted literal (`os.environ.get("NAME")`, an env dict key);
    prose mentions in docstrings and comments are not."""
    quoted = (f'"{name}"', f"'{name}'")
    offenders = [
        f"{path.relative_to(_REPO_ROOT)}:{number}"
        for path in (_REPO_ROOT / "packages").rglob("*.py")
        if "tests" not in path.parts and "templates" not in path.parts
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if any(token in line for token in quoted)
        and path.name not in _ENV_REJECTION_MODULES
    ]

    assert offenders == []
