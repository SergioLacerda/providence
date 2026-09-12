# Architecture Decision Records — Providence Runtime

Local ADRs specific to the Providence runtime layer. These are distinct from the framework-level ADR catalog under `docs/spec/decisions/`.

---

## Published Framework ADR Mirrors

### ADR-015: Python-to-Go Compiler Migration Performance Comparison (2026-07-01)

**Decision:** Supersede placeholder compiler benchmark claims with a real Python
vs Go compiler comparison.

**Links:**

- [ADR-015-go-compiler-migration-performance.md](ADR-015-go-compiler-migration-performance.md)
- Referenced by `docs/spec/guides/PERFORMANCE.md` section 5.3.C.

---

## 📋 Harness-Local ADRs

### ADR-001: Runtime Authority Boundary (2026-05-10)

**Decision:** Define the authority boundary between governance specifications and runtime implementation.

**Rationale:**

- Governance specs (`docs/spec/canonical/`) are the source of truth
- Compiled artifacts are immutable snapshots
- Runtime execution engine (`providence_runtime`) is a pure executor, not a normative authority
- Prevents runtime from overriding specs

**Links:**

- [ADR-001-runtime-authority-boundary.md](ADR-001-runtime-authority-boundary.md)
- Implements M003 (Context Awareness), M005 (Token Economy)
- Enforced by `GovernanceOrchestrator` in `providence_core`

---

### ADR-002: Intelligence Provider Architecture (2026-05-11)

**Decision:** Implement pluggable intelligence providers for context compression and analysis.

**Rationale:**

- Single if/else solution doesn't scale (new providers always needed)
- Factory pattern too rigid for runtime swapping
- ABC/Protocol allows runtime discovery and fallback chain
- `ProviderRegistry` enables cascading: HTTP → AST → TFIDF → LocalProvider

**Providers:**

- `HttpProvider` — External intelligence service (if configured)
- `AstProvider` — Abstract syntax tree analysis
- `TfidfProvider` — Statistical text frequency analysis
- `LocalIntelligenceProvider` — Fallback (always available)

**Links:**

- [ADR-002-intelligence-provider-architecture.md](ADR-002-intelligence-provider-architecture.md)
- Implements M005 (Token Economy) compression obligations
- Implementation: `providence_runtime` package, `intelligence_providers.py`

---

### ADR-003: Skill Handler Strategy Pattern (2026-05-19)

**Decision:** Replace `if skill.name == "sdd-ask"` chains in `run_skill` with per-skill handler classes (`AskHandler`, `CorrectHandler`, etc.) discovered via name convention.

**Rationale:**

- `run_skill` had cyclomatic complexity of 12 (`# noqa: C901`)
- Every new skill with lifecycle hooks required editing `run_skill` in 2–3 places
- Strategy pattern: adding a new skill = new handler class, zero changes to `run_skill`

**Links:**

- [ADR-003-skill-handler-strategy-pattern.md](ADR-003-skill-handler-strategy-pattern.md)
- Implementation: `_skill_executor.py` (handlers + `_get_skill_handler` factory)

---

### ADR-004: SkillEngine Split into SkillRegistry + SkillExecutor (2026-05-19)

**Decision:** Split the 414-line `SkillEngine` into `SkillRegistry` (disk loading, lookup, export) + `SkillExecutor` (run_skill, commands, telemetry) + `SkillEngine` thin facade.

**Rationale:**

- Registry and execution have different change reasons and different collaborators
- Each class independently testable without the full engine
- Zero breaking changes: all callers continue to use `SkillEngine`

**Links:**

- [ADR-004-skillengine-registry-executor-split.md](ADR-004-skillengine-registry-executor-split.md)
- Files: `_skill_registry.py`, `_skill_executor.py`, `skills.py`

---

### ADR-005: `_REGISTRY` Stays in `skills.py` (2026-05-19)

**Decision:** Keep the hardcoded `_REGISTRY` dict in `skills.py` and pass it to `SkillRegistry` as a constructor parameter, preserving a live reference for test mutation support.

**Rationale:**

- Moving `_REGISTRY` to `_skill_registry.py` is semantically clean but architecturally unnecessary
- `SkillRegistry(fallback, project_root)` is generic and testable with any dict
- Live reference (`self._fallback`) allows post-construction mutations to remain visible via `get_skill`

**Links:**

- [ADR-005-registry-fallback-in-skills-facade.md](ADR-005-registry-fallback-in-skills-facade.md)

---

### ADR-006: CLI Canonical JSON Envelope — Big-Bang Cut (2026-05-21)

