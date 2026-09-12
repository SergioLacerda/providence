# Threat Models — Component Analysis

**Status:** Complete (2026-05-11)

**Overview:** Systematic threat analysis using STRIDE methodology for all 7 core packages in the providence system.

---

## How to Read This Document

Each threat model follows this structure:

1. **Trust Boundary** — What inputs does the component accept? Which should be validated?
2. **Assets** — What sensitive data or capabilities are at risk?
3. **Threat Table** — STRIDE-categorized threats with likelihood, impact, and mitigations
4. **Attack Scenarios** — Realistic attack narratives
5. **Mitigations Implemented** — Controls already in place (with Phase reference)
6. **Mitigations Pending** — Future hardening opportunities

**STRIDE Categories:**

- **S** = Spoofing (identity/authentication)
- **T** = Tampering (data modification)
- **R** = Repudiation (deny actions)
- **I** = Information Disclosure (leakage)
- **D** = Denial of Service (availability)
- **E** = Elevation of Privilege (unauthorized access)

---

## providence_core — Centralized Environment & Contracts

### Trust Boundary

**Accepts (must validate):**

- File system paths from environment (`$HOME`, `$PWD`, `$GITHUB_WORKSPACE`)
- `.providence/profile` configuration file (user-modifiable)
- Package import paths (`sys.path` entries)

**Must not trust:**

- User-supplied workspace paths (without validation)
- Symlinks without following policies
- Environment variable values without type checking

### Assets

- **Workspace path resolution logic** — Used by all packages; if broken, could load wrong artifacts
- **Profile detection (master vs client)** — Controls which artifacts are loaded; wrong profile = wrong governance
- **Artifact path registry** — Central source of truth for where artifacts are stored

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Path traversal via `$PWD` | T/I | Medium | High | Input validation on paths; reject `..` and absolute paths outside workspace | ✅ Phase 5.0 |
| Symlink attack (load wrong artifact) | T/E | Low | Critical | Follow symlinks with policy: reject if symlink points outside workspace | ✅ Phase 5.1 |
| Profile confusion (load client artifacts as master) | T/E | Medium | High | Detect profile from `.providence/profile` file; validate profile type before artifact load | ✅ Phase 3.0 |
| Hardcoded `/home/` path assumption | D/I | Medium | Medium | Use environment-driven paths; test on Windows/macOS to catch hardcoded paths | ✅ Phase 4.0 |
| $HOME environment spoofing | T/E | Low | High | Walk up from `.providence/` directory; don't blindly trust $HOME | ✅ Phase 1.0 |
| Import path injection (add malicious module) | E | Low | Critical | Lock `sys.path` entries to workspace; don't add user-supplied paths | ⏳ Phase 6 (optional) |

### Attack Scenarios

**Scenario 1: Path Traversal**

```
Attacker sets $PWD=/tmp/malicious
Client code calls sdd.environment.get_sdd_paths()
Result: Loads governance from /tmp/malicious/.providence/ (wrong context)
Mitigation: Validate that resolved path stays within project workspace
```

**Scenario 2: Symlink Attack**

```
Attacker creates symlink: /tmp/project/.providence/compiled -> /etc/secret-data
Governance loader follows symlink, leaks contents
Mitigation: Follow symlinks with bounds check; log when symlink points outside workspace
```

### Mitigations Implemented

- ✅ **Phase 1.0** — Walk-up directory search for `.providence/` (trusted anchor point)
- ✅ **Phase 3.0** — Profile validation (reject unknown profile types)
- ✅ **Phase 4.0** — Cross-platform path testing (Windows, macOS, Linux)
- ✅ **Phase 5.1** — Input validation on all path inputs (reject `..`, require relative paths)

### Mitigations Pending

- ⏳ **Phase 6** — Symlink policy enforcement (explicit approval before following)
- ⏳ **Phase 6** — sys.path isolation (lock to workspace, no user additions)

---

## sdd_compiler — Spec Parsing & Artifact Generation

### Trust Boundary

**Accepts (must validate):**

