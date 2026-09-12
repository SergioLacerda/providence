# Incident Response Playbooks

**Overview:** Step-by-step guides for responding to common SDD framework incidents.

Each playbook follows this structure:

1. **Symptoms:** How to recognize the problem
2. **Root Causes:** What can go wrong
3. **Response Steps:** Numbered phases (Detect → Contain → Investigate → Recover → Learn)
4. **Escalation:** When to call for help
5. **Prevention:** How to avoid next time

---

## Quick Reference

| Incident | Priority | MTTR Target | On-Call Playbook |
|----------|----------|-------------|------------------|
| [Governance Artifact Corrupted](#governance-artifact-corrupted) | **CRITICAL** | 15 min | Yes |
| [Standalone Compiler Release Assets Missing](#standalone-compiler-release-assets-missing) | HIGH | 20 min | Yes |
| [Compiler Timeout](#compiler-timeout) | HIGH | 30 min | Yes |
| [Budget Exhausted](#budget-exhausted-mid-request) | HIGH | 20 min | Yes |
| [Cache Poisoning](#cache-poisoning-wrong-results-returned) | HIGH | 25 min | Yes |
| [Supply Chain Compromise](#supply-chain-compromise) | **CRITICAL** | 10 min | Yes |
| [Context Load Failure](#context-load-failure) | MEDIUM | 45 min | No |
| [Telemetry Pipeline Blocked](#telemetry-pipeline-blocked) | MEDIUM | 60 min | No |

---

## Governance Artifact Corrupted

### Symptoms

- `providence ask` returns: `artifact validation failed`
- `providence governance compile` succeeds, but `providence runtime status` shows corrupt artifact
- CI tests pass, but production deployment fails
- Hash mismatch between SBOM and actual artifact

### Root Causes

- Disk corruption during build (rare)
- Incomplete download/network error
- Concurrent write during artifact generation
- Malicious tampering (very rare, but possible)
- Accidental modification of compiled/ directory

### Response Steps

#### Phase 1: Detect & Alert (5 min)

1. **Confirm corruption:**

   ```bash
   sha256sum generated/master/compiled/governance-core.compiled.msgpack
   # Compare with expected hash in SBOM or .compile-state.json
   ```

2. **Check git status:**

   ```bash
   git log --oneline -5 docs/spec/canonical/
   git status generated/master/compiled/
   ```

3. **Page on-call if:**
   - Hash mismatch confirmed
   - Multiple artifacts affected
   - Production environment impacted

#### Phase 2: Containment (10 min)

1. **Stop affected services:**

   ```bash
   systemctl stop providence-runtime providence-wizard  # if applicable
   ```

2. **Block release:**

   ```bash
   git tag -d v$(cat packages/core/providence_core/pyproject.toml | grep version | head -1)
   # Don't push to remote yet
   ```

3. **Notify stakeholders:**
   - Slack: `#incidents` channel
   - Message: "Governance artifact validation failure — investigating. ETA: 15 min"

#### Phase 3: Investigation (30 min)

1. **Verify source integrity:**

   ```bash
   python -m sdd_compiler  # Attempt recompile
   sha256sum generated/master/compiled/governance-core.compiled.msgpack
   # If hash differs from corrupted: code issue
   # If hash matches corrupted: infrastructure/tampering issue
   ```

2. **Check Sigstore attestation (Phase 5.1):**

   ```bash
   cosign verify-blob \
     --certificate-identity-regexp="" \
     --certificate-oidc-issuer-regexp="" \
     generated/master/compiled/governance-core.compiled.msgpack
   ```

3. **Review recent commits:**

   ```bash
   git log --oneline --all -- "docs/spec/canonical/" | head -20
   git diff HEAD~5 HEAD -- "docs/spec/canonical/"
   ```

4. **Check CI/CD logs:**
   - GitHub Actions: `.github/workflows/release.yml`
   - Check for build errors, timeouts, network issues

#### Phase 4: Recovery (15–60 min depending on cause)

**Scenario A: Code Issue (Source Changed)**

```bash
# Fix the source file
vi docs/spec/canonical/core/mandate.spec

# Recompile
python -m sdd_compiler

# Verify new artifact
sha256sum generated/master/compiled/governance-core.compiled.msgpack

# Re-sign with Cosign
cosign sign-blob --key ... generated/master/compiled/governance-core.compiled.msgpack

# Create new release tag
git tag v0.2.1 -m "Fix: Governance artifact corruption"
git push origin v0.2.1
```

**Scenario B: Infrastructure Issue (Corruption During Build)**

```bash
# Clean build artifacts
rm -rf generated/master/compiled/*

# Rebuild from source
python -m sdd_compiler

# Verify reproducibility (hash should match previous good build)
sha256sum generated/master/compiled/governance-core.compiled.msgpack

# If hash stable: Infrastructure was transient, proceed
# If hash unstable: Code issue (go to Scenario A)
```

**Scenario C: Tampering (Sigstore Fails)**

```bash
# ESCALATE IMMEDIATELY to security@...
# Do NOT use or serve the artifact
# Investigate access logs:
git log --oneline -- "generated/master/compiled/" | head -20
# Check who has push access to main branch
# Review branch protection rules

# Contact infra team: possible unauthorized access
```

#### Phase 5: Postmortem (24h)

- [ ] Document root cause in GitHub issue
- [ ] Assign owner to fix (if code issue)
- [ ] Create prevention task: "Add artifact integrity check to CI"
- [ ] Update this playbook with new insights
- [ ] Share learning in team standup

### Escalation

- **Level 1 (5 min):** On-call engineer acknowledges
- **Level 2 (10 min):** Team lead involved if tampering suspected
- **Level 3 (15 min):** Security team if breach confirmed

### Prevention

- ✅ SBOM generation (Phase 5.1): Artifact hashes recorded
- ✅ Sigstore attestation (Phase 5.1): Artifact signatures verified
- ⏳ Artifact integrity tests: CI verifies hash after build
- ⏳ Read-only compiled/ in production: Prevents accidental modification

---

## Standalone Compiler Release Assets Missing

### Symptoms

- A standalone client (installed from PyPI/Git, no local repo checkout) fails
  `providence init --default` or any command that compiles governance, with:
  `PHASE 2 error: No sdd-compile release binary found for version X.Y.Z
  (asset sdd-compile-<goos>-<goarch>; tried tags vX.Y.Z and VX.Y.Z)`
- `curl -s https://api.github.com/repos/<org>/<repo>/releases/tags/<TAG>`
  returns `"assets": []` even though the release itself exists.
- The GitHub Releases web UI shows only the automatic
  `Source code (zip)` / `Source code (tar.gz)` links, no `sdd-compile-*`
  files or `SHA256SUMS`.

### Root Causes

- The release job in `.github/workflows/release.yml` failed or was skipped
  after the tag/release was created but before `softprops/action-gh-release`
  uploaded `dist/*` (e.g. a step between them failed).
- A release for the tag was created manually (e.g. via the GitHub UI) before
  CI ran, and CI's release step did not subsequently attach assets.
- **Not a root cause:** GitHub's automatic source archives are generated by
  GitHub itself and are never listed in the Releases API `assets` array —
  their presence in the UI does not mean the client can download anything.

### Response Steps

#### Phase 1: Detect (2 min)

```bash
# Confirm the release has zero assets (not just "few assets")
curl -s https://api.github.com/repos/<org>/<repo>/releases/tags/<TAG> | jq '.assets | length'
```

#### Phase 2: Contain (5 min)

- Tell affected standalone users to set `SDD_COMPILE_BIN` to a locally built
  `tools/sdd-compile/bin/providence-compile` (built via `make build-compiler`) as an
  immediate workaround, or pin to the previous good release.

#### Phase 3: Investigate (5 min)

```bash
# Check whether the release job actually ran and which step failed
# (GitHub Actions UI -> Actions -> Release -> failed run for the tag)

# Locally reproduce the exact asset contract the CI gate checks
python3 tools/release/validate_release_assets.py dist
```

#### Phase 4: Recover (10 min)

If a `dist/` with all six required files
(`sdd-compile-linux-amd64`, `sdd-compile-linux-arm64`,
`sdd-compile-darwin-amd64`, `sdd-compile-darwin-arm64`,
`sdd-compile-windows-amd64.exe`, `SHA256SUMS`) already exists locally or as a
CI workflow artifact, validate it first, then attach it as an emergency
recovery:

```bash
python3 tools/release/validate_release_assets.py dist

gh release upload <TAG> dist/sdd-compile-linux-amd64 \
  dist/sdd-compile-linux-arm64 \
  dist/sdd-compile-darwin-amd64 \
  dist/sdd-compile-darwin-arm64 \
  dist/sdd-compile-windows-amd64.exe \
  dist/SHA256SUMS
```

Manual upload is an emergency measure only. Immediately follow it with a new
patch tag that goes through the full CI pipeline (build → install smoke →
release → post-publication asset gate) so a clean CI run becomes the
authoritative evidence that the pipeline works end to end.

#### Phase 5: Postmortem

- [ ] Confirm which CI step failed (or whether the release was created
      out-of-band) and fix the underlying cause.
- [ ] Verify `release.yml` still has all three gates: pre-publication staged
      asset check, standalone install smoke, and post-publication release API
      check (see `docs/guides/release/STANDALONE_COMPILER_ASSETS.md`).
- [ ] Record the incident in `docs/incidents/FAILURE_LEDGER.md`.

### Prevention

- ✅ Pre-publication staging gate: `tools/release/validate_release_assets.py`
  fails the build before publish if any asset or `SHA256SUMS` entry is missing.
- ✅ Standalone install smoke (`release-install-smoke` job) proves the packaged
  compiler binary can run the install path before publication.
- ✅ Post-publication release API gate fails the release job if the GitHub
  Release does not expose all required assets after publish.
- ✅ `overwrite_files: true` on the release-creation step so re-running the
  workflow for the same tag repairs a broken release instead of erroring.

---

## Compiler Timeout

### Symptoms

- Build fails with: `subprocess timeout after 15 seconds`
- CI workflow hangs then fails
- `python -m sdd_compiler` takes >15s to complete
- Large spec files cause timeouts

### Root Causes

- Spec file unusually large (>10K items)
- Regex parsing inefficiency on complex patterns
- Insufficient CI runner resources (CPU, memory)
- Nested/recursive patterns in DSL
- System under high load (many concurrent builds)

### Response Steps

#### Phase 1: Detect (2 min)

```bash
# Check compile time locally
time python -m sdd_compiler

# If <15s: CI environment issue
# If >15s: Code issue
```

#### Phase 2: Investigate (10 min)

```bash
# Check spec size
wc -l docs/spec/canonical/core/mandate.spec
du -h docs/spec/canonical/core/

# Profile the compiler (add timing)
python -c "
import time
start = time.perf_counter()
# ... run compiler ...
print(f'Total: {time.perf_counter() - start:.2f}s')
"
```

#### Phase 3: Fix (variable)

**Option A: Increase timeout** (quick fix, band-aid)

```yaml
# .github/workflows/health.yml
- name: Compile specs
  run: timeout 30 python -m sdd_compiler
  # Changed from 15 to 30 seconds
```

✅ **When:** Temporary, while investigating root cause

**Option B: Split large spec** (medium fix)

```bash
# Split mandate.spec into mandate-core.spec + mandate-extensions.spec
# Compile separately, merge results
```

✅ **When:** Spec legitimately >5K items

**Option C: Optimize regex** (proper fix)

```python
# Replace inefficient regex with state machine or tokenizer
# Profile: which patterns are slow?
# Optimize in-order
```

✅ **When:** Regex is inherently slow, even on small specs

#### Phase 4: Recovery

1. Apply fix (A, B, or C above)
2. Test locally: `time python -m sdd_compiler` should be <5s
3. Merge PR, re-run CI
4. Confirm compile completes within 15s

#### Phase 5: Postmortem

- [ ] Document which option was chosen and why
- [ ] Add benchmark test to prevent regression
- [ ] Update `tests/perf/benchmark_performance.py` with timeout check

### Prevention

- ✅ Benchmark suite (Phase 5.3): Measures compile time at 1K/5K/10K scales
- ⏳ Compile time assertions: CI fails if compile >10s (early warning)
- ⏳ Profiling in CI: Per-build timing breakdown

---

## Budget Exhausted Mid-Request

### Symptoms

- `providence ask` returns: `BudgetBreachError: budget utilization ≥ 100%`
- User session halts, no further context loads allowed
- Token economy metrics show 100%+ utilization
- Repeated queries fail after ~5 requests

### Root Causes

- User misconfigured budget (set too low)
- Single query consumes large number of tokens
- Budget not reset between sessions
- Token accounting bug (over-charging)

### Response Steps

#### Phase 1: Detect (1 min)

```bash
# Check governance/runtime state
providence runtime status

# Check token economy metrics
providence metrics summary
```

#### Phase 2: Investigate (5 min)

```bash
# Check session state
cat .providence/runtime/providence-runtime-sessions.json | jq '.' 2>/dev/null || echo "Session file not found"

# Check token consumption by query
providence metrics summary --last-hours 24

# Is budget legitimately exhausted?
# Or is it a bug?
```

#### Phase 3: Fix (depends on cause)

**Scenario A: User Misconfigured Budget (Most common)**

```bash
# Reset runtime state and re-bootstrap
providence bootstrap

# Or: increase token_budget_ceiling in pyproject.toml
# [tool.sdd.runtime]
# token_budget_ceiling = 200000  # was 100000
```

**Scenario B: Single Query Too Expensive**

```bash
# Check recent events to identify expensive queries
providence metrics summary --last-hours 1

# Single query consumed many tokens → expensive
# Options:
# 1. Use more specific query (fewer matches)
# 2. Use --skill to limit context to a specific path
# 3. Increase token_budget_ceiling in pyproject.toml

providence ask "architecture" --skill "diagnose"  # route to lighter path
```

**Scenario C: Budget Not Reset**

```bash
# Between sessions, budget should reset automatically.
# If not, it's a bug — file an issue.

# Workaround: re-bootstrap the runtime state
providence bootstrap

# File bug: "Budget not reset between sessions"
```

**Scenario D: Token Accounting Bug**

```bash
# Reproduce: providence ask "<query>" N times
# Check if tokens charged correctly via metrics

providence metrics summary --last-hours 1

# File bug with reproduction steps
# Escalate to maintainer

# Workaround: re-bootstrap the runtime state
providence bootstrap
```

#### Phase 4: Verify

```bash
# Confirm runtime is healthy
providence runtime status
# Should show: "PROVIDENCE GOVERNANCE: drift=none | governance=ok | ..."

# Try query again
providence ask "test"
# Should succeed
```

### Prevention

- ✅ Token economy tests (Phase 3): Test budget exhaustion scenarios
- ✅ Budget validation (Phase 3): Warn if budget <10% remaining
- ⏳ Budget auto-reset: Reset budget on new session
- ⏳ Per-query limits: Cap max_items to prevent expensive queries

---

## Cache Poisoning (Wrong Results Returned)

### Symptoms

- `providence ask` returns incorrect context items
- Same query returns different results at different times
- Cache hit shows stale/wrong data
- Inconsistent behavior between fresh vs cached results

### Root Causes

- Cache key collision (different queries, same hash)
- Artifact ID not properly included in cache key
- Stale data not evicted after TTL
- Concurrent cache modification (race condition)

### Response Steps

#### Phase 1: Detect (2 min)

```bash
# Reproduce: run same query multiple times
providence ask "mandate"

# Check if results consistent
providence ask "mandate" > query1.txt
providence ask "mandate" > query2.txt
diff query1.txt query2.txt
# If different: cache poisoning
```

#### Phase 2: Clear Cache (1 min)

```bash
# Clear cache manually to restore service
rm -f .providence/runtime/.providence-cache.md

# Verify fresh results
providence ask "mandate"
# Should show correct results
```

#### Phase 3: Investigate (10 min)

```bash
# Check recent compliance events for cache anomalies
tail -100 .providence/runtime/compliance-events.jsonl | jq . | tail -20

# Look for:
# 1. Same key, different values?
# 2. Entries not evicted after TTL?
# 3. Artifact ID collisions?

# Run tests
pytest packages/core/providence_runtime/tests/test_*.py -k cache -v
# Look for failures in cache tests
```

#### Phase 4: Fix (depends on cause)

**Scenario A: Cache Key Collision**

```python
# In packages/core/providence_runtime/cache.py
# Check _make_key() function

# Example bug:
# key = f"{query}:{max_items}"  # Missing artifact_id!
# Should be:
# key = f"{artifact_id}:{query}:{max_items}:..."
```

**Scenario B: TTL Not Enforced**

```python
# Check: does cache.get() validate timestamp?
if elapsed > entry.ttl_seconds:
    del self.cache[key]
    return None  # Cache miss, recompute
# If missing: entries not expired properly
```

**Scenario C: Race Condition**

```python
# Add thread-safe locking
import threading
self.cache_lock = threading.RLock()

def get(self, ...):
    with self.cache_lock:
        # ... cache logic ...
```

#### Phase 5: Verify Fix

```bash
# Run cache integrity tests
pytest packages/core/providence_runtime/tests/test_cache.py -v

# Stress test: concurrent queries
python tests/perf/benchmark_performance.py --concurrent 10

# Verify no poisoning
```

### Prevention

- ✅ Cache module (Phase 5.3): Unit tests for collisions
- ⏳ Cache poisoning test: Intentionally create collisions, verify eviction
- ⏳ Concurrent access test: Multiple threads/processes, verify consistency
- ⏳ Cache metrics: Monitor hit rate, eviction rate for anomalies

---

## Supply Chain Compromise

### Symptoms

- `pip install providence` installs older/unexpected version
- SBOM contains unexpected dependencies
- Artifact signature fails Sigstore verification
- CI detects new CVE in a dependency (pip-audit)

### Root Causes

- Dependency with unpatched CVE (most common)
- PyPI package hijack (rare, but critical)
- Compromised GitHub Actions runner (rare)
- Accidental upload of malicious code (very rare)

### Response Steps

#### Phase 1: Detect (2 min)

```bash
# CVE in dependency detected by pip-audit
pip-audit 2>&1 | grep "CRITICAL\|HIGH"

# Or: Sigstore verification fails
cosign verify-blob --certificate-identity-regexp="" ...
# Output: "signature validation failed"

# Or: SBOM shows unexpected package
cat .providence/compiled/sbom.spdx.json | jq '.packages[] | select(.name=="suspicious")'
```

#### Phase 2: Immediate Containment (5 min)

**If CVE in dependency:**

```bash
# DO NOT RELEASE
git tag -d v0.2.1  # If already tagged
# or don't push if not yet published

# File emergency issue
gh issue create --title "[SECURITY] CVE-XXXX in dependency YYY" \
  --body "Blocking v0.2.1 release pending patch"
```

**If signature verification fails:**

```bash
# DO NOT RELEASE
# Investigate immediately

# Check who signed
cosign verify ... 2>&1 | grep "certificate subject"

# Check CI logs
gh run view $(gh run list | head -1 | awk '{print $1}')
```

**If PyPI compromise suspected:**

```bash
# DO NOT UPDATE PyPI package
# Contact PyPI security: security@pypi.org
# Provide: package name, version, suspicious changes
```

#### Phase 3: Investigation (30 min)

**For CVE in dependency:**

```bash
# Check which dependency
pip-audit --desc | grep "CRITICAL\|HIGH"
# Example: "Requests 2.25.0 has CVE-2021-33503 (CRITICAL)"

# Check if update available
pip index versions requests
# Example: Latest is 2.31.0 (patched)

# Update
pip install requests==2.31.0
# Re-test
pytest tests/ -q
```

**For signature failure:**

```bash
# Check artifact integrity
sha256sum generated/master/compiled/governance-core.compiled.msgpack
# Compare with SBOM hash

# Check git history
git log --oneline --all | head -20

# Was artifact modified?
git status generated/

# Who has push access?
gh repo view --json pushPermissions
```

#### Phase 4: Recovery

**For CVE (standard path):**

```bash
# 1. Update dependency in pyproject.toml
[project]
dependencies = [
  "requests>=2.31.0",  # Was: >=2.25.0
]

# 2. Run tests
uv sync
pytest tests/unit tests/integration -q

# 3. Rebuild
python -m build packages/core/providence_core

# 4. Update version
# (depends on semver: patch for CVE fix)
# pyproject.toml: version = "0.2.1" → "0.2.2"

# 5. Create release
git tag v0.2.2
git push origin v0.2.2
```

**For signature failure (escalation):**

```bash
# 1. Security team investigates
# 2. Audit CI/CD logs and access
# 3. Rotate CI secrets if compromised
# 4. Reset and rebuild artifact
# 5. Re-sign with new credentials
```

#### Phase 5: Postmortem (24h)

- [ ] Document what happened and timeline
- [ ] File issues: "Update dependency X", "Add CVE detection", etc.
- [ ] Update dependency strategy:
  - Monthly pip-audit checks?
  - Dependabot auto-merge for patch updates?
  - CI gate: fail if CVE detected?
- [ ] Share in team/public (transparency builds trust)

### Prevention

- ✅ pip-audit in CI (Phase 5.1): Detects CVEs before release
- ✅ Sigstore attestation (Phase 5.1): Verifies artifact signature
- ✅ SBOM generation (Phase 5.1): Documents all dependencies
- ⏳ Auto-dependency updates: Merge patch/minor updates daily
- ⏳ Supply chain policy: Require signed tags, branch protection

---

## Context Load Failure

### Symptoms

- `providence ask` times out or returns timeout error
- ContextLoader.load_result() raises exception
- Manifest parsing fails
- Artifact file missing or unreadable

### Root Causes

- Artifact file corrupted or incomplete
- Manifest metadata mismatched with artifact
- Insufficient file permissions
- Disk space exhausted
- Large artifact takes too long to load

### Response Steps

#### Phase 1: Detect

```bash
providence ask "test" 2>&1
# Error: "context load failed: [Errno 13] Permission denied"
```

#### Phase 2: Investigate

```bash
# Check artifact exists
ls -lh generated/master/compiled/governance-core.compiled.msgpack

# Check permissions
stat generated/master/compiled/governance-core.compiled.msgpack
# Should have read permission for current user

# Check manifest
cat generated/master/compiled/metadata-core.json | jq .

# Check disk space
df -h generated/
```

#### Phase 3: Fix

**Permission issue:**

```bash
chmod 644 generated/master/compiled/*
```

**Missing artifact:**

```bash
python -m sdd_compiler  # Rebuild
```

**Disk space:**

```bash
rm -rf generated/master/compiled/*.backup
python -m sdd_compiler  # Rebuild
```

---

## Telemetry Pipeline Blocked

### Symptoms

- Telemetry events not persisting
- JSONL log file not updated or missing
- `providence metrics summary` returns empty results
- Telemetry file permission errors in logs

### Root Causes

- Telemetry file permissions issue
- Disk full
- File descriptor exhausted
- Telemetry service crash

### Response Steps

#### Phase 1: Detect

```bash
# Check governance state and timestamp
providence runtime status

# Check if metrics reflect recent activity
providence metrics summary
# If output is empty or stale: pipeline may be blocked
```

#### Phase 2: Investigate

```bash
# Check telemetry file (compliance events log)
stat .providence/runtime/compliance-events.jsonl 2>/dev/null || echo "Telemetry file not found"

# Check permissions
ls -l .providence/runtime/ 2>/dev/null || echo "Runtime directory not found"

# Inspect recent events
tail -5 .providence/runtime/compliance-events.jsonl | jq . 2>/dev/null || echo "Cannot read events"

# Emit a test event and verify it was written
providence ask "test" 2>/dev/null
tail -1 .providence/runtime/compliance-events.jsonl | jq '.event'
```

#### Phase 3: Fix

**Option A: Check for disk space**

```bash
df -h .providence/
# If full: free space and retry
```

**Option B: Verify sink is running**

```bash
# Telemetry sink should emit events automatically via sdd commands
providence ask "test"  # This should emit an event

# Check if event was written
tail -1 .providence/runtime/compliance-events.jsonl | jq .
```

**Option C: Reset telemetry (last resort)**

```bash
# Backup current log
mv .providence/runtime/compliance-events.jsonl .providence/runtime/compliance-events.jsonl.backup

# Bootstrap fresh runtime state
providence bootstrap
```

---

## How to Use This Guide

1. **Identify the incident:** Match symptoms to a playbook
2. **Follow phases in order:** Detect → Contain → Investigate → Recover → Learn
3. **Escalate if needed:** Contact on-call or team lead
4. **Document everything:** Add to postmortem after resolution
5. **Update playbook:** Share learning for future incidents

---

## Adding New Playbooks

When a new incident occurs:

1. Document what happened (timeline, root cause, resolution)
2. Create a new playbook section with symptoms/root causes/steps
3. PR review: team discusses to validate steps
4. Merge: add to main branch
5. Next incident: use playbook instead of improvising

**Playbook Template:**

```markdown
## [Incident Name]

### Symptoms
- ...

### Root Causes
- ...

### Response Steps

#### Phase 1: Detect
...

#### Phase 2: Contain
...

#### Phase 3: Investigate
...

#### Phase 4: Recovery
...

#### Phase 5: Postmortem
...

### Prevention
...
```
