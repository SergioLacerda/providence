"""Contract tests for hard-mode governance propagation to agent-instructions.md and skill registry."""

from __future__ import annotations

import pytest
from providence_runtime.skills import _REGISTRY

from providence_wizard.orchestration.seedlings._agent_instructions_content import (
    build_agent_instructions_content,
)
from providence_wizard.templates._agent_instructions_template import (
    build_agent_instructions,
)
from providence_wizard.templates._hard_mode_rules import HARD_MODE_RULES_SECTION

pytestmark = pytest.mark.unit

_CONTROLLED_SKILLS = ["sdd-ask", "sdd-converge", "sdd-correct", "sdd-stabilize"]

_RENDERED_CONTENT = build_agent_instructions_content(
    fingerprint="deadbeef",
    generated_at="2026-06-14T00:00:00Z",
    mandate_count=1,
    ids_preview="M001",
    mandates_list="- M001: Example",
)
_RENDERED_TEMPLATE = build_agent_instructions(
    spec_fingerprint="deadbeef",
    generated_at="2026-06-14T00:00:00Z",
    mandates_list="- M001: Example",
)


class TestAgentInstructionsTemplate:
    @pytest.mark.parametrize("rendered", [_RENDERED_CONTENT, _RENDERED_TEMPLATE])
    def test_governance_mode_section_present_in_template(self, rendered: str):
        """Both generators render the shared ## Governance Mode section."""
        assert "## Governance Mode" in rendered
        assert HARD_MODE_RULES_SECTION in rendered

    @pytest.mark.parametrize("rendered", [_RENDERED_CONTENT, _RENDERED_TEMPLATE])
    def test_hard_mode_rule1_gate_present(self, rendered: str):
        """Rule 1 (execution_gate=blocked → STOP) is in the rendered output."""
        assert "execution_gate" in rendered
        assert "blocked" in rendered

    @pytest.mark.parametrize("rendered", [_RENDERED_CONTENT, _RENDERED_TEMPLATE])
    def test_hard_mode_rule2_git_authorization_present(self, rendered: str):
        """Rule 2 (git commands blocked without authorization) is in the rendered output."""
        assert "Task completion is NOT authorization" in rendered

    @pytest.mark.parametrize("rendered", [_RENDERED_CONTENT, _RENDERED_TEMPLATE])
    def test_hard_mode_rule3_intake_none_not_permission(self, rendered: str):
        """Rule 3 (intake_index_mode=none is not permission) is in the rendered output."""
        assert "intake_index_mode" in rendered
        assert "not permission" in rendered.lower() or "surface" in rendered.lower()

    @pytest.mark.parametrize("rendered", [_RENDERED_CONTENT, _RENDERED_TEMPLATE])
    def test_hard_mode_rule3_does_not_force_stop_when_gate_allowed(self, rendered: str):
        """Rule 3 must not instruct an unconditional stop when execution_gate is allowed."""
        rule3_start = rendered.index("Rule 3")
        rule3_text = rendered[rule3_start : rule3_start + 700]
        assert "execution_gate: blocked" in rule3_text
        stop_idx = rule3_text.lower().find("stop and wait")
        gate_idx = rule3_text.lower().find("execution_gate: blocked")
        assert stop_idx == -1 or stop_idx > gate_idx


class TestSkillRegistryInvariants:
    def test_sdd_ask_has_hard_mode_protocol(self):
        """sdd-ask registry entry has hard_mode_protocol defined."""
        assert _REGISTRY["sdd-ask"].hard_mode_protocol is not None

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_controlled_skill_has_hard_mode_invariants(self, skill_name: str):
        """All four controlled skills have hard_mode_invariants defined."""
        assert _REGISTRY[skill_name].hard_mode_invariants is not None, (
            f"{skill_name} missing hard_mode_invariants in _REGISTRY"
        )

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_hard_mode_invariants_post_conditions_reference_m010(self, skill_name: str):
        """hard_mode_invariants post_conditions reference M010."""
        invariants = _REGISTRY[skill_name].hard_mode_invariants
        post = invariants.get("post_conditions", [])
        assert "M010" in str(post), (
            f"{skill_name}: M010 not referenced in post_conditions"
        )

    @pytest.mark.parametrize("skill_name", _CONTROLLED_SKILLS)
    def test_hard_mode_invariants_post_conditions_reference_m015(self, skill_name: str):
        """hard_mode_invariants post_conditions reference M015."""
        invariants = _REGISTRY[skill_name].hard_mode_invariants
        post = invariants.get("post_conditions", [])
        assert "M015" in str(post), (
            f"{skill_name}: M015 not referenced in post_conditions"
        )