- Specification files (`mandate.spec`, `guidelines.dsl`) — user-provided Markdown/DSL
- Regex patterns from parsing rules (high risk for DoS)
- Output file paths where artifacts are written

**Must not trust:**

- Malformed spec files (may cause parsing errors, timeouts, or regex DoS)
- User-supplied output paths without validation
- Temporary files created during compilation (race condition risk)

### Assets

- **Compiled artifacts** — Binary msgpack files distributed to runtime; if corrupted, entire system fails closed
- **Compilation state** — `.compile-state.json` tracks source hashes; if falsified, skips recompilation (cache poisoning)
- **Temporary files** — Build artifacts in `/tmp` or build directory; if accessed by attacker, could substitute artifacts

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Regex DoS via malformed spec | D | Medium | High | Timeout on each regex (15s per compile); log slow patterns | ✅ Phase 4.0 |
| Spec injection → arbitrary artifact data | T/E | Low | Critical | Validate spec syntax; reject unknown field types; unit tests for injection cases | ✅ Phase 2.0 |
| Artifact tampering post-compile | T | Low | Critical | Hash artifacts in metadata.json; runtime validates hash on load | ✅ Phase 5.1 |
| Temp file race condition | T/E | Low | High | Use secure temp directory; set restrictive permissions (0o600); cleanup in finally block | ✅ Phase 4.0 |
| Compile state poisoning (skip recompile) | T | Medium | Medium | Validate .compile-state.json format; ignore if invalid/corrupted | ✅ Phase 5.3 |
| Path traversal in output paths | T/I | Low | High | Reject `..` and absolute paths in output config; validate paths before mkdir | ✅ Phase 4.0 |
| Integer overflow in size calculations | D | Low | Medium | Use Python int (unbounded); sanity-check artifact size (1KB–1MB range) | ✅ Phase 5.1 |

### Attack Scenarios

**Scenario 1: Regex DoS**

```
Attacker provides malicious mandate spec with 1000-char regex (e.g., (a|a)*b)
Compiler regex engine hangs for >15s
Mitigation: Timeout enforced; compilation fails with clear error message
```

**Scenario 2: Artifact Substitution**

```
Attacker modifies governance-core.msgpack after compilation
Runtime loads corrupted artifact (e.g., wrong policy decisions)
Mitigation: Runtime validates artifact hash (SHA256 from metadata.json); rejects if mismatch
```

**Scenario 3: Compile State Poisoning**

```
Attacker edits .compile-state.json to falsify source hashes
Compiler thinks source unchanged, skips recompilation
Old/poisoned artifact remains in use
Mitigation: Validate compile state structure; use deterministic hash comparison
```

### Mitigations Implemented

- ✅ **Phase 2.0** — Spec validation (reject unknown fields)
- ✅ **Phase 4.0** — 15-second compile timeout per spec file
- ✅ **Phase 4.0** — Secure temp file handling (chmod 0o600)
- ✅ **Phase 5.1** — Artifact hash validation (SHA256 in metadata.json)
- ✅ **Phase 5.3** — Compile state validation (schema check, hash comparison)

### Mitigations Pending

- ⏳ **Phase 6** — Regex complexity analysis (reject "catastrophic backtracking" patterns)
- ⏳ **Phase 6** — Signed compilation state (HMAC or signature to prevent casual tampering)

---

## providence_runtime — Context Loading & Budget Enforcement

### Trust Boundary

**Accepts (must validate):**

- Compiled artifacts (governance-core.msgpack) — should be validated by hash
- Query strings from users (search terms)
- Budget and configuration parameters

**Must not trust:**

- Artifact integrity (must validate hash); artifact may be corrupted or substituted
- Cache contents (may be stale or poisoned); must expire with TTL
- User queries (may be designed to consume excessive budget)

### Assets

