#!/usr/bin/env python3
"""
SDD Security Demo — Unauthorized Skill Execution

Shows SDD blocking an agent that attempts to invoke a skill that is not
registered in the governance skill registry. The SkillEngine raises
UnauthorizedSkillError before any execution occurs.

Run from repo root:
    uv run python examples/security/demo_unauthorized_skill.py
"""

from __future__ import annotations

from pathlib import Path

from providence_runtime import SkillEngine

REPO_ROOT = Path(__file__).resolve().parents[2]
SECTION = "\n" + "=" * 60


def main() -> None:
    print(SECTION)
    print("SDD Security — Unauthorized Skill Execution Demo")
    print(SECTION)

    engine = SkillEngine(project_root=REPO_ROOT)

    registered = [s.name for s in engine.list_skills()]
    print(f"\n[SDD] Registered skills ({len(registered)}): {registered or '(none)'}")

    # Simulate an agent trying to invoke a skill that was never registered.
    unauthorized_skill = "exfiltrate-data"
    print(f"\n[Agent] Attempting to run skill: '{unauthorized_skill}'")

    result = engine.run_skill(
        unauthorized_skill,
        execute=False,
        enforcement_mode="block",
    )

    if result.policy_result == "missing_skill" or result.exit_code != 0:
        print(f"\n[SDD] BLOCKED — skill='{unauthorized_skill}' is not in the registry.")
        print(f"[SDD] State          : {result.state}")
        print(f"[SDD] Policy result  : {result.policy_result}")
        print(f"[SDD] Reason         : {result.reason}")
        print(f"[SDD] Exit code      : {result.exit_code}")
        print(f"\n[SDD] {result.governance_footer}")
        print("\n[SDD] Agent execution prevented. Governance enforced.")
        print(SECTION)
        return

    # Reached only when the skill is registered and allowed.
    print(f"\n[SDD] Skill '{unauthorized_skill}' authorized — executing.")
    print(SECTION)


if __name__ == "__main__":
    main()
