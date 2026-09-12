# SDD Integration — Decision Log

**Module:** `packages/features/providence_integration`
**Purpose:** Bridge between compiler (artifacts) and runtime (queries), wizard initialization
**Owner:** @SergioLacerda

---

## DEC-2026-001: Two-Stage Integration (Compile → Validate → Load) (2026-02-01)

**Decision:** Integration = (1) compile artifacts, (2) validate manifest, (3) load into runtime

**Rationale:**
- Clean separation: Compiler owns artifacts, runtime owns queries
- Checkpoints: Validate at each stage, fail fast
- Observable: Each stage logged separately
- Testable: Can mock/stub at each boundary

**Stages:**
1. Compiler: mandate.spec → governance-core.msgpack
2. Validator: Check metadata.json matches artifact
3. Runtime: Load artifact into ContextLoader
4. Wizard: Initialize user-facing interface

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-002: Integration Assumes Master Layout (2026-03-01)

**Decision:** Integration code expects generated/master/compiled/ layout (not client/)

**Rationale:**
- Development: Integration runs in master workspace (dev machine)
- Publishing: Wizard packages artifacts for distribution
- Simplification: Don't support parallel master+client paths

**Consequence:** Can't compile in client profile, only master

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-003: Validation Checks (Defensive) (2026-03-10)

**Decision:** Integration validates: file exists, hash matches, artifact loadable, manifest valid

**Rationale:**
- Safety: Don't hand bad artifacts to runtime
- Debugging: Which stage failed? (compile, transport, storage)
- Recovery: Clear error message + remediation step

**Checks:**
1. File exists: `governance-core.compiled.msgpack` present?
2. Size reasonable: Between 1KB and 1MB (sanity)
3. Hash matches metadata: SHA256 in metadata.json == actual?
4. Deserializable: msgpack.unpackb() succeeds?
5. Manifest valid: metadata.json valid JSON?

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-004: Artifact Rollback / Backup Strategy (2026-03-15)

**Decision:** Before writing new artifact, backup old one to .backup/

**Rationale:**
- Safety: Can rollback if new artifact corrupted
- Investigation: Keep old artifact for diff/analysis
- Automation: Backup automatic, no manual steps
- Space: Rotate, keep only last 2 backups

**Paths:**
- Current: generated/master/compiled/governance-core.compiled.msgpack
- Backup: generated/master/compiled/backup/governance-core.compiled.msgpack.backup

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-005: Integration Manifest (Deployment Tracking) (2026-04-01)

**Decision:** Create DEPLOYMENT_MANIFEST.json after successful integration

**Rationale:**
- Audit: When was last successful deployment?
- Rollback: Can reference old manifest to revert
- Metrics: Deployment frequency, success rate
- Wizard: Uses manifest to show current governance status

**Manifest fields:**
- version: "3.0.0" (artifact version)
- deployed_at: ISO timestamp
- source_hashes: {mandate_hash, guidelines_hash} (for reproducibility)
- artifacts: {paths, sizes, hashes}
- status: "success" | "failed"

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: Integration Idempotency (2026-04-10)

**Decision:** Running integration twice with same source = same result (idempotent)

**Rationale:**
- CI/CD: Can safely re-run failed builds
- Reproducibility: Same source → same artifact hash
- No side effects: Integration doesn't "accumulate"

**Consequence:** All temp files cleaned up, artifacts deterministic

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-007: Wizard Initialization (Client Profile Setup) (2026-05-01)

**Decision:** Integration exports artifacts for wizard to use in client profile

**Rationale:**
- Distribution: Wizard bundles artifacts with user's instance
- Isolation: Each user/org has separate governance artifacts
- Updates: User can update wizard independently of master

**Flow:**
1. Master: Compiler builds artifacts
2. Integration: Validates, backs up, manifests
3. Wizard: Reads artifacts from manifest
4. Client: User receives wizard + bundled governance

**Status:** ACTIVE
**Owner:** @SergioLacerda

---
