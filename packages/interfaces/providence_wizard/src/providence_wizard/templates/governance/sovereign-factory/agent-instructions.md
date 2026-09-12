# SDD Agent Instructions  Authority & Bootstrap

**This workspace is governed by Spec Driven Development (SDD).**

You MUST NOT proceed without reading this file in its entirety.

---

## 1. Authority Hierarchy

**The source of truth for all governance is this directory (`.providence/`).**

```
.providence/
 metadata.json                       Workspace version + fingerprints
 agent-instructions.md               THIS FILE (you are reading it)
 compiled/                           Optional binary/runtime artifacts (may be absent in template handoff)
 source/
     metadata.json                   Workspace version + fingerprints  READ THIS
     mandates/mandates.md            Mandate descriptions (enforcement rules)
     README.md
```

**Do not trust CLAUDE.md, .vscode/, .cursor/, or any other "convenience" pointers over what is in `.providence/`.**

---

## 2. Mandatory Bootstrap (3 steps)

Before planning, coding, or deciding:

1. **Read `.providence/metadata.json`**
   - Check `version` (currently 3.0)
   - Check `mandates_count` (count of active mandates)
   - Verify workspace is not stale
   - Expected fingerprint prefix (first 8 chars): 8d00f2d0

2. **Read `.providence/metadata.json`**
   - Extract mandate IDs and titles
   - Example: `"items": [{"id": "M001", "title": "Clean Architecture"}, ...]`
   - If `items` is empty or count < 4, governance is broken  escalate to human

3. **Read `.providence/source/mandates/mandates.md`**
   - Understand enforcement rules for each active mandate
   - If descriptions are stale or missing, request governance regeneration from the human

### 2a. Mandatory Awakening (skills base)

Before executing business tasks, run:

1. `providence runtime status`
2. `providence skills list --json`

Then:
- Resolve the base skill set from the real runtime catalog (not from memory).
- Cache awareness state in runtime-local memory for this workspace/session.
- If required skills are missing, declare degraded mode (SOFT), provide remediation, and avoid pretending the skill exists.

For explicit HARD paths (example: `/sdd-ask`), missing/invalid governance must fail-closed.

---

## 3. Active Mandates (read from `.providence/source/`)

The authoritative human-readable list is in `.providence/metadata.json`, not this file.

**Current snapshot** (validate this against `.providence/metadata.json`):
- **M001**: Clean Architecture
- **M002**: Test-Driven Development (TDD)
- **M003**: Context Awareness & Task Caching
- **M005**: Token Economy Enforcement
- **M006**: Any change that could require users to update their code or governance artifacts must follow this RFC process.
- **M007**: Telemetry Enforcement
- **M008**: Audit Integrity
- **M009**: OpenTelemetry Compliance
- **M010**: Delivery Hygiene Enforcement
- **M011**: English Language Standard
- **M015**: Bidirectional Agent Handshake
- **M016**: Guardrail Non-Regression

---

## 4. Pre-Task Checklist

Before starting any work:

- [ ] `.providence/metadata.json` read  version, fingerprint, count verified
- [ ] `.providence/metadata.json` read  mandates extracted
- [ ] `.providence/source/mandates/mandates.md` read  enforcement rules understood
- [ ] No contradictions between this file and `.providence/` (if found  escalate)

**If you cannot complete this checklist, do not proceed  ask the human first.**

---

## 5. Enforcement Scope

Mandates (HARD) are non-negotiable and always take precedence.

Policies, rules, and guidelines (SOFT) must also be applied when they do not conflict with mandates.

Git protocol (M010), testing, architecture, and token budgets must be followed.

### HARD Constraints  Never Violate

These constraints are non-negotiable. Violation requires human escalation, not auto-correction.