**Decision:** All CLI JSON responses use a single canonical envelope `{status, command, ok, error, data}`. Legacy mirroring and `SDD_CLI_ENVELOPE_STRICT` removed atomically.

**Rationale:**

- Dual-payload pattern required maintaining two code paths indefinitely
- Feature flag had no planned graduation date
- Big-bang cut guarantees the codebase is never in an ambiguous state post-merge

**Links:**

- [ADR-006-cli-canonical-json-envelope.md](ADR-006-cli-canonical-json-envelope.md)
- Implementation: `packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`

---

### ADR-007: Environment Variable Precedence Matrix (2026-05-21)

**Decision:** A single explicit matrix governs all path-resolution env vars, with R/O/F classification per environment (`test`, `runtime`, `dev/prod`).

**Rationale:**

- Per-module ad-hoc resolution caused silent cross-test contamination and non-reproducible CI behaviour
- Single contract is predictable, testable, and auditable

**Links:**

- [ADR-007-environment-variable-precedence-matrix.md](ADR-007-environment-variable-precedence-matrix.md)

---

### ADR-008: `trace_id` Propagation as Explicit Function Argument (2026-05-21)

**Decision:** `trace_id` travels as an explicit argument through the call chain. No thread-locals, no globals.

**Rationale:**

- Thread-locals and context vars create invisible coupling and break in async contexts
- Explicit argument makes propagation visible in signatures and testable in isolation

**Links:**

- [ADR-008-trace-id-as-explicit-argument.md](ADR-008-trace-id-as-explicit-argument.md)
- Related: M007 (Telemetry Enforcement)

---

### ADR-020: Progressive Enforcement Ladder (WARN → BLOCK → STRICT) (2026-05-21)

**Decision:** Governance enforcement uses a three-phase ladder; rules advance based on measured stability, not calendar.

**Rationale:**

- Binary enforce/skip creates incentive to delay activation indefinitely
- Evidence-based promotion prevents rules from becoming permanent advisory signals

**Links:**

- [ADR-020-progressive-enforcement-ladder.md](ADR-020-progressive-enforcement-ladder.md)
- [ADR-021-threshold-signoff.md](ADR-021-threshold-signoff.md)
- [ADR-009-ci-fail-closed-matrix.md](ADR-009-ci-fail-closed-matrix.md) — companion matrix mapping CI controls onto the warn/block/strict phases
- Related: M010 (Governance Hardening)

---

### ADR-010: structlog as the Logging Primitive (2026-05-21)

**Decision:** `structlog` replaces raw `print()` across all 6 packages. A single `providence_core/logging.py` module is the only place structlog is configured. ConsoleRenderer for dev/TTY, JSONRenderer for production/non-TTY.

**Rationale:**

- stdlib logging requires more complex configuration for structured output
- Single config module prevents renderer drift and ensures processor chain consistency

**Links:**

- [ADR-010-structlog-as-logging-primitive.md](ADR-010-structlog-as-logging-primitive.md)
- Implementation: `packages/core/providence_core/src/providence_core/logging.py`

---

### ADR-011: Golden Snapshot Drift Classification (2026-05-21)

**Decision:** Drift is classified as Type A (volatile-only), B (backward-compat), or C (breaking). Each type has a defined evidence requirement and review path.

**Rationale:**

- Ad-hoc refresh produced no audit trail; regressions accepted silently
- Typed classification scales review burden to actual risk of the change

**Links:**

- [ADR-011-golden-snapshot-drift-classification.md](ADR-011-golden-snapshot-drift-classification.md)

---

### ADR-012: AskRuntimeContext — Dependency-Injection Seam for `providence ask` Testing (2026-06-10)

**Decision:** Introduce an `AskRuntimeContext` object bundling the collaborators currently reached via `unittest.mock.patch("providence_cli.commands._ask_backend.<symbol>")`, passed explicitly to `_ask_cmd_impl` and its orchestration helpers.

**Rationale:**

- `_ask_backend.py` (1060 lines) is the only `providence_cli` file still over the Wave 8 ≤300-line gate, blocked by ~121 `mock.patch` call sites across 9 test files
- "Extract + re-export" (the pattern used for every other Wave 8 file) fails here because the orchestration chain itself — not just the helpers — needs to move
- A context object decouples patched collaborators from the physical module location of their call sites, unblocking incremental decomposition

**Links:**

- [ADR-012-ask-runtime-context-seam.md](ADR-012-ask-runtime-context-seam.md)
- `packages/interfaces/providence_cli/REFACTOR_NOTES.md` (Wave 1 / Wave 8 — `_ask_backend.py` blocker history)