- **Governance context** — The loaded mandate/guideline data; if wrong, policy decisions are incorrect
- **Budget state** — Token tracking; if bypassed, users exceed allocation
- **Cache contents** — Cached query results; if poisoned, wrong decisions propagated
- **Policy evaluation logic** — If bypassed or corrupted, policies are not enforced

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Artifact substitution (wrong governance) | T/E | Low | Critical | Validate artifact hash (SHA256) on load; fail closed if mismatch | ✅ Phase 5.1 |
| Budget bypass (exhaust quota early) | E | Medium | High | BudgetBreachError if utilization ≥100%; enforce quota in load_result() | ✅ Phase 3.0 |
| Cache poisoning (wrong query results) | T | Medium | High | Cache TTL = 5min; cache key includes all inputs (query, max_items, item_types); deterministic SHA256 key | ✅ Phase 5.3 |
| Policy evaluation bypass | E | Low | Critical | Policy validator checks all conditions; no shortcut evaluation; log policy decisions | ⏳ Phase 6 |
| Integer overflow in token accounting | D | Low | Medium | Use Python int (unbounded); validate token_delta > 0 | ✅ Phase 3.0 |
| Concurrent cache access (race condition) | T/D | Low | Medium | Python GIL provides mutual exclusion for dict operations; document thread-safety | ✅ Phase 5.3 |
| Resource exhaustion via large queries | D | Medium | High | Truncate results to max_items; enforce max_items limit (default 5, max 100) | ✅ Phase 1.0 |

### Attack Scenarios

**Scenario 1: Artifact Substitution**

```
Attacker replaces governance-core.msgpack with modified version
Modified version relaxes policy requirements (e.g., removes security mandates)
Runtime loads and uses poisoned artifact without detection
Mitigation: Hash validation on load; mismatch detected immediately
```

**Scenario 2: Budget Bypass**

```
Attacker modifies runtime memory to bypass budget check
Exhausts token quota without triggering BudgetBreachError
Mitigation: Budget check on every load_result() call; error raised before policy applied
```

**Scenario 3: Cache Poisoning**

```
Attacker injects stale/wrong result into cache (e.g., via race condition)
User queries and receives wrong guidance (cached result)
Mitigation: TTL = 5min; cache key is deterministic (no collisions); cache eviction on size
```

### Mitigations Implemented

- ✅ **Phase 1.0** — Result truncation (max_items limit)
- ✅ **Phase 3.0** — Budget tracking with BudgetBreachError on ≥100%
- ✅ **Phase 5.1** — Artifact hash validation (SHA256)
- ✅ **Phase 5.3** — LRU cache with 5-min TTL and deterministic key (SHA256)

### Mitigations Pending

- ⏳ **Phase 6** — Policy evaluation audit logging (log every policy decision)
- ⏳ **Phase 6** — Cache integrity verification (periodically verify cache hits are correct)

---

## providence_telemetry — Event Logging & Token Tracking

### Trust Boundary

**Accepts (must validate):**

- Event data from all components (query results, token counts, error messages)
- File system write operations (telemetry.jsonl path)

**Must not trust:**

- User-supplied event field values (may contain PII or injection)
- Log file permissions (may be modified post-write)
- Timestamp accuracy (clock skew possible)

### Assets

- **Telemetry log (telemetry.jsonl)** — Audit trail of all operations; if modified, audit trail compromised
- **Token tracking** — Budget enforcement depends on accurate token counts; if falsified, budget bypassed
- **Event immutability** — Once written, events should not be editable (no retroactive corrections)

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Log injection (craft false events) | T/R | Medium | Medium | Validate event structure; reject unknown event types; log as sanitized JSON only | ✅ Phase 5.4 |
| PII leakage (log user data) | I | Medium | High | Never log query results, file paths, or user input; log only metrics and types | ✅ Phase 3.0 |
| Log file tampering | T/R | Low | Medium | Write-once append (telemetry.jsonl immutable after creation); use file permissions (0o644) | ✅ Phase 5.4 |
| Log file overflow (disk exhaustion) | D | Low | Medium | Rotate logs at 10MB; keep 30 days; auto-delete old logs | ✅ Phase 3.0 |
| Token count falsification | T/E | Medium | High | Validate tokens_delta is positive integer; audit token sum vs budget | ✅ Phase 3.0 |
| Timestamp spoofing (out-of-order events) | R/T | Low | Medium | Validate timestamp is ISO 8601 UTC; reject timestamps >1 hour in past/future | ✅ Phase 5.4 |
| Event repudiation (deny actions) | R | Low | Medium | Immutable log; all operations logged before execution; log includes actor context | ⏳ Phase 6 |

