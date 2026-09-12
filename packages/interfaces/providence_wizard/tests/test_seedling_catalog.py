"""Tests for the central seedling selection catalog."""

from __future__ import annotations

from providence_wizard.orchestration.wizard.seedling_catalog import (
    AGENTS,
    CATALOG,
    CATALOG_BY_KEY,
    CORE,
    IDE,
    OPTIONAL,
    RECOMMENDED_DEFAULT,
    grouped_options,
    resolve_selection,
)


def test_antigravity_is_a_distinct_ide_option() -> None:
    option = CATALOG_BY_KEY["antigravity"]
    assert option.group == IDE
    assert option.key != "gemini"


def test_ide_and_agents_are_separate_groups() -> None:
    groups = {option.group for option in CATALOG}
    assert IDE in groups
    assert AGENTS in groups
    assert "AGENT/IDE" not in groups


def test_ci_and_compliance_are_optional_and_off_by_default() -> None:
    for key in ("ci", "compliance"):
        option = CATALOG_BY_KEY[key]
        assert option.group == OPTIONAL
        assert option.default is False
        assert key not in RECOMMENDED_DEFAULT


def test_pre_commit_is_not_a_seedling_option() -> None:
    assert "pre-commit" not in CATALOG_BY_KEY


def test_recommended_default_excludes_optional_group() -> None:
    optional_keys = {o.key for o in CATALOG if o.group == OPTIONAL}
    assert RECOMMENDED_DEFAULT.isdisjoint(optional_keys)


def test_recommended_default_includes_core_ide_and_agents() -> None:
    assert {"governance", "verify"} <= RECOMMENDED_DEFAULT
    assert "vscode" in RECOMMENDED_DEFAULT
    assert "claude" in RECOMMENDED_DEFAULT


def test_resolve_selection_none_returns_recommended_default() -> None:
    assert resolve_selection(None) == set(RECOMMENDED_DEFAULT)


def test_resolve_selection_explicit_set_is_returned_unchanged() -> None:
    assert resolve_selection({"codex"}) == {"codex"}
    assert resolve_selection(set()) == set()


def test_grouped_options_preserves_group_order() -> None:
    groups = [group for group, _ in grouped_options()]
    assert groups == [g for g in (CORE, IDE, AGENTS, OPTIONAL) if g in groups]
