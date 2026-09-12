# 🚀 SDD v3.0 Operations Guide

**Production operational procedures and daily practices for SDD Framework**

**Version:** 3.0 | **Date:** April 22, 2026 | **Status:** Production Ready

---

## 📖 Quick Navigation

| Section | Purpose | Duration |
|---------|---------|----------|
| [Overview](#overview) | Understand operational model | 5 min |
| [Daily Operations](#daily-operations) | Common tasks | 5-15 min |
| [Monitoring](#monitoring) | Health checks | 5-10 min |
| [Troubleshooting](#troubleshooting) | Common issues | 10-30 min |
| [Performance](#performance) | Optimization | 15-30 min |
| [Maintenance](#maintenance) | Upkeep procedures | 30-60 min |

---

## 🎯 Overview

### Operational Model

**SDD Framework is a stateless governance system:**

- ✅ **No persistent state** — All configuration is file-based
- ✅ **Multi-environment** — Same artifacts work in dev/staging/prod
- ✅ **Atomic operations** — Each phase completes or fails cleanly
- ✅ **Immutable core** — Governance core cannot be modified at runtime
- ✅ **Audit-friendly** — All changes tracked via fingerprints

### Key Concepts

| Concept | Meaning | Impact |
|---------|---------|--------|
| **Core** | 4 immutable governance rules | Cannot be changed; provides foundation |
| **Client** | 151 customizable guidelines | Teams select which to implement |
| **SALT** | Fingerprint embedded in metadata | Prevents tampering; enables validation |
| **Wizard** | Single guided-flow orchestrator (`providence install --wizard`) | Creates new projects with governance |
| **CLI** | Governance management tool | Loads, validates, generates agent seeds |

### Architecture Layers

```
Application Layer (Agent-driven code)
         ↓
Governance Layer (Core + Client rules)
         ↓
Compilation Layer (msgpack artifacts)
         ↓
Storage Layer (.providence-wizard/compiled/)
```

### Final Template Handoff Layout

When Phase 4-6 consolidation is executed, the handoff bundle is organized under
`generated/client/build/final-template/` with runtime governance artifacts inside `.providence`:

```text
final-template/
├── .providence/
│   ├── compiled/
│   │   ├── governance-core.compiled.msgpack
│   │   ├── governance-client-template.compiled.msgpack
│   │   ├── metadata-core.json
│   │   └── metadata-client-template.json
│   ├── DEPLOYMENT_MANIFEST.json
│   ├── source/
│   └── runtime/
└── ... (project scaffold files)
```

Compatibility note: loaders also accept legacy top-level artifact placement in
`final-template/` during migration.

---

## 📅 Daily Operations

### 1️⃣ Morning Health Check (5 min)

**Goal:** Verify governance system is operational

```bash
# Check compiled artifacts exist
ls -lh .providence-wizard/compiled/

# Expected output:
# - governance-core.compiled.msgpack (2.3 KB)
# - governance-client-template.compiled.msgpack (34 KB)
# - metadata-core.json
# - metadata-client-template.json
# - DEPLOYMENT_MANIFEST.json

# Validate integrity
providence governance validate

# Expected: ✅ All fingerprints verified
```

**What to do if artifacts are missing:**

1. Recompile: `cd .providence-wizard && python compile_artifacts.py`
2. Verify: `ls .providence-wizard/compiled/`
3. If still missing: See [Troubleshooting](#troubleshooting)

### 2️⃣ Load Governance Configuration (2 min)

**Goal:** Display current governance rules

```bash
# Display governance configuration
providence governance load

# Output shows:
# - Core rules (4 items) [IMMUTABLE]
# - Client guidelines (151 items) [CUSTOMIZABLE]
# - SALT fingerprint validation status
```

**Expected output pattern:**

```
✅ Core Governance Loaded
   - M001: Specification-Driven Development
   - M002: AI-First Architecture
   - M003: CORE+CLIENT Separation
   - M004: Governance Integrity

✅ Client Guidelines Loaded (151 items)
   - G01-G50: Architecture & Design
   - G51-G100: Development Practices
   - G101-G150: Quality & Security

✅ SALT Strategy Verified
   - Core fingerprint embedded in client metadata
   - Tampering detection enabled
```

### 3️⃣ Initialize New Project (30 min)

**Goal:** Add new project with SDD governance

```bash
# Navigate to workspace
cd /path/to/new-project

# Run wizard
sdd new --project-name "my-project" --language python

# Wizard orchestrates 7 phases:
# Phase 1: Validate source governance
# Phase 2: Load compiled artifacts
# Phase 3: Filter mandates by selection
# Phase 4: Filter guidelines by language
# Phase 5: Apply template customization
# Phase 6: Generate project structure
# Phase 7: Validate output

# Expected result: Generated project structure with:
# - .providence/CANONICAL/ (governance files)
# - .providence-guidelines/ (customizable rules)
# - src/ (code scaffolding)
# - tests/ (test structure)
# - docs/ (documentation)
```

**What to verify:**

- ✅ All 7 phases completed successfully
- ✅ Project directory structure created
- ✅ Governance files in place
- ✅ Generated configuration valid

### 4️⃣ Generate Agent Seeds (5 min)

**Goal:** Create agent configuration for Cursor, Copilot, etc.

```bash
# Generate all agent seeds
providence governance generate

# Generates:
# - .cursor-instructions.md (Cursor IDE rules)
# - .copilot-instructions.md (GitHub Copilot rules)
# - .agent-generic.md (Generic AI agent rules)

# Or specify target
providence governance generate --agent cursor
providence governance generate --agent copilot
providence governance generate --agent generic
```

**Output:** Configuration files ready for your IDE/agent

---

## 👁️ Monitoring

### Health Indicators

| Indicator | Check | Healthy | Action |
|-----------|-------|---------|--------|
| **Artifacts** | File size changes | No change | Recompile if changed |
| **Fingerprints** | Match validation | All match | Investigate mismatch |
| **Performance** | Load time | <500ms | Check disk I/O |
| **Compliance** | Rule violations | 0 | Review violations |

### Validation Commands

```bash
# Full governance validation
providence governance validate

# Output: Validates 8 checks
# ✅ Core file structure
# ✅ Client file structure
# ✅ Fingerprint preservation
# ✅ SALT strategy
# ✅ Separation validation
# ✅ Item counts
# ✅ Metadata integrity
# ✅ Roundtrip serialization

# Check specific project compliance
cd /path/to/project
sdd project validate

# Output: Validates project has:
# ✅ Governance files in .providence/
# ✅ Guidelines in .providence-guidelines/
# ✅ Valid metadata
# ✅ Specification integrity
```

### Performance Metrics

```bash
# Check compiled artifact sizes
du -h .providence-wizard/compiled/

# Expected:
# - Core: 2.3 KB (4 rules)
# - Client: 34 KB (151 rules)
# - Total: ~37 KB

# Check load performance
time providence governance load

# Expected: <500ms total time
```

### Monitoring Checklist

**Daily (Morning):**

- [ ] Artifacts exist and match deployment manifest
- [ ] `providence governance validate` returns all checks passing
- [ ] CLI responds in <1 second

**Weekly (Monday morning):**

- [ ] Verify no fingerprint mismatches
- [ ] Check performance hasn't degraded
- [ ] Review any violation reports

**Monthly (First of month):**

- [ ] Audit all modifications to core rules
- [ ] Review governance compliance metrics
- [ ] Plan any needed updates

---

## 🔧 Troubleshooting

### Common Issues

#### ❌ Issue: "ModuleNotFoundError: No module named 'sdd'"

**Symptoms:**

```
$ sdd --help
ModuleNotFoundError: No module named 'sdd'
```

**Solution:**

```bash
# Option 1: Use pre-built binary
chmod +x ./dist/providence
./dist/providence --help

# Option 2: Install from source
pip install -r requirements-cli.txt
python -m cli --help

# Option 3: Add to Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/.providence-core
python -m cli --help
```

#### ❌ Issue: "Fingerprint mismatch detected"

**Symptoms:**

```
✗ Fingerprint validation failed
  Expected: 35efc54d3e353daaf633fad531562f1da97ec17814193b7ac44b2e9ef12daddd
  Got: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1
```

**Causes:**

- Governance files modified externally
- Artifact compilation failed
- Tampering detected (SALT strategy working)

**Solution:**

```bash
# Step 1: Check if source files were modified
git diff .providence-core/CANONICAL/

# Step 2: If modified intentionally, recompile
cd .providence-wizard
python compile_artifacts.py

# Step 3: Verify new fingerprints
providence governance validate

# Step 4: If unauthorized changes found, revert
git checkout .providence-core/CANONICAL/
cd .providence-wizard
python compile_artifacts.py
```

#### ❌ Issue: "Compiled artifacts missing"

**Symptoms:**

```
$ ls .providence-wizard/compiled/
# Returns empty or file not found
```

**Solution:**

```bash
# Step 1: Create compiled directory
mkdir -p .providence-wizard/compiled

# Step 2: Compile from source
cd .providence-wizard
python compile_artifacts.py

# Step 3: Verify output
ls -lh compiled/

# Step 4: Check DEPLOYMENT_MANIFEST
cat compiled/DEPLOYMENT_MANIFEST.json
```

#### ❌ Issue: "Wizard Phase X failed"

**Symptoms:**

```
❌ PHASE_5_APPLY_TEMPLATE failed
Error: Language not recognized: 'cpp'
```

**Diagnosis:**

```bash
# Run with verbose output
python .providence-wizard/src/wizard.py --test-phases 1-7 --verbose

# Check which phase actually failed
# Look for first ❌ mark

# Common phase failures:
# Phase 1: Source validation - Check .providence-core/ structure
# Phase 2: Compilation - Check artifact generation
# Phase 3: Mandate filtering - Check mandate.spec format
# Phase 4: Guideline filtering - Check language parameter
# Phase 5: Template application - Check template files exist
# Phase 6: Project generation - Check write permissions
# Phase 7: Output validation - Check generated structure
```

**Solution by phase:**

```bash
# Phase 1 failure: Validate source
python .providence-core/scripts/validate_source.py

# Phase 2 failure: Recompile
python .providence-wizard/compile_artifacts.py

# Phase 4 failure: Check language support
# Valid: python, java, javascript
# Use: --language python (or java/javascript)

# Phase 6 failure: Check permissions
ls -ld /path/to/generation/target
chmod 755 /path/to/generation/target

# Phase 7 failure: Check output structure
ls -R ./providence-generated/project/
```

### Troubleshooting Decision Tree

```
Problem reported
    ↓
Is CLI working?
    ├→ NO → Install/reinstall CLI (requirements, Python path)
    └→ YES → Continue
    ↓
Does `providence governance validate` pass?
    ├→ NO → Fingerprint mismatch (see above)
    └→ YES → Continue
    ↓
Is it a wizard issue?
    ├→ YES → Run with --verbose, check phase output
    └→ NO → Continue
    ↓
Is it a project issue?
    ├→ YES → Check project .providence/ structure
    └→ NO → See operational/troubleshooting/
```

---

## ⚡ Performance

### Optimization

#### 1. Artifact Caching

```bash
# Compiled artifacts are cached automatically
# Cache location: .providence-wizard/compiled/

# To verify cache is being used:
time providence governance load  # Should be <100ms

# If cache is not working:
# Check file timestamps
stat .providence-wizard/compiled/governance-core.compiled.msgpack

# Clear cache and regenerate if needed
rm -rf .providence-wizard/compiled/*
python .providence-wizard/compile_artifacts.py
```

#### 2. Parallel Processing

```bash
# Guideline filtering can process in parallel
# Max workers: number of CPU cores
# Environment variable:
export WORKERS=$(nproc)

# Then run wizard:
python .providence-wizard/src/wizard.py --language python
```

#### 3. Disk I/O Optimization

```bash
# Use SSD for .providence-wizard/compiled/
# Check I/O performance:
time dd if=/dev/zero of=test.bin bs=1M count=10
# Expected: <100ms for 10MB

# If slow, move compiled/ to faster disk:
mv .providence-wizard/compiled /fast-disk/sdd-compiled
ln -s /fast-disk/sdd-compiled .providence-wizard/compiled
```

### Performance Monitoring

```bash
# Benchmark governance operations
time providence governance load
time providence governance validate
time providence governance generate

# Expected times:
# - load: 50-150ms
# - validate: 100-300ms
# - generate: 200-500ms

# If significantly slower:
# 1. Check disk I/O: iostat -x 1
# 2. Check CPU: top
# 3. Check memory: free -h
# 4. Verify artifact sizes unchanged
```

### Capacity Planning

| Load | Metric | Healthy | Action |
|------|--------|---------|--------|
| **Light** | <100 projects | Load <100ms | No action |
| **Medium** | 100-1K projects | Load <500ms | Monitor I/O |
| **Heavy** | >1K projects | Load <1s | Consider caching layer |

---

## 🛠️ Maintenance

### Backup Procedures

```bash
# Daily backup of governance
BACKUP_DIR="/backups/sdd-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup critical components
cp -r .providence-core/CANONICAL "$BACKUP_DIR/"
cp -r .providence-wizard/compiled "$BACKUP_DIR/"
cp CHANGELOG.md "$BACKUP_DIR/"

# Verify backup
du -sh "$BACKUP_DIR"
echo "Backup: $BACKUP_DIR" >> backup_manifest.log
```

### Update Procedures

```bash
# Update governance rules (CLIENT items only)
# Core rules cannot be modified at runtime

# 1. Modify CLIENT guidelines
edit .providence-core/CANONICAL/guidelines.dsl

# 2. Recompile artifacts
cd .providence-wizard
python compile_artifacts.py

# 3. Validate new artifacts
providence governance validate

# 4. Deploy to projects
# (Projects load from updated artifacts on next initialization)

# 5. Verify compliance
sdd project validate
```

### Cleanup Procedures

```bash
# Remove old generated projects
find . -name "providence-generated" -type d -mtime +30 -exec rm -rf {} \;

# Clear compiled artifact cache (forces recompilation)
rm -rf .providence-wizard/compiled

# Remove test artifacts
find . -name ".pytest_cache" -type d -exec rm -rf {} \;
find . -name "__pycache__" -type d -exec rm -rf {} \;

# Verify cleanup
du -sh .providence-*
```

### Routine Maintenance Schedule

| Task | Frequency | Time | Priority |
|------|-----------|------|----------|
| **Morning check** | Daily | 5 min | High |
| **Artifact validation** | Daily | 5 min | High |
| **Backup** | Daily | 5 min | High |
| **Performance review** | Weekly | 10 min | Medium |
| **Log cleanup** | Weekly | 5 min | Low |
| **Compliance audit** | Monthly | 30 min | High |
| **Artifact refresh** | Quarterly | 15 min | Medium |

---

## 📚 Related Documentation

**See also:**

- [DEPLOYMENT.md](./DEPLOYMENT.md) — Production deployment checklist
- [MONITORING.md](./MONITORING.md) — Detailed monitoring procedures
- [MAINTENANCE.md](./MAINTENANCE.md) — Advanced maintenance tasks
- [OPERATIONS-INDEX.md](./OPERATIONS-INDEX.md) — Specific operational tasks
- [TROUBLESHOOTING_SPEC_VIOLATIONS.md](./TROUBLESHOOTING_SPEC_VIOLATIONS.md) — Extended troubleshooting

---

## 🆘 Support

**Need help?**

1. **Check troubleshooting:** [Troubleshooting](#troubleshooting)
2. **Search guides:** `.providence-core/spec/guides/`
3. **Review logs:** Check phase output with `--verbose` flag
4. **Escalate:** Contact SDD framework maintainers

**Provide when reporting issues:**

- Command run: `providence version` output
- Error message: Full stack trace if available
- Environment: OS, Python version
- Recent changes: What changed before issue occurred