- **M010 (Delivery Hygiene)**: NEVER execute git state-modifying commands (add, commit, push, reset, merge, rebase, branch -D, etc.) autonomously via any tool or shell. ONLY suggest git commands in ready-to-run blocks for human execution.
  - **Explicit Authorization Required**: Only the human can authorize git operations with an explicit request: `"commita"`, `"commit"`, `"push"`, etc.
  - **Invalid Triggers** (NOT authorization): "continuar", "seguir", "pronto", "ok", "aplicar", code changes completion, test passing, linting passing.
  - **Corollary**: Task completion does NOT authorize a commit. Only explicit user request does.
  - **Pre-Bash Checklist**: Before every Bash call, ask "Does this command modify git state?" If YES  present as code block and STOP. Never execute.
  - **Read**: `.providence/source/mandates/mandates.md#M010` and `docs/spec/canonical/core/mandates/M010_DELIVERY_HYGIENE.md`

- **M016 (Guardrail Non-Regression)**: Guardrails MAY be incremented and optimized, but MUST NEVER regress. No removal of coverage, no hacks, no code smells.
  - **Allowed**: adding checks, refactoring for clarity/performance, composing new behavior on top of existing guardrails.
  - **Prohibited**: removing or narrowing a check, disabling via flag/bypass, silencing exceptions, weakening strict checks, hacks, dead code, removing guardrail tests.
  - **Composition over replacement**: Extend guardrail behavior; never replace it wholesale.
  - **Audit required**: Any change to guardrail code MUST emit a `GovernanceEvent` with `event_type=GUARDRAIL_MODIFIED`.
  - **RFC gate**: Any regression (prohibited action) requires an active RFC token approved by the human owner.
  - **Read**: `.providence/source/mandates/mandates.md#M016` and `docs/spec/core/M016-guardrail-immutability.md`

---

## 5a. Pre-Bash Gate (M010 Enforcement Point)

**Every time the agent is about to call the Bash tool:**

1. **Question**: "Does this command modify git state (add, commit, push, reset, rebase, merge, branch -D, cherry-pick, stash)?"
2. **If YES**:
   - Do NOT call Bash
   - Present the command in a ready-to-run code block
   - Explain what it does and why
   - Wait for explicit user authorization (e.g., "commita", "push", "merge")
3. **If NO**:
   - Proceed with the Bash call
   - For read-only git commands (status, log, diff)  allowed
   - For non-git commands  allowed
   - For linters, tests, formatters  allowed

**This gate is MANDATORY  it is the operational enforcement of M010.**

---

## 6. Fallback & Escalation

**If `.providence/` is incomplete or inconsistent:**
- Do not guess or interpolate
- Escalate to human: "`.providence/` is broken: [specific problem]"
- Example: "`.providence/metadata.json` has only 1 mandate but `.providence/metadata.json` claims 4"

**This is not a blocker  it's a signal that the human should regenerate the workspace.**

---

## 7. Mission Triggers (Slash Commands)

The following aliases are mapped to the operational prompt templates in `.github/prompts/`. When a user provides a command starting with `/sdd-`, you MUST read the corresponding template and follow its mission protocol exactly.

- `/sdd-ask`:  `.github/prompts/sdd-ask.prompt.md` (Governance Context Query)
- `/sdd-diagnose`:  `.github/prompts/sdd-diagnose.prompt.md` (Diagnose runtime/workspace problems)
- `/sdd-validate-governance`:  `.github/prompts/sdd-validate-governance.prompt.md` (Governance integrity preflight)
- `/sdd-stabilize`:  `.github/prompts/sdd-stabilize.prompt.md` (Stabilization checks before handoff)
- `/sdd-compress-context`:  `.github/prompts/sdd-compress-context.prompt.md` (Context footprint reduction)
- `/sdd-review-architecture`:  `.github/prompts/sdd-review-architecture.prompt.md` (Architecture adherence review)
- `/sdd-correct`:  `.github/prompts/sdd-correct.prompt.md` (Targeted governance correction)
- `/sdd-converge`:  `.github/prompts/sdd-converge.prompt.md` (Systemic alignment convergence)
- `/sdd-organize`:  `.github/prompts/sdd-organize.prompt.md` (Large context intake/indexing)

**Mandate**: All responses triggered by these commands MUST include the mandatory SDD footer:
`PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`

Additional mandate for `/sdd-ask`:
- Always run preflight (`providence runtime status` + `providence governance validate`) before `providence ask --full`.
- If preflight fails, stop and return governance-blocked status (do not proceed with business task).
