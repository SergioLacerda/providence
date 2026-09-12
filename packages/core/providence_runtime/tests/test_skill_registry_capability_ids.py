from __future__ import annotations

from providence_runtime.skills._registry_data import _REGISTRY

_EXPECTED_CAPABILITY_IDS = {
    "sdd-ask": "query",
    "sdd-diagnose": "diagnose",
    "sdd-correct": "correct",
    "sdd-converge": "converge",
    "sdd-review-architecture": "review_architecture",
    "sdd-stabilize": "stabilize",
    "sdd-compress-context": "compress_context",
}

# sdd-pipeline is never a capability implementation — it *is* the Pipeline layer
# (nova_arquitetura.txt §7's own Capability/Skill/Pipeline split) — and is not
# even present in the hardcoded _registry_data fallback (file-based registry
# only), so it's excluded here rather than asserted as capability_id=None.
#
# sdd-validate-governance was never in scope for any capability-naming
# refinement (not named in nova_arquitetura §14, not raised as a question) — it
# stays capability_id=None until someone actually looks at it.
_EXPECTED_NO_CAPABILITY = {"sdd-validate-governance"}


def test_seven_skills_declare_their_capability_id() -> None:
    for skill_name, expected_capability_id in _EXPECTED_CAPABILITY_IDS.items():
        assert _REGISTRY[skill_name].capability_id == expected_capability_id


def test_unmapped_skills_have_no_capability_id() -> None:
    for skill_name in _EXPECTED_NO_CAPABILITY:
        if skill_name in _REGISTRY:
            assert _REGISTRY[skill_name].capability_id is None
