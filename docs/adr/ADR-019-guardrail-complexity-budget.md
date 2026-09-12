# ADR-019 — Guardrail Complexity Budget

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The repository's own guardrail/governance surface (CI workflows, lint gates,
architecture validators, signing/compliance checks) has grown alongside the product
it governs. A 2026-08-01 external critique raised the risk of "governance over
governance" — a second platform dedicated to verifying the first, without a
declared budget or a metric for whether any given control is worth its cost. This
ADR establishes that budget and, as its first applied decision, resolves the
specific case that prompted it: whether the 400-line module-size warning
(`tools/architecture/validate_class_size.py`) should become a blocking gate.

---

## Decision

**Every guardrail addition or promotion (warn → block, per ADR-009's ladder) is
evaluated against an explicit cost/benefit budget, not against "how many policies
exist."**

### Guiding metric

> Violations prevented per control, at what cost, with what false-positive rate —
> not the count of controls.

### Complexity budget (baseline, 2026-08-07)

| Metric | Baseline | Source | Status | Owner | Review By |
|---|---|---|---|---|---|
| Module-size violations (>400 lines, real source only) | 4 | `validate_class_size.py --show-module-warnings`, re-run 2026-08-07, excluding the 2 `build/` false positives (see Consequences) | Measured | Sergio Lacerda | 2026-11-24 |
| CI workflow files | 13 | `.github/workflows/*.yml` count, confirmed in Strategist mission `20260807-critique-project-todo-gap-eval` | Measured | Sergio Lacerda | 2026-11-24 |
| Number of canonical governance sources | 46 | `grep -c "^  - id:" docs/spec/canonical/governance-sources.yaml`, re-measured 2026-08-24 (16 mandates + 23 guidelines + 7 handbook/docs/mirror entries) | Measured | Sergio Lacerda | 2026-11-24 |
| Product-code : enforcement-code ratio | 10.42:1 | `wc -l` over `packages/**/*.py` (excl. `tests/`, `build/`) = 60,057 lines vs. `tools/{ci,architecture,guardrails}/**/*.py` = 5,762 lines, measured 2026-08-24 | Measured | Sergio Lacerda | 2026-11-24 |
| Number of generated artifacts | 22 | 8 in `.providence/compiled/*` + 9 required release assets (`tools/release/validate_release_assets.py`'s `REQUIRED_ASSETS`: 5 compiler binaries + 3 CLI binaries + `SHA256SUMS`) + 4 additional release artifacts (`providence_cli` wheel, SBOM, Sigstore signature bundle, SLSA provenance attestation, per `release.yml`) + 1 docs site (mkdocs static build). Measured 2026-08-24 | Measured | Sergio Lacerda | 2026-11-24 |
| Supported modes/configurations | 3 Strategist personas (`debug`, `epic`, `pragmatic`) + 3 signature modes (`off`/`warn`/`strict`) + output profiles (`.strategist/output-profiles/`) | `ls .strategist/personas/`, `grep signature_mode packages/core/providence_core/src/`, `ls .strategist/output-profiles/`, measured 2026-08-24 — kept as an enumerated list, not a single count, since "modes" spans unrelated dimensions with no single meaningful sum | Measured | Sergio Lacerda | 2026-11-24 |
| Max synchronous gates per PR | TBD | Requires enumerating blocking jobs per workflow trigger | Needs measurement | Sergio Lacerda | 2026-11-24 |
| Pipeline P50/P95 wall-clock time | TBD | Requires CI run-history mining (GitHub Actions API) | Needs measurement | Sergio Lacerda | 2026-11-24 |
| Handshake token/time cost | TBD | Referenced in the critique; `providence ask` telemetry (`ask.runtime.handbook`, `ask.governance.snapshot` timings visible in this session's own hook output) is the likely source — not aggregated this pass | Needs measurement | Sergio Lacerda | 2026-11-24 |
| Guardrail false-positive rate | TBD, but see Consequences | The module-size scanner's own `build/`-directory bug (this ADR's trigger case) is itself one concrete false-positive data point. Needs the false-positive/override telemetry described in doc 06 (no emitter exists yet — see `.analysis/pending/20260824-tp4-complexity-budget-remainder-analysis.md`) before a real rate can be computed | Needs measurement (partial evidence) | Sergio Lacerda | 2026-11-24 |

Rows marked `Needs measurement` are not blocking on this ADR's acceptance — they
are the explicit backlog for making this budget quantitatively complete. This ADR
is accepted with a partially-measured budget rather than delayed until every row is
filled, consistent with ADR-009's own "evidence-based, not calendar-based"
philosophy: measurement work is scoped and tracked, not indefinitely deferred by
waiting for a perfect budget before deciding the one case in front of us.

**2026-08-24 update** (doc 06, `.analysis/refined/20260822-critique-v3-refinement/`
T-P4): five of the nine `TBD` rows above are now measured — see the `Owner`/
`Review By` columns added to satisfy doc 06's acceptance criterion that no
critical metric stays `TBD` without an owner and a deadline. The four
remaining `TBD` rows need real new instrumentation (per-gate latency
timers, an override/false-positive telemetry emitter) rather than a
one-time derivation — scoped in
`.analysis/pending/20260824-tp4-complexity-budget-remainder-analysis.md`,
not attempted in this pass.

**2026-08-25 update** (Strategist mission `20260825-tp4-instrumentation-design`,
`.analysis/refined/20260825-tp4-instrumentation-design/`): design guidance for
two of the remaining `TBD` rows is now available — a two-tier gate-latency
event/aggregation model (pipeline-level and per-gate-rule P50/P95 from one
event stream) and a dedicated `GateLatencyCollector`, covering the "Max
synchronous gates per PR" and "Pipeline P50/P95 wall-clock time" rows once
implemented (not yet — this is design only, tracked as `implementation_handoff`
in that package's `tasks.md`). The "Guardrail false-positive rate" row's two
prerequisite product questions — what mechanically counts as a "false
positive" or an "override" in this repo, and whether a guardrail-evaluation
cache should exist — remain open decisions pending user input; see that
package's `proposal.md`. This row stays `Needs measurement` until those
decisions are made.

### Applied decision: module-size enforcement

- Fix the `validate_class_size.py` module-level scan to exclude gitignored/build
  directories (root cause of 2 of the 6 currently-reported violations —
  `packages/interfaces/providence_cli/build/lib/...`).
- Grandfather the 4 remaining real violations in a new exceptions list (same
  pattern as `packages/interfaces/providence_wizard/EXCEPTIONS.md`):
  `compiler_runner.py` (661), `governance_docs_sources.py` (540),
  `ask_context.py` (494), `pipeline_builder.py` (405).
- Change `validate_class_size.py`'s exit code to also fail on any module-size
  violation **not** present in the exceptions list — i.e. block *new* violations
  immediately, without requiring the 4 existing files to be split first.
- Splitting any of the 4 grandfathered files is out of scope for this ADR — file a
  separate, scoped card per file if a split is wanted, same discipline
  `EXCEPTIONS.md` already documents ("scope and analyze that as its own pending
  item rather than folding it into this exceptions list without review").

---

## Rationale

- **Budget over headcount-of-policies:** the critique's own framing — "how many
  defects were prevented, at what cost, with what false-positive rate" — is
  adopted verbatim as this repo's guardrail evaluation principle.
- **Partial budget accepted now, not delayed:** every row does not need a number
  today; the alternative (waiting for a complete budget before deciding the
  module-size case) repeats the exact failure mode ADR-009 already rejected
  (indefinite advisory status via unresolved preconditions).
- **Grandfather, don't mass-remediate:** the 4 real violations are pre-existing,
  not newly introduced; requiring an immediate split to enable enforcement would
  block unrelated work and repeats the risk ADR-009's ladder is designed to avoid
  (activation discouraged by immediate-breakage cost). `EXCEPTIONS.md` is proven,
  low-risk prior art for exactly this situation.
- **Fix the scanner bug before changing its enforcement:** promoting a check to
  blocking while it still double-counts a gitignored build directory would block
  PRs on a tooling defect, not a real complexity signal.

---

## Consequences

- New module-size violations block CI/local gates immediately upon this decision
  landing; the 4 grandfathered files do not.
- The `build/`-directory false-positive (F4 in this ADR's originating discovery,
  `.analysis/refined/20260807-guardrail-complexity-budget-fix/analysis.md`) is
  concrete evidence for this budget's `Guardrail false-positive rate` row — the
  measurement backlog should start here rather than from zero.
- Several budget rows remain `TBD`. This ADR does not claim the budget is complete
  — only that the module-size decision it needed to make is resolved, and the
  measurement backlog for the rest is now tracked in one place instead of scattered
  across ad-hoc critique responses.

---

## Alternatives Considered

- **Full-repo split before enabling enforcement** — rejected: blocks unrelated PRs
  on 4 files nobody asked to split yet; no scoped analysis exists for any of them.
- **Leave module-size permanently informational** — rejected: this is the status
  quo the originating critique flagged; visibility without any enforcement path
  never closes the gap, per F1/F2 in the originating discovery.
- **Complete the full complexity budget before deciding module-size** — rejected:
  repeats ADR-009's rejected "wait for perfect preconditions" pattern; the module-
  size case has enough evidence (F3-F5, F7) to decide now.

---

## Links

- `docs/adr/ADR-020-progressive-enforcement-ladder.md` (related — general
  warn/block/strict philosophy this ADR's module-size decision follows)
- `packages/interfaces/providence_wizard/EXCEPTIONS.md` (prior-art pattern reused for the
  grandfather list)
- `tools/architecture/validate_class_size.py` (implementation target for the scan
  fix and enforcement change — tracked as `implementation_handoff`, not executed by
  this ADR's authoring mission)
- `.analysis/refined/20260807-guardrail-complexity-budget-fix/` (originating
  Strategist mission — full fact trail F1-F9)
