# ADR-012: Bidirectional Agentic Handshake and Skill Enforcement (M015)

- Status: Accepted
- Date: 2026-05-13

## Context

As the Providence moves toward autonomous agent orchestration, a formal trust boundary is required. Previously, agents could execute any CLI command or skill if they had the binary, without a formal declaration of intent or acknowledgment of governance mandates. This created a "Fail-Open" risk where unauthorized or high-risk skills could be used without a pre-delivery quality gate.

## Decision

Implement a **Fail-Closed** bidirectional handshake protocol (Mandate M015) that governs all agentic interactions:

1. **Handshake Initiation (Challenge)**: The runtime provides the agent with a formal challenge containing the session context, available skills (registry export), active mandates (MIDs), and signature status.
2. **Handshake Completion (Response)**: The agent must formally respond with a declaration of its `agent_id`, the set of `skills_to_use`, and an explicit acknowledgment of digital signatures and mandates.
3. **Runtime Enforcement Guard**: The `SkillEngine` intercepts all tool calls and blocks any skill not explicitly authorized in the handshake response.
4. **Strict Mode**: When `SDD_SIGNATURE_MODE=strict` is set, execution is blocked if the handshake is missing or if the agent has not acknowledged the artifact signatures.

## Consequences

- **Positive**:
  - **Executable Governance**: Handshake responses serve as an auditable contract of agent intent.
  - **Fail-Closed Security**: Blocks unauthorized skill usage at the registry level.
  - **Framework Agnostic**: Supports LangChain, OpenAI, and other tool-use schemas via standardized exports.
  - **Signature Verification**: Mandatory pre-handshake checks ensure artifact integrity.
- **Negative**:
  - Adds a mandatory initialization step for agents (Handshake Initiation).
  - Requires agents to be "governance-aware" to operate in strict environments.

## Implementation Notes

- Handshake state is persisted in `.providence/runtime/handshake-response.json`.
- `AgentHandshakeProtocol` in `providence_core` is the authority for challenge/response logic.
- Integration into `providence ask` and `providence ask-full` ensures all primary entry points are guarded.
