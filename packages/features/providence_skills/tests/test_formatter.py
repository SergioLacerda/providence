"""Tests for governance footer formatting."""

from __future__ import annotations

from providence_skills import format_governance_footer


def test_footer_renders_providence_label_for_legacy_skill_id() -> None:
    footer = format_governance_footer(
        drift="none", governance="ok", profile="sdd-diagnose"
    )
    assert (
        footer
        == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=providence-diagnose"
    )


def test_footer_leaves_non_sdd_profile_unchanged() -> None:
    footer = format_governance_footer(drift="none", governance="ok", profile="default")
    assert (
        footer == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default"
    )


def test_footer_still_appends_root_seed_drift() -> None:
    footer = format_governance_footer(
        drift="none", governance="ok", profile="sdd-ask", root_seed_drift="none"
    )
    assert footer.endswith("profile=providence-ask | root_seed_drift=none")
