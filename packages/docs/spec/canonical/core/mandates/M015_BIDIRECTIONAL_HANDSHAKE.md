# Mandate: Bidirectional Agent Handshake

**ID:** M015
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution

---

## Objective

Ensure every agentic interaction is governed by a formal trust boundary via a
bidirectional challenge/response protocol before any skill or tool execution
begins.

---

## Requirements

1. **Challenge**: The runtime MUST issue a `HandshakeRequest` to the agent
   containing: session context, available skills (registry export), active
   mandate IDs, and signature status.

2. **Response**: The agent MUST formally respond with its `agent_id`, the set
   of `skills_to_use`, and explicit acknowledgment of mandate IDs and artifact
   signatures.

3. **Runtime Enforcement**: The `SkillEngine` MUST block any skill not
   explicitly authorized in the handshake response.

4. **Strict Mode**: When `SDD_SIGNATURE_MODE=strict`, execution is blocked if
   the handshake is missing or if the agent has not acknowledged artifact
   signatures.

---

## Enforcement Rules

- The handshake is non-negotiable and must precede any tool/skill call.
- Agents operating without a valid handshake are considered unauthorized.
- Handshake responses are stored as auditable contracts under `.providence/runtime/`.
- Violation requires human escalation — not auto-correction.

---

## Enforcement Steps

- Confirm a `HandshakeRequest` was issued to the agent before any skill or tool execution began
- Confirm the agent responded with its `agent_id`, declared `skills_to_use`, and acknowledged active mandate IDs
- Verify the `SkillEngine` blocks any skill not explicitly authorized in the handshake response
- If `SDD_SIGNATURE_MODE=strict`, confirm execution is blocked when handshake is missing or artifact signatures are unacknowledged
- Confirm the handshake response is stored under `.providence/runtime/` as an auditable contract

---

## Reference

See [ADR-012](../../../decisions/ADR-012-handshake-enforcement-m015.md) for
the full design rationale and implementation notes.
