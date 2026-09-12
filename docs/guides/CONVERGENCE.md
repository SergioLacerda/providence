# Convergence Policy

Operational rules for AI-assisted development in this workspace.
The goal: sustainable velocity through controlled convergence — not fast patching.

Source: `.sergioL/convergencia_ia.md` (2026-05-20)

---

## Core Principle

Replace the degradation cycle:

```
quick patch -> reactive fix -> regression -> new patch
```

With the convergence cycle:

```
diagnosis -> explicit scope -> minimal patch -> deterministic validation -> human review
```

---

## Operational Rules

### Rule 1 — Controlled Freeze

While any active regression is open:

- No new features
- No architectural expansion
- No speculative refactoring

### Rule 2 — Diagnose Before Fix

No correction patch without:

- A causal hypothesis
- Minimum evidence (log, test output, or code reference)
- A test that reproduces the failure

### Rule 3 — Mandatory Minimum Scope

Every execution must declare:

- Permitted paths (files/modules in scope)
- Required validations (test suite, lint, type check)
- Rollback criteria (what triggers abort)

### Rule 4 — Human Gate on Irreversible Git Actions

Agents do not execute autonomously:

- `git commit`, `git push`, `git pull`, `git reset`, `git cherry-pick`

Agents prepare commands and summarize changes. Final execution is human.

---

## Execution Checklist (per cycle)

1. Confirm governance/runtime state: `providence runtime status`
2. Classify task (PATH A/B/C/D) and risk level
3. Define execution contract (scope + validations)
4. Run diagnose and capture root cause
5. Apply minimum patch
6. Run deterministic validation (`pytest`, `ruff`, type checks)
7. Record result in `docs/incidents/FAILURE_LEDGER.md`
8. Submit for human review

---

## Convergence KPIs

| KPI | Target | Measurement |
|-----|--------|-------------|
| PRs with explicit diagnosis | ≥ 95% | PR description has "Root cause:" section |
| PRs without regression | ≥ 98% | CI test suite passes on merge |
| MTTR of recurring failures | Decreasing weekly trend | Failure Ledger MTTR field |
| Failures with confirmed root cause | ≥ 90% | Failure Ledger "Confirmed cause" filled |
| Changes outside permitted scope | 0% | Scope contract declared before execution |

---

## Tooling Map

| Purpose | Command |
|---------|---------|
| Governance health | `providence runtime status` |
| Governance validation | `providence governance validate` |
| Drift and telemetry | `providence audit` |
| Token economy | `sdd metrics summary` |
| Registry reconciliation | `providence governance reconcile-registries` |
| Quality guardrails | `pytest`, `ruff check`, `ruff format` |
| Failure tracking | `docs/incidents/FAILURE_LEDGER.md` |
| Incident response | `docs/incidents/PLAYBOOKS.md` |

---

## Entropy Signals (stop and diagnose when you see these)

- Corrections that address symptoms without confirming root cause
- Changes touching files outside the declared scope
- Validation skipped or deferred ("will test later")
- No single source of truth for current task status
- Multiple unresolved regressions open simultaneously
