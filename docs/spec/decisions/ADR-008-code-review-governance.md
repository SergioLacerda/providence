# ADR-008: Code Review Governance - Agent Never Auto-Commits

## Status

- **Accepted** ✅
- Proposed: 2026-04-21
- Accepted: 2026-04-21
- Review Date: 2026-10-21

---

## Context

**Problem**:
In previous sessions, automatic commits by agents led to:

- Important files removed without explicit review
- Architectural gaps not caught
- Difficult rollbacks of problematic changes
- No clear handoff between planning and execution
- Loss of critical context about why changes were made

**Risk**: With multiple agents and distributed work, auto-commits can mask issues until production.

**Stakeholders**:

- **Architects** (owner/decision-maker): Must approve changes
- **Agents**: Implement according to spec
- **Code Owners**: Per-domain responsibility

---

## Decision

**Enforce two-person rule: AGENT NEVER AUTO-COMMITS**

### Core Principle

```
Agent Work Flow:
  1. Plan/Design phase
  2. Specification phase
  3. Implementation phase
  4. Documentation phase
  5. MARK READY FOR REVIEW ← STOP HERE
  6. Architect Review phase   ← Human decision
  7. Code approved/changes requested
  8. IF approved: Architect commits
  9. IF changes needed: Agent revises → back to step 1
```

### Rule: Agent Creates, Architect Commits

```
AGENT RESPONSIBILITIES:
  ✅ Write code, tests, documentation
  ✅ Verify tests pass locally (111/111+)
  ✅ Create git branch with work
  ✅ Push branch to origin (WIP prefix)
  ✅ Create PR/MR with description
  ✅ Request review from architect
  ✅ Wait for feedback
  ✅ Implement review changes
  ✗ NEVER force-push to main
  ✗ NEVER merge own PRs
  ✗ NEVER auto-commit to main

ARCHITECT RESPONSIBILITIES:
  ✅ Review design and spec (early gatekeep)
  ✅ Review implementation vs design
  ✅ Review tests and coverage
  ✅ Review documentation completeness
  ✅ Approve or request changes
  ✅ Merge PR to main (architect commits)
  ✅ Ensure backup of critical files
  ✅ Communicate decisions clearly
  ✗ NEVER merge unreviewed code
  ✗ NEVER skip design phase
```

### Code Review Checklist (Architect Gate)

```
BEFORE ARCHITECT MERGES, VERIFY:

Design Alignment:
  [ ] Code matches FEATURE_DESIGN_<name>.md
  [ ] No scope creep beyond design
  [ ] All design decisions respected
  [ ] Backward compatibility verified

Spec Compliance:
  [ ] Code implements COMPONENT_<name>.md spec
  [ ] All data structures match spec
  [ ] All algorithms match spec
  [ ] All edge cases handled

Testing:
  [ ] All tests passing (111/111+)
  [ ] No flaky tests
  [ ] Coverage: >85% on new code
  [ ] Performance requirements met

Documentation:
  [ ] Design doc links to code
  [ ] Spec doc links to tests
  [ ] Code comments explain decisions
  [ ] Docstrings complete
  [ ] README updated (if applicable)
  [ ] CHANGELOG updated
  [ ] API reference updated (if applicable)

Architecture:
  [ ] Clean Architecture layers respected
  [ ] No breaking changes to ports
  [ ] MANDATE rules not violated
  [ ] GUIDELINES customizable where needed
  [ ] OPERATIONS layer clean
  [ ] No unexplained tech debt

Governance:
  [ ] No critical files at risk
  [ ] Rollback procedure clear
  [ ] Change is reversible
  [ ] Risk assessment complete

Risk Assessment:
  - [ ] Low risk: Can merge immediately
  - [ ] Medium risk: Requires monitoring after merge
  - [ ] High risk: Requires rollback plan + approval
```

### Workflow: Branch + PR + Review + Merge

