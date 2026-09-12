# ADR-010: Spec-to-Compiled Artifact Contract

## Status

- **Accepted** ✅
- Proposed: 2026-05-05
- Accepted: 2026-05-05
- Review Date: 2026-11-05

---

## Context

The SDD framework's core value proposition is transforming human-readable governance specs into
binary artifacts that can be validated at runtime by agents and CI pipelines.  Without an explicit
written contract for this transformation, changes to either the source spec format or the compiler
can silently break downstream consumers.

This ADR records the formal contract: what constitutes a valid input spec, what the pipeline
guarantees as output, and what invariants the compiled artifacts must satisfy.

The precise Compiler I/O artifact schema and fingerprint/signature invariants are maintained in
`docs/spec/canonical/specifications/compiler_io_contract.md`. This ADR remains the architectural
decision record for the compiled artifact pipeline; the canonical specification is the executable
contract consumed by the focused compiler I/O contract tests.

---

## Pipeline Overview

```
docs/spec/canonical/core/policies/*.md          ← Source specs (human-readable)
              │
              ▼  PHASE 1 — PipelineBuilder
generated/master/build/governance-core.json     ← Build artifact (intermediate)
generated/master/build/governance-client.json   ← Build artifact (intermediate)
              │
              ▼  PHASE 2 — GovernanceCompiler
generated/master/compiled/governance-core.json  ← Compiled JSON (canonical)
generated/master/compiled/governance-client.json
generated/master/compiled/governance-core.compiled.msgpack   ← Runtime binary
generated/master/compiled/governance-client-template.compiled.msgpack
              │
              ▼  PHASE 3 — DeploymentManager
generated/client/compiled/governance-client.compiled.msgpack ← Deployed to client
```

The `GovernanceOrchestrator` coordinates all three phases end-to-end.

---

## Decision

### 1. Source Spec Format (v3.0)

A valid governance source spec is a Markdown file in `docs/spec/canonical/` with the naming
convention `<ID>_<SLUG>.md` where:

- `<ID>` matches the pattern `[A-Z]\d{3}` (e.g., `M001`, `P003`)
- `<SLUG>` is a human-readable identifier in `UPPER_SNAKE_CASE`

**Minimal required fields** (parsed from Markdown headers and frontmatter):

| Field | Required | Example |
|-------|----------|---------|
| `id` | Yes | `M001` |
| `title` | Yes | `Clean Architecture` |
| `type` | Yes | `MANDATE` \| `GUIDELINE` \| `POLICY` |
| `metadata.category` | No | `architecture` |
| `metadata.criticality` | No | `MANDATORY` \| `RECOMMENDED` \| `OPTIONAL` |

**Invariants:**

- IDs must be unique across all source files in the same category (core vs. client)
- IDs must be sorted before fingerprint calculation (deterministic ordering)
- Emoji and Unicode in titles are allowed; they are preserved verbatim

### 2. PHASE 1 Output — Build Artifacts

`governance-core.json` and `governance-client.json` in `generated/*/build/`:

```json
{
  "category": "CORE",
  "version": "3.0",
  "fingerprint": "<sha256-hex-64-chars>",
  "items": [
    { "id": "M001", "type": "mandate" }
  ]
}
```

**Guarantees:**

- `fingerprint` is SHA-256 of the sorted, canonical JSON serialisation of `items`
- `items` are sorted by `id` ascending (lexicographic)
- `version` matches `PipelineBuilder.SCHEMA_VERSION = "3.0"`
- Output is deterministic: same source → same fingerprint across runs and environments

### 3. PHASE 2 Output — Compiled JSON

`governance-core.json` (enriched) and `governance-client.json` in `generated/*/compiled/`:

```json
{
  "category": "CORE",
  "version": "3.0",
  "fingerprint": "<sha256-hex-64-chars>",
  "items": [
    {
      "id": "M001",
      "title": "Clean Architecture",
      "metadata": { "category": "architecture", "criticality": "MANDATORY", "owner": "..." }
    }
  ]
}
```

**Guarantees:**

- `fingerprint` matches the PHASE 1 build artifact fingerprint (not recomputed)
- `items` contain all fields from source plus enriched `metadata`
- No `generated_at` volatile timestamp in the core JSON (stable for golden-file comparison)

### 4. PHASE 2 Output — Binary Artifacts (msgpack)

`*.compiled.msgpack` files are binary serialisations of the compiled JSON.

**Guarantees:**

- Deserialises to the same structure as the compiled JSON
- Used at runtime by `AgentHandshakeProtocol` Layer 1 and Layer 4
- File integrity is verified by checking `fingerprint` against `.providence/profile core_hash[:16]`

### 5. Compiler Invariants (breaking change definition)

A change to the pipeline is **breaking** if it:

- Removes or renames a top-level key (`category`, `version`, `fingerprint`, `items`)
- Changes the `id` field format (currently `[A-Z]\d{3}`)
- Changes the fingerprint algorithm (currently `sha256`, full 64-char hex)
- Changes item sort order

A change is **non-breaking** if it:

- Adds new optional fields to items (`metadata.*`)
- Adds new top-level optional keys
- Changes emoji or whitespace in `title`

### 6. Validation

The formal executable validation of this contract lives in:

- `tests/contract/test_governance_schema.py` — schema invariants + golden-file regression guard
- `.github/workflows/health.yml` — `Verify Fingerprint Determinism` step

When the golden file diverges (intentional spec change), update:

```
tests/contract/fixtures/governance_core.golden.json
```

with the documented update command in the module docstring.

---

## Consequences

**Positive:**

- New compiler contributors have a single reference for what they can and cannot change
- AHP integration tests have explicit invariants to verify against
- Breaking changes are identifiable before merging (golden-file diff in CI)

**Negative:**

- Adding new mandatory fields requires updating this ADR, the golden file, and the contract tests
  (intended — this is the friction that surfaces breaking changes)

---

## References

- `packages/features/providence_integration/src/providence_integration/builders/governance/pipeline_builder.py` — PHASE 1
- `packages/core/sdd_compiler/src/sdd_compiler/governance_compiler.py` — PHASE 2
- `packages/core/providence_core/src/providence_core/governance_orchestrator.py` — PHASE 3 coordinator
- `tests/contract/test_governance_schema.py` — executable contract tests
- `docs/spec/canonical/specifications/compiler_io_contract.md` — precise Compiler I/O contract
- `tests/contract/fixtures/governance_core.golden.json` — golden file
- `.github/workflows/health.yml` — `Verify Fingerprint Determinism` step
- ADR-009 — test location convention
- sdd_criticas.md CAT-F item F5