### Attack Scenarios

**Scenario 1: PII Leakage**

```
Developer logs query text: "Find me security guidance for OAuth2 in AWS"
Log file is backed up to unencrypted cloud storage
Attacker accesses backup, learns about company's security interests
Mitigation: Never log query content, only query type (e.g., "context_load")
```

**Scenario 2: Log Injection**

```
Attacker crafts event with fake fields: {"type":"budget_update","tokens_delta":-999999}
Event is appended to telemetry.jsonl
Budget calculations use poisoned event, incorrect balance
Mitigation: Validate event structure on write; reject unknown fields
```

**Scenario 3: Log File Tampering**

```
Attacker gains shell access, edits telemetry.jsonl to remove evidence of activity
Audit trail is compromised
Mitigation: Use append-only semantics; file permissions prevent owner modifications after write
```

### Mitigations Implemented

- ✅ **Phase 3.0** — No PII in logs (metrics only, no query content)
- ✅ **Phase 3.0** — Log rotation by size (10MB threshold)
- ✅ **Phase 3.0** — Token validation (positive integers)
- ✅ **Phase 5.4** — Event structure validation (reject unknown types)
- ✅ **Phase 5.4** — Timestamp validation (ISO 8601 UTC)

### Mitigations Pending

- ⏳ **Phase 6** — Write-once file permissions (chmod 0o444 after rotation)
- ⏳ **Phase 6** — Event signature (HMAC or hash chain to detect tampering)
- ⏳ **Phase 6** — Remote syslog export (audit trail on separate secure server)

---

## providence_integration — Artifact Validation & Deployment

### Trust Boundary

**Accepts (must validate):**

- Compiled artifacts from sdd_compiler (via file path)
- Backup and manifest file paths
- Deployment state from previous runs

**Must not trust:**

- Artifact file contents (must validate hash, format)
- Backup files (may be corrupted)
- Manifest metadata (may be stale or falsified)

### Assets

- **Artifact deployment workflow** — Ensures only validated artifacts reach runtime
- **Backup and rollback capability** — Critical for recovery if artifact corrupted
- **Deployment manifest** — Record of what was deployed when; if falsified, audit trail lost
- **Artifact hash registry** — Used for integrity verification; if corrupted, hash validation fails

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Hash collision (substitute artifact undetected) | T | Low | Critical | Use SHA256 (collision resistance: 2^128); validate before and after deployment | ✅ Phase 5.1 |
| Backup file substitution | T/E | Low | High | Backup stored with hash in manifest; validate backup hash before restore | ✅ Phase 5.2 |
| Manifest forgery (fake deployment record) | S/T | Low | Medium | Manifest includes source hashes + timestamps; compare to git history if needed | ✅ Phase 5.2 |
| Idempotency abuse (deploy multiple times, cause issues) | D | Low | Medium | Integration validates idempotency; same source hash → same artifact hash | ✅ Phase 5.2 |
| Race condition (backup overwrites active artifact) | T/D | Low | Medium | Use atomic file operations (rename); backup to .backup/ directory | ✅ Phase 5.1 |
| Disk space exhaustion (many backups) | D | Medium | Medium | Keep only last 2 backups; rotate old files | ✅ Phase 5.2 |
| Artifact not present (load failure) | D | Medium | High | Validation checks file existence; fail with clear error if missing | ✅ Phase 5.1 |

### Attack Scenarios

**Scenario 1: Backup Substitution**

```
Attacker replaces generated/master/compiled/backup/governance-core.msgpack with poisoned version
Operator runs rollback assuming backup is clean
System uses corrupted artifact
Mitigation: Backup hash stored in manifest; validation detects mismatch
```

**Scenario 2: Manifest Forgery**

```
Attacker edits DEPLOYMENT_MANIFEST.json to claim artifact was deployed 6 months ago
Audit trail falsified
Mitigation: Manifest includes source hashes + timestamps; can cross-check with git history
```