```
Step 1: Agent creates WIP branch
  $ git checkout -b wip/feature-<name>
  $ git push origin wip/feature-<name>

Step 2: Agent implements feature (PHASE 1-5)
  - Design phase (get architect approval on design)
  - Spec phase (write spec)
  - Dev phase (implement + test)
  - Doc phase (update docs)
  - Ready phase (mark WIP branch ready)

Step 3: Agent creates PR to main
  - Title: [REVIEW] Feature: <name>
  - Description includes:
    ├─ Design doc link
    ├─ Spec doc link
    ├─ Test results (111/111 passing)
    ├─ Risk assessment
    └─ Any special notes

  Example PR:
  ```

# [REVIEW] Feature: RTK Telemetry Deduplication

  Implements ADR-007 guardrails: design first, code follows.

## Design

  See: FEATURE_DESIGN_rtk_telemetry.md (APPROVED by @user)

## Specification

  See: COMPONENT_rtk_deduplication.md

- 50+ patterns implemented
- O(1) dedup with LRU cache
- 72.9% compression on test data

## Testing

- Local: 111/111 passing ✅
- Coverage: 92% on new code
- No performance regression

## Documentation

- [x] Design doc (referenced above)
- [x] Code comments (cross-referenced)
- [x] RTK.md updated with patterns
- [x] CHANGELOG.md updated
- [x] Tests document behavior

## Risk Assessment

  **Low Risk**: New module, no changes to existing APIs

## Rollback Plan

  If issues arise:

  1. Revert to commit abc123
  2. Run tests (should still pass)
  3. Notify team

  ```

Step 4: Agent requests architect review
  - Tag architect in PR
  - Wait for feedback

Step 5: Architect reviews
  - Checks all items in code review checklist
  - May request changes
  - Or: approves

Step 6a: If changes requested
  - Agent implements feedback
  - Pushes new commits to WIP branch
  - Requests re-review
  - Back to Step 5

Step 6b: If approved
  - Architect merges PR to main
  - Architect creates commit message
  - Architect signs off (if required by policy)

Step 7: Post-merge verification
  - Architect verifies main CI/CD passes
  - Architect monitors for issues
  - If rollback needed, can revert main commit
```

### Protected Main Branch Rules

```
GitHub/GitLab Rules (Enforced):

✅ Require pull request reviews before merging
  ├─ Minimum 1 approval (architect)
  └─ Dismissal of stale reviews: false

✅ Require status checks to pass before merging
  ├─ CI/CD must pass (tests, linting, security)
  └─ All 111+ tests must pass

✅ Require branches to be up to date before merging
  ├─ No merging if main has moved
  └─ Agent must rebase WIP branch

✅ Require code reviews from code owners
  ├─ CODEOWNERS file defines ownership
  └─ Code owner must approve

✅ Require signed commits
  ├─ Architect must sign merge commit
  ├─ GPG signature verified
  └─ Audit trail clear

❌ Do NOT allow force-pushes
❌ Do NOT allow dismissal of all reviews
❌ Do NOT allow self-approval of own code
```

### Critical File Protection

```
For files marked CRITICAL (architecture, mandate, rules):

1. Backup Before Merge
   ├─ Archive/backup to protected branch
   ├─ Versioned: main-backup-<date>
   └─ Kept for 90 days

2. Manual Verification
   ├─ Architect manually reviews diff
   ├─ May request additional testing
   ├─ May require extended review window

3. Reversibility Plan
   ├─ Document how to rollback
   ├─ Keep old versions accessible
   ├─ Tag points (pre/post merge)

Critical Files:
  - EXECUTION/spec/CANONICAL/decisions/* (ADRs)
  - EXECUTION/spec/CANONICAL/rules/* (mandates)
  - .providence-migration/PHASES.md
  - .providence-migration/DECISIONS.md
  - Any mandate.spec
```

---

## Rationale

### 1. Prevents Architectural Drift

```
Before (No review gate):
  Feature X → Agent codes → Auto-commit → Oops, broke mandate!

After (Architect reviews):
  Feature X → Design approved → Code verified → Architect commits
  → Drift prevented at step 2
```

### 2. Enables Reversibility

```
With review gate:
  - Clear commit history
  - Each change approved
  - Rollback to known-good state
  - No mysterious changes
```

### 3. Supports Distributed Teams

```
Agent 1 works on Feature A (WIP branch)
Agent 2 works on Feature B (WIP branch)
Architect reviews both in parallel
No conflicts on main
Clean integration
```