---

### ADR-013: Python-Native Pipeline Composition for Governed Skills (2026-06-11)

**Decision:** Execute `sdd-pipeline` as a composed runtime flow using
`ContextCarrier`, `PipelineHandler`, executor-managed stage orchestration, and
config-driven decision gates.

**Rationale:**

- CLI-only orchestration could not express runtime-native gates, freeze
  escalation, or shared retry/timeout semantics across stages
- Context propagation needed provenance-aware state sharing instead of repeated
  plain-dictionary copies
- The implementation roadmap explicitly required externalized gate rules and a
  governed ask → diagnose → correct → converge pipeline

**Links:**

- [ADR-013-pipeline-composition.md](ADR-013-pipeline-composition.md)
- `docs/guides/PIPELINE_ORCHESTRATION.md`

---

### ADR-016: CLI Envelope Schema Is Manually Maintained (2026-07-24)

**Decision:** Keep `CommandResult` and `CommandError` as frozen dataclasses and
publish a manually maintained JSON Schema validated by contract tests.

**Links:**

- [ADR-016-cli-envelope-schema-manual.md](ADR-016-cli-envelope-schema-manual.md)
- Schema: `tests/contract/schemas/cli_command_envelope.schema.json`

---

### ADR-017: Governance Signing KMS Is Deferred (2026-07-24)

**Decision:** Keep local Ed25519 signing and trusted keyring validation as the
supported model. Defer KMS provider integration to a separate scoped demand.

**Links:**

- [ADR-017-governance-signing-kms-deferred.md](ADR-017-governance-signing-kms-deferred.md)
- Implementation reference: `packages/core/providence_core/src/providence_core/utils/compiler_runner.py`

---

### ADR-018: Block Dependabot typescript Major Bumps in apps/landing (2026-07-30)

**Decision:** Ignore Dependabot major-version updates for `typescript` in
`apps/landing` until the Astro checking toolchain supports the next major.

**Rationale:**

- `@astrojs/check@0.9.10` supports `typescript@"^5.0.0 || ^6.0.0"`, not
  `typescript@7.x`
- Dependabot grouping cannot wait for compatible peer-dependency major releases
- Minor and patch updates remain allowed inside the supported major range

**Links:**

- [ADR-018-dependabot-typescript-major-ignore.md](ADR-018-dependabot-typescript-major-ignore.md)
- Related config: `.github/dependabot.yml`

---

### ADR-019: Guardrail Complexity Budget (2026-08-07)

**Decision:** Every guardrail addition/promotion is evaluated against an explicit
cost/benefit budget (violations prevented per control, at what cost, with what
false-positive rate) instead of policy headcount. First applied decision:
grandfather the 4 real current module-size violations and make the 400-line module
check blocking for new violations going forward.

**Rationale:**

- Repeats ADR-009's "evidence-based, not calendar-based" philosophy at the budget
  level, not just per-rule
- Grandfathering avoids blocking unrelated work on pre-existing violations while
  still closing the "warn-only forever" gap

**Links:**

- [ADR-019-guardrail-complexity-budget.md](ADR-019-guardrail-complexity-budget.md)
- Related: ADR-009 (Progressive Enforcement Ladder)
- Implementation reference: `tools/architecture/validate_class_size.py`,
  `packages/interfaces/providence_wizard/EXCEPTIONS.md` (grandfather-list pattern)

## 🧾 Operational Appendices

These artifacts support governance operations but are not ADRs:

- [Threshold signoff: progressive-enforcement-ladder](ADR-021-threshold-signoff.md)

---

## 📚 Related

- **Framework ADRs:** see `docs/spec/decisions/` — ADR-001 through ADR-010
- **Authority Hierarchy:** [docs/spec/canonical/core/INDEX.md](../spec/canonical/core/INDEX.md) — CORE is immutable kernel
- **Runtime Layer:** [docs/runtime/protocols/AGENT_ENTRYPOINT.md](../runtime/protocols/AGENT_ENTRYPOINT.md) — Bootstrap protocol

---

## 🔄 Adding New Harness ADRs

When adding a new runtime ADR:

1. **Filename:** `ADR-NNN-title-slug.md`
2. **Format:** Use standard ADR format (Decision, Rationale, Impact, Alternatives, Links)
3. **Authority:** If conflicts with governance specs → governance specs win
4. **Testing:** Include test file references if applicable
5. **Review:** Require SDD core team review before merge

---

**Last Updated:** 2026-05-24
**Authority:** Providence v0.1.0+
**Scope:** Runtime implementation decisions only
