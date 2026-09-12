"""Shared 'Governance Mode' / HARD Mode Rules section for agent-instructions.md.

Both the active `providence governance generate` path
(`orchestration/seedlings/_agent_instructions_content.py`) and the initial wizard
seedling path (`templates/_agent_instructions_template.py`) render this same
section. Keeping a single canonical copy here prevents the two generators from
silently drifting when the wording (e.g. Rule 3) is updated.
"""

from __future__ import annotations

HARD_MODE_RULES_SECTION = """## Governance Mode

When operating under SDD via a skill or CLI entry point (`providence ask`, `sdd-ask`, `sdd-converge`, etc.),
the execution context is **HARD governance mode**.

| Entry point | Mode |
|-------------|------|
| `providence ask` / `sdd-ask` skill | HARD |
| `sdd-converge`, `sdd-correct`, `sdd-stabilize` | HARD |
| Direct API / notebook / ad-hoc | SOFT |

### HARD Mode Rules

**Rule 1  Execution gate:**
If `providence ask` output contains `execution_gate: blocked`, **STOP immediately**.
Report the `gate_reason` to the user. Do not proceed with any action until the user re-authorizes.

**Rule 2  Git authorization:**
Git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, etc.)
are **blocked** unless the current user message contains explicit authorization.
Task completion is NOT authorization. Only explicit phrases like "commit this", "push to remote",
"run git add and commit" constitute authorization.

**Rule 3  `intake_index_mode: none` is an independent signal, not "the gate":**
`intake_index_mode: none` means no governance context was indexed for this query.
This is **separate from Rule 1**  `execution_gate` may be `allowed` while
`intake_index_mode` is still `none` (e.g. for short queries). Surface this
condition to the user by name and value  do not describe it as "the gate is
blocked" unless `execution_gate: blocked` is also present. If `execution_gate:
blocked` is present, follow Rule 1 (stop and wait for re-authorization). If
`execution_gate: allowed`, proceed normally  `intake_index_mode: none` alone
is informational, not a stop condition.

**Rule 4  Context is not execution:**
Prompt-submit hook context and `providence ask` query output are governance context
only. They do not prove that provider delegation, implementation, source
mutation, or user approval occurred. If implementation intent is present, use
an explicitly authorized implementation path or provider result."""