### 4. Knowledge Transfer

```
PR review = documentation of decisions
Architect comments explain reasoning
Future developers understand WHY
Onboarding clearer
```

### 5. Catch Early

```
Design phase:
  - Architect reviews intent (before any code)
  - Can prevent wrong approach
  - Saves rework

Code phase:
  - Architect reviews implementation (before merge)
  - Can catch missing edge cases
  - Can verify quality

Both gates = high confidence
```

---

## Implementation (How to Use)

### Step 1: Create WIP Branch (Agent)

```bash
git checkout -b wip/feature-<name>
```

### Step 2: Push to Origin (Agent)

```bash
git push origin wip/feature-<name>
```

### Step 3: Make Changes (Agent)

1. Design phase (write FEATURE_DESIGN_*.md)
   - Get architect approval (async via Slack/PR comment)

2. Spec phase (write COMPONENT_*.md)

3. Dev phase (code + tests)
   - Ensure all tests pass: `pytest tests/ -v`
   - Ensure no warnings: `python -m pylint src/`

4. Doc phase (update docs)
   - Ensure docs are current

5. Mark ready (push final commits)

```bash
$ git add .
$ git commit -m "feat: Implement feature X

Implements ADR-007 guardrails
Design: FEATURE_DESIGN_X.md (approved)
Spec: COMPONENT_X.md
Tests: 111/111 passing ✅
Ready for review by architect
"
$ git push origin wip/feature-<name>
```

### Step 4: Create PR (Agent)

In GitHub/GitLab:

```
Title: [REVIEW] Feature: <name>
Description: [Use template from workflow section]
Assignee: @architect
```

### Step 5: Architect Reviews

Architect runs checklist:

```bash
git checkout wip/feature-<name>
pytest tests/ -v  # Verify tests pass
git diff main..HEAD  # Review changes
```

Then in PR:

- Approve with comment: "✅ Approved - LGTM"
- Or request changes: "⚠️ Please address: ..."

### Step 6: Architect Merges (or Agent Revises)

If approved:

```bash
git checkout main
git pull origin main
git merge --no-ff wip/feature-<name> -m "Merge: Feature X (Approved by architect)"
git push origin main
```

If changes needed:

- Agent makes changes on WIP branch
- Pushes new commits
- Requests re-review

---

## Consequences

### Positive ✅

- Clear accountability (architect owns commits to main)
- Prevention of architectural drift
- Early catch of design issues
- Easy rollback to known-good state
- Better knowledge transfer
- Support for parallel agent work
- Compliance trail (all changes reviewed)
- Reversibility guaranteed

### Negative ⚠️

- Slower merge velocity (need review)
- More communication overhead
- Architect bottleneck (if too many PRs)
- Initial setup of review processes

### Mitigation ⚡

- Async reviews (architect reviews when available)
- SLA for review (24 hours for non-critical)
- SLA for urgent (4 hours for critical fixes)
- Multiple architects (distribute load)

---

## Exceptions

When review can be skipped:

```
❌ NEVER skip review for:
  - Any change to MANDATE rules
  - Any change to core architecture
  - Any change to critical files
  - Any breaking API change

✅ CAN skip review for:
  - Documentation typo fixes (minor)
  - Comments/docstring improvements
  - README examples
  - Non-code files (changelog notes, etc)

  BUT: Still requires PR, just expedited review
       (architect approves quickly)
```

---

## Related Decisions

- ADR-007: Implementation Guardrails (Design first, code follows)
- ADR-001: Clean Architecture (What code must respect)
- ADR-003: Ports-Adapters (Architecture boundaries)

---

## See Also

- EXECUTION/spec/guides/operational/ (PR templates)
- CODEOWNERS (code ownership)
- .github/pull_request_template.md (PR structure)

---

## Migration Note

**Applying Retroactively:**

- v3.0 migration already completed (DECISIONS.md approved by architect)
- v3.1-beta.1 will use this from day 1
- Past commits: use best judgment for audit trail

---

## Approval Chain

```
✅ Architect approval required before ANY commit to main
   └─ Signed by: @sergio (owner)
   └─ Date: 2026-04-21
   └─ Applies: v3.1-beta.1 onwards
```
