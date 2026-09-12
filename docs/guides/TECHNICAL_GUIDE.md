# Technical Guide

Reference for architects, tech leads, and senior engineers.

## Architecture Overview

Providence is structured as a hexagonal uv workspace with three tiers:

```
packages/
├── core/          # providence_core, sdd_compiler, providence_telemetry
├── features/      # providence_integration, providence_wizard
└── interfaces/    # providence_cli, providence_wizard (UI layer)

tools/             # Sovereign Factory: operational tooling and tool projects
```

- **core** — domain logic, governance compiler, compliance event logger
- **features** — orchestration, wizard flows
- **interfaces** — CLI entry points, user-facing commands
- **tools** — repo-local operational support. This includes runnable maintenance
  scripts, CI and documentation validators, governance helpers, release tooling,
  the isolated `tools/guardrails/` analysis framework, and the self-contained
  `tools/sdd-compile/` Go compiler project. These tools support the workspace but
  do not replace the product ownership boundaries in `packages/`.

## Key References

| Topic | Location |
|---|---|
| Canonical mandates and policies | `docs/spec/canonical/` |
| Architecture Decision Records | `docs/spec/decisions/` |
| Harness runtime ADRs | [docs/adr/INDEX.md](../adr/INDEX.md) |
| Pipeline orchestration | [docs/guides/PIPELINE_ORCHESTRATION.md](./PIPELINE_ORCHESTRATION.md) |
| Learning integration | [docs/guides/LEARNING_INTEGRATION.md](./LEARNING_INTEGRATION.md) |
| Robustness patterns | [docs/guides/ROBUSTNESS_PATTERNS.md](./ROBUSTNESS_PATTERNS.md) |
| Operational runbooks | [docs/runbooks/README.md](../runbooks/README.md) |
| Agent Runtime Protocol | [docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md](../runtime/protocols/AGENT_RUNTIME_PROTOCOL.md) |
| Security policy | [docs/spec/reference/SECURITY.md](../spec/reference/SECURITY.md) |
| CLI reference | [docs/spec/reference/commands/cli.md](../spec/reference/commands/cli.md) |

## Core Policies

| Policy | Description |
|---|---|
| P002 — Honest Critique | No validation theater; failures must be real |
| P003 — Mandatory Human Review | All PRs require human sign-off evidence |
| M001 — Clean Architecture | Hexagonal layering enforced |
| M002 — TDD | Test-first development required |

## CI/CD

Workflows in `.github/workflows/`:

- `health.yml` — tests, linting, Docker build, governance audit
- `docs.yml` — MkDocs build and Pages deployment
- `codeql.yml` — Static security analysis (Python + Actions)
- `release.yml` — Versioned release pipeline

### GitHub Pages Publish Flow

`docs.yml` has two stages:

1. `docs-quality`: installs deps, validates docs and builds MkDocs with `--strict`.
2. `deploy`: publishes to GitHub Pages only on `push` to `main`.

Publishing is gated by repository variable `ENABLE_GITHUB_PAGES`:

- `ENABLE_GITHUB_PAGES=true` → upload artifact + deploy job runs
- unset/`false` → docs are validated, but not published

Operational checklist:

- [docs/guides/GITHUB_PAGES_PUBLISH_CHECKLIST.md](./GITHUB_PAGES_PUBLISH_CHECKLIST.md)
- [docs/runbooks/docs-site-selector-publish.md](../runbooks/docs-site-selector-publish.md)

## Governance Artifacts

After `providence governance compile`, artifacts land in:

- `generated/master/compiled/` — master governance (msgpack + JSON)
- `generated/client/compiled/` — client/project instance artifacts

---

## Token Economy

The runtime enforces token/context budget governance to prevent context overflow and degraded model reasoning.
Four integrated modules work together:

