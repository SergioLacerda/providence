"""Tests for the sdd-* -> providence-* profile label resolver."""

from __future__ import annotations

import pytest

from providence_skills import resolve_profile_label


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sdd-diagnose", "providence-diagnose"),
        ("sdd-ask", "providence-ask"),
        ("sdd-correct", "providence-correct"),
        ("sdd-converge", "providence-converge"),
        ("sdd-stabilize", "providence-stabilize"),
        ("sdd-validate-governance", "providence-validate-governance"),
        ("sdd-organize", "providence-organize"),
    ],
)
def test_resolves_legacy_sdd_id_to_providence_label(raw: str, expected: str) -> None:
    assert resolve_profile_label(raw) == expected


@pytest.mark.parametrize(
    "raw", ["default", "client", "master", "", "providence-diagnose"]
)
def test_non_sdd_values_pass_through_unchanged(raw: str) -> None:
    assert resolve_profile_label(raw) == raw


def test_resolver_is_idempotent() -> None:
    once = resolve_profile_label("sdd-diagnose")
    assert resolve_profile_label(once) == once
