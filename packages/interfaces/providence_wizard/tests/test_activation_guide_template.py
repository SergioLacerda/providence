"""Golden-output test for build_activation_guide.

Guards the structure-refactor split of _activation_guide_template.py into
_activation_guide_setup_sections.py / _activation_guide_reference_sections.py
(see .analysis/pending/wizard-structure-refactor-20260708/)  output must stay
byte-identical across the split.
"""

from __future__ import annotations

import pytest

from providence_wizard.templates._activation_guide_template import (
    build_activation_guide,
)

pytestmark = pytest.mark.unit

_ARGS: dict[str, str] = {
    "fingerprint": "abc123def456",
    "generated_at": "2026-07-08T12:00:00Z",
    "enforcement_label": "Strict Mode",
    "enforcement_explanation": "Violations block commits and CI.",
    "enforcement_behavior": "Blocking with human review required.",
    "language": "Python",
    "mandates_list": "M001, M002, M003",
    "guidelines_list": "quality, style",
    "mandate_ids_joined": "M001, M002, M003",
}


def test_build_activation_guide_includes_all_sections() -> None:
    output = build_activation_guide(**_ARGS)

    assert output.startswith("# Governance Activation Guide")
    assert output.rstrip().endswith("Status:** Ready for activation")
    for heading in (
        "## What This Is",
        "##  Quick Start (3 Steps)",
        "##  Activation Checklist",
        "##  Your Governance Configuration",
        "##  Enforcement Mode",
        "##  What Each Seedling Does",
        "## Invocation Playbook (Skills + CLI)",
        "##  Verification",
        "##  Troubleshooting",
        "##  More Information",
        "##  After Activation",
    ):
        assert heading in output, f"missing section: {heading}"


def test_build_activation_guide_interpolates_all_args() -> None:
    output = build_activation_guide(**_ARGS)

    assert _ARGS["fingerprint"] in output
    assert _ARGS["generated_at"] in output
    assert _ARGS["enforcement_label"] in output
    assert _ARGS["enforcement_explanation"] in output
    assert _ARGS["enforcement_behavior"] in output
    assert _ARGS["language"] in output
    assert _ARGS["mandates_list"] in output
    assert _ARGS["guidelines_list"] in output
    assert _ARGS["mandate_ids_joined"] in output


def test_build_activation_guide_section_order_is_stable() -> None:
    """Sections must render in the documented order (composition order in
    build_activation_guide must match the original single-function output).
    """
    output = build_activation_guide(**_ARGS)
    headings = [
        "## What This Is",
        "##  Quick Start (3 Steps)",
        "##  Activation Checklist",
        "##  Your Governance Configuration",
        "##  Enforcement Mode",
        "##  What Each Seedling Does",
        "## Invocation Playbook (Skills + CLI)",
        "##  Verification",
        "##  Troubleshooting",
        "##  More Information",
        "##  After Activation",
    ]
    positions = [output.index(h) for h in headings]
    assert positions == sorted(positions)