| Module | Package | Role |
|--------|---------|------|
| `llm.py` | `providence_runtime` | Captures tokens from LLM API responses or env vars (`SDD_TOKENS_INPUT/OUTPUT`) |
| `context.py` | `providence_runtime` | Budget zone enforcement + YELLOW zone compression trigger |
| `cache.py` | `providence_runtime` | LRU context cache (128 entries, 5-min TTL) — cache hits bypass compression |
| `providers/` | `providence_runtime` | Pluggable compression providers (TF-IDF, AST, HTTP, Local) |

### Budget Zones

| Zone | Utilization | Required Action |
|------|-------------|-----------------|
| GREEN | < 70% | Proceed normally |
| YELLOW | 70–90% | Attempt compression before loading more context |
| RED | > 90% | Emit `economy.budget.warn`; MUST apply compression; skip non-essential loads |
| BREACH | ≥ 100% | Emit `economy.budget.breach` + raise `BudgetBreachError`; block all further loading |

### CLI Integration

Pass token counts to `providence ask --full`:

```bash
# Via CLI flags
providence ask --full "query" --tokens-input 150 --tokens-output 50

# Via environment variables (picked up automatically)
SDD_TOKENS_INPUT=150 SDD_TOKENS_OUTPUT=50 providence ask --full "query"
```

Budget breach guard blocks context loading:

```bash
# When budget is breached (≥100% utilization), ask in full mode exits with code 3
SDD_BUDGET_UTILIZATION_PCT=105 providence ask --full "query"
# → [Providence] BUDGET BREACH: context utilization at 105.0% (>= 100%).
# → Further context loading is blocked.
```

### Compression Mechanics

When budget utilization is 70–90% (YELLOW zone), `ContextLoader` automatically:

1. Computes target budget to bring utilization down to 70%
2. Tries providers in order: Http → Ast → Tfidf → Local
3. Uses the first provider that succeeds
4. If `compression_ratio < 1.0`, applies compressed result
5. Otherwise, keeps original context and emits `economy.compression.skip` event

**Convention:** `compression_ratio = compressed_bytes / original_bytes`. Value < 1.0 = compression applied.

→ See `docs/cognition/context-loading/COMPRESSION.md` for detailed provider mechanics and how to extend with custom providers.

---

## Drift Detection

The runtime automatically detects mismatches between session state and compiled governance. The `DriftDetector`
classifies drift into five semantic types, each with a deterministic remediation command.

### Drift Types

| Type | Meaning | Remediation |
|------|---------|-------------|
| `spec_drift` | Spec changed but artifact not recompiled | `providence governance compile` |
| `profile_drift` | Runtime profile ≠ expected profile | `providence governance validate --profile <expected>` |
| `session_drift` | Session cached to stale artifact fingerprint | `providence runtime reset-session` |
| `policy_drift` | Policy-set version mismatch | `providence governance compile --force` |
| `fingerprint_mismatch` | Artifact fingerprint differs from session | `providence governance compile` |

### Integration with `providence runtime status`

The `providence runtime status` command runs drift classification and emits telemetry:

```bash
providence runtime status
# → [runtime] drift detected: spec_drift
# →   → providence governance compile
```

Emitted events in `.providence/runtime/compliance-events.jsonl`:

- `runtime.session.start` — session loaded
- `runtime.drift.detected` — drift classified (if detected)

### Implementation

**Two-level drift API:**

1. **Legacy (fingerprint-only):** `DriftDetector.detect(session_fp, artifact_fp)` — backward-compatible
2. **Semantic:** `DriftDetector.classify(session, artifact, profile)` — full type classification

Code modules:

- `providence_runtime/drift.py` — `DriftDetector` + `DriftReport` + remediation mapping
- `providence_runtime/session.py` — `SessionState` persistence
- `packages/interfaces/providence_cli/commands/runtime.py` — `providence runtime status` integration

---

## References

- ADR-001: [Runtime Authority Boundary](../adr/ADR-001-runtime-authority-boundary.md)
- ADR-002: [Intelligence Provider Architecture](../adr/ADR-002-intelligence-provider-architecture.md)
- Mandate M005: `docs/spec/canonical/core/mandates/M005_TOKEN_ECONOMY.md`
- Canonical economy specs: `docs/spec/canonical/core/economy/`