**Scenario 3: Concurrent Deployment**

```
Two CI jobs deploy simultaneously; first backs up old artifact, second overwrites backup before it's validated
Result: No safe rollback path
Mitigation: Atomic operations (rename); backup to separate directory; manifest lock
```

### Mitigations Implemented

- ✅ **Phase 5.1** — SHA256 hash validation (artifact and backup)
- ✅ **Phase 5.1** — Artifact presence validation (file exists check)
- ✅ **Phase 5.2** — Backup strategy (last 2 backups only)
- ✅ **Phase 5.2** — Manifest generation (source hashes, timestamps)
- ✅ **Phase 5.2** — Idempotency validation (same source → same artifact hash)

### Mitigations Pending

- ⏳ **Phase 6** — Manifest signing (HMAC or signature for authenticity)
- ⏳ **Phase 6** — Concurrent deployment prevention (mutex on manifest)
- ⏳ **Phase 6** — Audit log of all deployments (immutable audit trail)

---

## providence_cli — User Input Handling & Command Execution

### Trust Boundary

**Accepts (must validate):**

- Command-line arguments (`--profile`, `--output`, query strings)
- Environment variables (`$SDD_PROFILE`, `$HOME`)
- File system paths provided by user

**Must not trust:**

- User-supplied arguments without type checking
- Environment variables (may be injected)
- Workspace path (may be symlink or path traversal attempt)

### Assets

- **Command execution flow** — If hijacked, wrong commands run
- **Profile selection** — If spoofed, wrong artifacts loaded
- **Output handling** — If exploited, data leakage or XSS (if output used in web context)
- **Workspace resolution** — If confused, wrong context/governance loaded

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Argument injection via --profile | T/E | Low | High | Whitelist profile values (master, client only); reject unknown values | ✅ Phase 1.0 |
| Environment variable injection ($SDD_PROFILE) | T/E | Medium | High | Validate $SDD_PROFILE against whitelist; CLI flag overrides env var | ✅ Phase 5.1 |
| Path traversal via query argument | I | Low | Medium | Queries are strings, not file paths; no special processing needed | ✅ Phase 1.0 |
| Command confusion (wrong subcommand called) | E | Low | Medium | Typer enforces strict command matching; no dynamic dispatch | ✅ Phase 1.0 |
| Output injection (if used in templates/scripts) | I | Low | Medium | Use Rich for terminal output (auto-escaped); --json uses standard json.dumps() | ✅ Phase 5.1 |
| Workspace confusion (load from wrong .providence/) | I | Medium | High | Walk-up from CWD to find .providence/; validate profile before using artifacts | ✅ Phase 1.0 |
| Privilege escalation via CLI flags | E | Low | Critical | No --force or --assume-yes flags; all destructive operations require confirmation | ✅ Phase 1.0 |

### Attack Scenarios

**Scenario 1: $SDD_PROFILE Injection**

```
Attacker sets SDD_PROFILE=master in CI pipeline
Client-only CLI reads master artifacts (confidential governance)
Mitigation: Whitelist profile values; reject unknown values
```

**Scenario 2: Workspace Confusion**

```
Attacker creates symlink: /home/user/project/.providence -> /etc/sensitive-data
User runs providence ask from project directory
CLI loads wrong governance
Mitigation: Validate symlink destination; reject if outside workspace bounds
```

**Scenario 3: Output Injection**

```
Query result contains HTML/JavaScript: "<img src=x onerror=alert('XSS')>"
Output piped to web tool without escaping
Mitigation: Rich auto-escapes terminal output; --json uses json.dumps() (safe)
```

### Mitigations Implemented

- ✅ **Phase 1.0** — Strict command matching (Typer enforces)
- ✅ **Phase 1.0** — No --force flags (confirmation required for destructive ops)
- ✅ **Phase 1.0** — Workspace auto-detection (walk-up from CWD)
- ✅ **Phase 5.1** — Environment variable validation ($SDD_PROFILE whitelist)
- ✅ **Phase 5.1** — Output escaping (Rich, json.dumps())

