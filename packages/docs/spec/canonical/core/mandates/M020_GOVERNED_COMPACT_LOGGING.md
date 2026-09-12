# Mandate: Governed Compact Logging

**ID:** M020
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** execution

---

## Objective

All agent interfaces — both input to the LLM and output to the user — MUST follow
the Simple Governed IO pattern: a canonical event or context produces a simple base
form, with an optional profile presentation layer on top. Input and output follow
the same simplification rule by default.

---

## Requirements

1. Derive all LLM input context from canonical fields (governance state, fingerprint, mandates count). Base form: max 2 lines, key=value compact
2. Derive all user-facing output from a canonical event (phase, status, decision, artifact_path, next_action). Base output: max 3 lines, max 120 chars per line
3. Persist full diagnostic evidence in `.providence/runtime/` artifacts, not in console output
4. Emit DEBUG/TRACE as structured JSON telemetry, bypassing all profile renderers
5. Deduplicate repeated findings before rendering
6. Include artifact paths for auditability on every finding or decision event
7. Stop and emit a BLOCKER event when evidence is unreliable
8. Profiles MUST NOT change meaning, severity, status, decision, artifact path, or governance state — they may only change presentation
9. Agents MUST NOT send verbose governance metadata (query hash, trust source labels, repeated instructions) as LLM input when a compact canonical form suffices
10. Agents MUST NOT stream internal reasoning chains as console output
11. Agents MUST NOT use verbose first-person analysis as operational output
12. Agents MUST NOT repeat uncertainty loops without producing a decision
13. Agents MUST NOT mix user-facing logs with raw JSON telemetry
14. Agents MUST NOT use log volume as a substitute for evidence artifacts
15. A profile renderer MUST NOT alter governance state or decision content

---

## Rationale

Governance operations historically produced verbose, narrative-style content on both
sides of the agent boundary: input context sent to the LLM (query_hash, trust_source,
repeated instructions) and output sent to the user (multi-line intake blocks mixing
labels, reasons, and instructions). Both inflate token usage, degrade UX, and obscure
the actionable signal — state, decision, artifact, next action. M020 fixes this
symmetrically: governance defines what happened, the profile defines how to show it,
for both input and output, while telemetry and persisted artifacts retain full detail
for audit.

---

## Enforcement Steps

- Verify LLM-facing governance context (`render_context_header` or equivalent) emits ≤2 lines when healthy, ≤3 lines when degraded, using canonical key=value form
- Verify user-facing blocked/allowed output blocks are capped at 3 lines / 2 lines respectively
- Verify DEBUG/TRACE telemetry events are emitted as structured JSON and bypass profile renderers
- Verify profile renderers (pragmatic, epic) do not alter `decision`, `artifact_path`, `level`, `governance_state`, or `degraded` fields
- Verify error/precondition output paths cap console messages to 2 lines plus an artifact reference

---

## Related

- M005: Token Economy Enforcement (compact IO reduces token usage)
- M007: Telemetry Enforcement (DEBUG/TRACE structured JSON routing)
- M011: English Language Standard (all canonical IO types and tests in English)
- `packages/core/providence_core/src/providence_core/output/canonical_event.py` (`CanonicalLogEvent`, `CanonicalGovernanceInput`, `ProfileRenderer`)
