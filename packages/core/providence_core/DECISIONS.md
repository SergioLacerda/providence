# SDD Core — Decision Log

**Module:** `packages/core/providence_core`
**Purpose:** Core utilities, environment detection, artifact handling
**Owner:** @SergioLacerda

---

## DEC-2026-001: Centralized Environment & Path Registry (2026-01-10)

**Decision:** Single source of truth for all paths (get_sdd_paths(), resolve_profile())

**Rationale:**
- Before: Each module had hardcoded paths → inconsistent, brittle
- After: All modules use get_sdd_paths() → consistent, maintainable
- Enables workspace detection without env vars
- Supports master/client profile switching

**Trade-offs:**
- Pro: One place to update paths
- Con: Breaking change to add new path type (must update all callers)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-002: Profile-Based Workspace Detection (2026-01-15)

**Decision:** Support both master (dev) and client (user) workspace profiles

**Rationale:**
- Master: Full development repo, all packages editable
- Client: Single installed package, read-only artifacts
- Enables same code to run in dev and production
- Supports "master → client → master" upgrade paths

**Alternatives rejected:**
- Single profile: Can't separate dev/user concerns
- Environment variables: Fragile, hard to debug

**Implementation:**
- `resolve_profile()`: Walk up from CWD looking for .providence/profile
- Fail fast with WorkspaceNotInitializedError (not silent fallback)
- Support override via SDD_PROFILE env var or --profile flag

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** `packages/core/providence_core/src/providence_core/utils/environment.py`

---

## DEC-2026-003: TOML over ConfigParser for Settings (2026-02-01)

**Decision:** Use tomllib (Python 3.11+) / tomli (3.10) for config files

**Rationale:**
- pyproject.toml already TOML, not duplicating format
- TOML more readable than ConfigParser/INI
- Typed values (arrays, tables) without manual parsing
- Python 3.11+ has tomllib built-in

**Trade-offs:**
- Pro: Native format, readable
- Con: Adds tomli dependency for Python 3.10

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Alternative considered:** Use .providence/config.yaml → rejected, TOML preferred

---

## DEC-2026-004: Artifact Dataclass (CompiledArtifact) (2026-02-15)

**Decision:** Represent artifacts as immutable dataclasses, not dicts

**Rationale:**
- Type-safe: .items, .metadata are guaranteed attributes
- Validation: __post_init__ checks invariants
- Serializable: Can convert to/from JSON/MessagePack
- IDE support: Better autocomplete and docs

**Alternatives rejected:**
- Plain dict: No type safety, easy to have wrong keys
- NamedTuple: Less flexible, harder to validate
- Pydantic: Overkill, adds heavy dependency

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** `packages/core/providence_core/src/providence_core/artifacts.py`

---

## DEC-2026-005: GovernanceItem IDs as Semantic Strings (2026-03-01)

**Decision:** Item IDs like "M001", "G042", not integer PKs

**Rationale:**
- Human-readable: `providence ask M001` is clearer than `providence ask 1`
- Stable across versions: ID doesn't change when reordered
- Self-describing: "M" prefix = mandate, "G" = guideline
- Queryable in docs: Grep `M001` to find all references

**Trade-offs:**
- Pro: Semantic, stable
- Con: Longer keys, need validation (must be \[MG]\d{3})

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: No External Cache Library (Roll Our Own) (2026-05-01)

**Decision:** Implement LRU cache in Python, not use functools.lru_cache or cachetools

**Rationale:**
- functools.lru_cache: Only per-function, not configurable
- cachetools: Large dependency for 100 lines of code
- Custom: Full control over cache key, TTL, stats
- Lightweight: No dependencies, easy to test

**Trade-offs:**
- Pro: Minimal dependencies, full control
- Con: Maintenance burden if we add features

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** `packages/core/providence_runtime/src/providence_runtime/cache.py`

**Future consideration:** If performance becomes critical, evaluate redis/memcached

---

## DEC-2026-007: Environment Detection Strategies (Ordered) (2026-04-01)

**Decision:** Detect repo root via: (1) CWD walk-up, (2) __file__ location, (3) GITHUB_WORKSPACE env

**Rationale:**
- Walk-up: Works in dev, user shell, IDE
- __file__: Works when installed in editable mode (pip install -e)
- GITHUB_WORKSPACE: Works in GitHub Actions
- Fallback to CWD if all fail (less helpful, but graceful)

**Consequence:** Never trust a single detection method

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** `detect_repo_root()` in environment.py

---

## DEC-2026-008: Version Synchronization Across Monorepo (2026-05-05)

**Decision:** All 7 packages release with same version number (e.g., 0.2.0)

**Rationale:**
- Monorepo: Single source of truth
- Dependency: All packages depend on each other
- Simple: One version to track, not 7
- Release: Tag v0.2.0, build all packages

**Consequence:** Patch in providence_runtime → all packages bump to next patch version

**Implementation (updated 2026-07-17):** All 9 workspace packages use
`hatch-vcs` dynamic versioning (`[tool.hatch.version] source = "vcs"`), each
resolving its version directly from the release tag at build time. The
original implementation (`tools/release/sync_versions.py`, which rewrote a
static `version = "..."` line in every `pyproject.toml`) was removed — it's no
longer needed once no package has a static version to rewrite, and removing it
also eliminated the `SETUPTOOLS_SCM_PRETEND_VERSION` workaround the sync step
required (it rewrote files in place without committing, leaving the tree
"dirty" in a way hatch-vcs's dirty-check would otherwise misread).

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 5.2 Compatibility Governance

---

## DEC-2026-009: Supported Python Versions (2026-05-11)

**Decision:** Support Python 3.10, 3.11, 3.12 (stable); 3.13 (experimental, allow-fail)

**Rationale:**
- 3.10: Earliest version with modern syntax (match/case, type hints)
- 3.12: Latest stable release (current date)
- 3.13: Test forward compatibility, catch breaking changes
- Drop 3.9: Too old, difficult dependency conflicts

**Policy:** Minimum 3 stable releases + 1 experimental

**Consequence:** Can't use features from 3.14+ yet, only Python 3.10+ features allowed

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Phase 5.2 Compatibility Matrix

---

## DEC-2026-010: No Runtime Configuration Files (Environment-Driven) (2026-05-08)

**Decision:** Configuration via .providence/profile (workspace), env vars (runtime), CLI flags (explicit)

**Rationale:**
- .providence/profile: Persistent workspace config (located via walk-up)
- Env vars: CI/CD, containerized environments
- CLI flags: One-off overrides, highest priority
- NO: ~/.providencerc, /etc/sdd/config, or XML bloat

**Trade-offs:**
- Pro: Simple, Unix-like
- Con: Can't use complex nested structures (but don't need to)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-011: CLI as Adapter-Only for Capability Commands (2026-05-13)

**Decision:** `providence_cli` commands for capabilities must delegate domain execution to runtime/core services.

**Rationale:**
- Preserves clean layering: interface vs domain.
- Prevents command-level drift in policy/enforcement behavior.
- Maximizes reuse across CLI, wizard flows, and external orchestrators.

**Consequence:** handshake/compliance logic must observe runtime-produced skill state, never parse CLI internals.

**Status:** ACTIVE
**Owner:** @SergioLacerda