### Mitigations Pending

- ⏳ **Phase 6** — Input rate limiting (prevent query spam)
- ⏳ **Phase 6** — Command audit logging (log all CLI invocations)

---

## providence_wizard — Artifact Loading & State Persistence

### Trust Boundary

**Accepts (must validate):**

- Artifact files from integration (governance-core.msgpack)
- Wizard state file (wizard-state.json — user preferences)
- User interactions (theme, layout selections)

**Must not trust:**

- Artifact file integrity (must validate hash)
- Wizard state file (may be corrupted or edited)
- CLAUDE.md generation (template-based; must escape values)

### Assets

- **Loaded artifacts** — Governance context displayed to user; if corrupted, wrong guidance shown
- **Wizard state** — User preferences; tampering causes UX issues (not critical)
- **CLAUDE.md generation** — Template output; if injected, arbitrary code possible
- **User interface** — Interactive display; if compromised, misinformation shown

### Threat Table

| Threat | STRIDE | Likelihood | Impact | Mitigation | Status |
|--------|--------|-----------|--------|------------|--------|
| Artifact load from wrong path | I | Low | High | Wizard reads artifact path from manifest; validate path before loading | ✅ Phase 5.4 |
| Corrupted artifact (missing/unreadable fields) | D/I | Low | Medium | Error handling with graceful degradation; show "Artifact corrupted" message | ✅ Phase 5.4 |
| Wizard state file tampering | T | Low | Low | State file is preferences only (no security value); json.loads() safe | ✅ Phase 5.4 |
| CLAUDE.md code injection | T/E | Low | Critical | Template rendering escapes variables; no interpolation of artifact data | ✅ Phase 5.4 |
| Arbitrary file read via path | I | Low | High | Wizard only reads from manifest-specified path; no user-supplied paths | ✅ Phase 5.4 |
| Out-of-memory (large artifact) | D | Low | Medium | Load artifact only on demand; lazy loading prevents large loads on startup | ✅ Phase 5.3 |

### Attack Scenarios

**Scenario 1: Artifact Load from Wrong Path**

```
Attacker modifies DEPLOYMENT_MANIFEST.json to point to /etc/passwd
Wizard loads and parses /etc/passwd as governance artifact
Failure in artifact parsing, but sensitive file accessed
Mitigation: Manifest path validation; ensure path is in expected directory
```

**Scenario 2: CLAUDE.md Code Injection**

```
Attacker crafts artifact with field value: `${DANGEROUS_CODE}`
Wizard generates CLAUDE.md using template: "# {{artifact.field}}"
Output file contains unescaped code
Mitigation: Template rendering escapes all variables; safe substitution
```

**Scenario 3: Corrupted Artifact**

```
Artifact file is truncated or has invalid msgpack format
Wizard attempts to parse and crashes
User sees raw error, not helpful guidance
Mitigation: Error handling; display "Artifact corrupted, rebuild with sdd compile" message
```

### Mitigations Implemented

- ✅ **Phase 5.3** — Lazy loading (artifacts loaded on-demand, not startup)
- ✅ **Phase 5.4** — Error boundaries (graceful failure messages)
- ✅ **Phase 5.4** — Artifact path validation (from manifest only)
- ✅ **Phase 5.4** — Safe template rendering (escaping/no interpolation)

### Mitigations Pending

- ⏳ **Phase 6** — Artifact signature verification (HMAC or Sigstore attestation)
- ⏳ **Phase 6** — State file encryption (encrypt wizard-state.json at rest)

---

## Cross-Component Threat Scenarios

### Scenario 1: Supply Chain Compromise

**Attack:** Attacker compromises the providence GitHub account or PyPI account.

**Threat Path:**

1. Attacker publishes poisoned wheel (providence-core 1.0.1) to PyPI
2. Users install poisoned version
3. Poisoned code loads artifacts from attacker's server instead of local
4. Attacker gains visibility into all governance contexts

**Mitigations Implemented:**

- ✅ Sigstore/Cosign artifact attestation (release.yml §5.1.A) — proves artifact comes from GitHub Actions
- ✅ SBOM generation (release.yml §5.1.A) — enables SCA tools to detect compromised dependencies
- ✅ Dependabot alerts on CVEs (§5.1.D) — catches malicious dependency updates
- ✅ pip-audit in CI (§5.1.C) — detects published CVEs before release

**Mitigations Pending:**

- ⏳ **Phase 6** — PyPI 2FA enforcement (account takeover prevention)
- ⏳ **Phase 6** — Binary reproducibility (verify wheel contents match source)

### Scenario 2: Artifact Integrity During Transit

**Attack:** Attacker intercepts wheel file during download or installation.

**Threat Path:**

1. User runs `pip install providence-core==1.0.0`
2. Attacker performs MITM attack, serves poisoned wheel
3. Poisoned code is installed and executed

**Mitigations Implemented:**

- ✅ TLS 1.2+ in transit (PyPI enforces HTTPS)
- ✅ Wheel hash validation by pip (wheel includes RECORD with hashes)
- ✅ Sigstore attestation (release.yml) — proves authenticity of source wheel

**Mitigations Pending:**

- ⏳ **Phase 6** — PEP 740 signature support (direct wheel signatures)

### Scenario 3: Artifact Upgrade Path (Version Confusion)

**Attack:** Attacker crafts artifact compatible with old version but incompatible with new version.

**Threat Path:**

1. System running providence-core 1.0.0, providence-runtime 0.1.0 (unsynced versions)
2. User upgrades only providence-core to 1.0.1
3. New version has incompatible artifact format
4. Runtime fails to load artifact; system degraded

**Mitigations Implemented:**

- ✅ §5.2.A Per-package hatch-vcs versioning — every package resolves its version directly from the release tag, ensuring all packages release at the same version without a separate sync step
- ✅ §5.2.B Release workflow verification (checks all packages match tag)
- ✅ COMPATIBILITY.md (§5.2.C) — documents version matrix and breaking changes

**Mitigations Pending:**

- ⏳ **Phase 6** — Runtime version checking (artifact includes min/max compatible versions)

### Scenario 4: Governance Drift (Stale Artifacts)

**Attack:** Attacker prevents compilation, forcing system to use stale governance.

**Threat Path:**

1. Attacker modifies mandate.spec but blocks compilation (DoS on compiler)
2. System continues using old governance artifact
3. Security policies are not updated
4. Attacker exploits gaps in stale policy

**Mitigations Implemented:**

- ✅ §5.3.A Incremental compilation state (.compile-state.json) — tracks source hashes
- ✅ §5.3.B Runtime caching (5-min TTL) — prevents unbounded staleness
- ✅ SDD validation workflow (sdd-validation.yml §5.1.E) — runs on every commit

**Mitigations Pending:**

- ⏳ **Phase 6** — Artifact age limit enforcement (fail if artifact >7 days old)
- ⏳ **Phase 6** — Freshness check before policy decision (verify artifact is current)

---

## Threat Model Review Schedule

| Component | Next Review | Owner |
|-----------|-------------|-------|
| providence_core | 2026-11-11 | @SergioLacerda |
| sdd_compiler | 2026-11-11 | @SergioLacerda |
| providence_runtime | 2026-11-11 | @SergioLacerda |
| providence_telemetry | 2026-11-11 | @SergioLacerda |
| providence_integration | 2026-11-11 | @SergioLacerda |
| providence_cli | 2026-11-11 | @SergioLacerda |
| providence_wizard | 2026-11-11 | @SergioLacerda |

Update threat models every 6 months or when a new security incident occurs.

---

## Related Documentation

- [RFC_PROCESS.md](RFC_PROCESS.md) — Process for proposing security improvements (new ADRs)
- [BREAKING_CHANGES.md](BREAKING_CHANGES.md) — RFC process for security-relevant breaking changes
- [COMPATIBILITY.md](COMPATIBILITY.md) — Version management and compatibility matrix
- [Security Policy](../reference/SECURITY.md) — Security policies and vulnerability reporting
