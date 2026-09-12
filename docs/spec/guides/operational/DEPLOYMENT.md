# 🚀 SDD v3.0 Deployment Guide

**Production deployment procedures and pre/post-deployment checklists**

**Version:** 3.0 | **Date:** April 22, 2026 | **Status:** Production Ready

---

## 📋 Quick Checklist

**Pre-Deployment:** 15 min | **Deployment:** 5-15 min | **Validation:** 10-20 min | **Total:** 30-50 min

```
[ ] Pre-Deployment Checklist
[ ] Backup Current Environment
[ ] Deploy Artifacts
[ ] Deploy CLI Binary
[ ] Validate Deployment
[ ] Post-Deployment Verification
[ ] Document Changes
```

---

## ✅ Pre-Deployment Checklist

### 1. Environmental Verification (5 min)

```bash
# Check current environment
echo "=== Environment Check ==="
uname -a  # OS
python --version  # Python 3.11+ required
df -h /  # Disk space (need 100MB minimum)
free -h  # Memory (need 256MB available)

# Verify git status (should be clean)
git status
# Expected: "On branch main, nothing to commit, working tree clean"

# Check critical paths
ls -d .providence-core
ls -d .providence-wizard
ls -d .providence-compiler
ls -d .providence-integration

echo "✅ Environment ready"
```

**Requirements:**

- ✅ OS: Linux, macOS, or Windows
- ✅ Python: 3.11+ (if installing from source)
- ✅ Disk: 100MB available
- ✅ Memory: 256MB available
- ✅ Network: For package installation (if needed)

### 2. Governance Validation (5 min)

```bash
# Validate current governance
providence governance validate

# Expected output:
# ✅ Core governance valid
# ✅ Client governance valid
# ✅ Fingerprints verified
# ✅ SALT strategy confirmed

# If any checks fail: DO NOT DEPLOY
# Contact framework maintainers before proceeding
```

### 3. Test Artifacts (5 min)

```bash
# Run full test suite
cd .providence-wizard
python -m pytest tests/ -v

# Expected: 124/124 tests passing
# Example:
# test_generate_specializations.py::test_basic_generation PASSED
# test_setup_wizard.py::test_wizard_phases_1_7 PASSED
# ...
# ======================== 124 passed in 3.24s ========================

# If any tests fail: DO NOT DEPLOY
# Fix failing tests before continuing
```

### 4. Backup Current Environment (5 min)

```bash
# Create timestamped backup
BACKUP_DIR="/backups/sdd-deployment-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup current deployment
cp -r .providence-core "$BACKUP_DIR/"
cp -r .providence-wizard/compiled "$BACKUP_DIR/"
cp -r .providence-integration "$BACKUP_DIR/"
cp CHANGELOG.md "$BACKUP_DIR/"

# Store backup location
echo "Deployment backup: $BACKUP_DIR" >> deployment_log.txt

# Verify backup integrity
du -sh "$BACKUP_DIR"
find "$BACKUP_DIR" -type f | wc -l
echo "✅ Backup created: $BACKUP_DIR"
```

---

## 🚀 Deployment Steps

### Phase 1: Core Artifacts (2 min)

```bash
# Verify source files
echo "=== Source Files Check ==="
ls -lh .providence-core/CANONICAL/
# Expected files:
# - mandate.spec (governance core rules)
# - guidelines.dsl (governance client rules)
# - metadata.json (framework metadata)

# Verify structure
file .providence-core/CANONICAL/mandate.spec
file .providence-core/CANONICAL/guidelines.dsl

echo "✅ Source files verified"
```

### Phase 2: Compile Artifacts (3 min)

```bash
# Fresh compilation from source
cd .providence-wizard
python compile_artifacts.py

# Expected output:
# Parsing mandate.spec...
# Compiling to msgpack...
# [CORE] 4 items serialized
# [CLIENT] 151 items serialized
# ✅ Compilation complete

# Verify compiled artifacts
echo "=== Compiled Artifacts ==="
ls -lh compiled/
du -sh compiled/

# Expected:
# governance-core.compiled.msgpack (2.3 KB)
# governance-client-template.compiled.msgpack (34 KB)
# metadata-core.json
# metadata-client-template.json
# DEPLOYMENT_MANIFEST.json

echo "✅ Artifacts compiled"
```

### Phase 3: Deploy CLI Binary (2 min)

**Option A: Use Pre-built Binary (Recommended)**

```bash
# Binary already included in dist/
# Make executable
chmod +x ./dist/providence

# Verify binary works
./dist/providence version
# Expected: "SDD Framework v3.0"

# Optionally add to PATH
sudo ln -sf $(pwd)/dist/providence /usr/local/bin/providence

# Verify system-wide availability
which sdd
providence version

echo "✅ CLI binary deployed"
```

**Option B: Install from Source**

```bash
# Install Python dependencies
pip install -r requirements-cli.txt

# Verify installation
python -m cli --help

# Create alias (optional)
alias sdd="python -m cli"

# Verify alias works
providence version

echo "✅ CLI installed from source"
```

### Phase 4: Validate Deployment (5 min)

```bash
# Test compilation
echo "=== Compilation Test ==="
cd .providence-wizard
python -c "from compile_artifacts import compile_artifacts; compile_artifacts()"
echo "✅ Compilation test passed"

# Test governance loading
echo "=== Governance Load Test ==="
providence governance load
# Expected: Shows core + client items

# Test artifact validation
echo "=== Validation Test ==="
providence governance validate
# Expected: All 8 checks pass

# Test wizard phases
echo "=== Wizard Phases Test ==="
python src/wizard.py --test-phases 1-7 --verbose
# Expected: All 7 phases pass

echo "✅ All deployment validations passed"
```

---

## ✔️ Post-Deployment Verification

### 1. Immediate Checks (5 min)

```bash
# Verify CLI is accessible
which sdd
providence version

# Quick governance check
providence governance validate | grep -E "(✅|✗)"

# Check no errors in system logs
journalctl -n 20 | grep -i error || echo "No errors found"

echo "✅ Immediate checks passed"
```

### 2. Functional Tests (10 min)

```bash
# Test new project creation
mkdir -p /tmp/sdd-test-project
cd /tmp/sdd-test-project

# Run wizard
sdd new --project-name "test-deployment" --language python

# Verify project structure
if [ -d ".providence/CANONICAL" ] && [ -d "src" ]; then
    echo "✅ Project creation successful"
else
    echo "❌ Project creation failed"
    exit 1
fi

# Cleanup test project
cd -
rm -rf /tmp/sdd-test-project
```

### 3. Performance Baseline (5 min)

```bash
# Establish baseline metrics
echo "=== Performance Baseline ==="

# Load time
time providence governance load > /dev/null
# Expected: <200ms

# Validate time
time providence governance validate > /dev/null
# Expected: <300ms

# Generate time
time providence governance generate > /dev/null
# Expected: <500ms

echo "✅ Performance baseline established"
```

### 4. Documentation Update (5 min)

```bash
# Record deployment details
cat >> deployment_log.txt << EOF

## Deployment: $(date)
- Version: $(providence version)
- Environment: $(uname -a)
- Backup location: $BACKUP_DIR
- CLI location: $(which sdd)
- Status: ✅ Successful

EOF

# Commit deployment record
git add deployment_log.txt
git commit -m "deploy: Production deployment v3.0 on $(date +%Y-%m-%d)"
git push

echo "✅ Documentation updated"
```

---

## 🔄 Rollback Procedures

### If Deployment Fails During Validation

**Immediate Steps:**

```bash
# Stop any active operations
# (Usually none - deployment is atomic)

# Check what failed
providence governance validate

# Investigate error
cat .providence-wizard/compile_artifacts.log

# If corruption detected:
echo "❌ Deployment validation failed"
echo "Rolling back to backup..."
```

### Rollback to Previous Version

```bash
# Restore from backup
BACKUP_DIR="/backups/sdd-deployment-YYYYMMDD-HHMMSS"
# (Use actual backup directory)

# Step 1: Stop any active operations
pkill -f "sdd\|wizard"

# Step 2: Remove corrupted artifacts
rm -rf .providence-core/CANONICAL/*
rm -rf .providence-wizard/compiled/*

# Step 3: Restore from backup
cp -r "$BACKUP_DIR"/.providence-core/CANONICAL .providence-core/
cp -r "$BACKUP_DIR"/.providence-wizard/compiled .providence-wizard/

# Step 4: Validate restoration
providence governance validate

# Step 5: Verify it works
providence governance load

echo "✅ Rollback complete"

# Step 6: Investigate what went wrong
git diff .providence-core/
```

### If Rollback Needed Post-Deployment

```bash
# Full system restoration
BACKUP_DIR="/backups/sdd-deployment-YYYYMMDD-HHMMSS"

# Backup current state (for investigation)
mv .providence-core .providence-core.failed.$(date +%s)
mv .providence-wizard .providence-wizard.failed.$(date +%s)

# Restore everything
cp -r "$BACKUP_DIR"/.providence-core .
cp -r "$BACKUP_DIR"/.providence-wizard .

# Verify
providence governance validate

# Alert team
echo "🚨 ROLLBACK COMPLETED - Investigate .providence-core.failed and .providence-wizard.failed"
```

---

## 📊 Deployment Status Tracking

### Deployment Log Template

```bash
# Use this template for each deployment
cat > DEPLOYMENT_RECORD_$(date +%Y%m%d_%H%M%S).md << 'EOF'
# Deployment Record

**Date:** $(date)
**Version:** 3.0
**Environment:** Production
**Operator:** $USER

## Pre-Deployment
- [ ] Environment verified
- [ ] Tests passing (124/124)
- [ ] Backup created: $BACKUP_DIR
- [ ] Governance validated

## Deployment
- [ ] Artifacts compiled
- [ ] CLI deployed
- [ ] Permissions verified

## Post-Deployment
- [ ] CLI functional
- [ ] Governance loads
- [ ] Validation passes
- [ ] Performance baseline recorded

## Results
- Duration: _ minutes
- Issues: None / List issues
- Status: ✅ Success / ❌ Failure
- Rollback needed: Yes / No

## Sign-off
- Deployed by: $USER
- Approved by: [Name]
- Date: $(date)

EOF
```

---

## 🎯 Multi-Environment Deployment

### Development Environment

```bash
# Dev environment typically doesn't need pre-deployment checks
cd /path/to/dev-workspace

# Fresh setup
python .providence-wizard/compile_artifacts.py
providence governance validate

# Note: No backup needed in dev
```

### Staging Environment

```bash
# Staging = test production
cd /path/to/staging-workspace

# Run full pre-deployment checklist
providence governance validate
pytest tests/ -v

# Create backup
BACKUP_DIR="/backups/staging-$(date +%Y%m%d-%H%M%S)"
cp -r .providence-* "$BACKUP_DIR/"

# Deploy
python .providence-wizard/compile_artifacts.py
providence governance validate

# Document
git tag -a "staging-$(date +%Y%m%d)" -m "Staging deployment"
```

### Production Environment

```bash
# Production = use full checklist above
cd /path/to/prod-workspace

# Full pre-deployment (15 min)
# 1. Environment check
# 2. Governance validation
# 3. Test artifacts
# 4. Backup environment

# Full deployment (5 min)
# 1. Compile artifacts
# 2. Deploy CLI
# 3. Validate

# Full post-deployment (10 min)
# 1. Immediate checks
# 2. Functional tests
# 3. Performance baseline
# 4. Document changes

# Commit production tag
git tag -a "prod-$(date +%Y%m%d)" -m "Production deployment"
git push --tags
```

---

## 📞 Troubleshooting Deployments

### ❌ Compilation Fails

```bash
# Check source files
ls -lh .providence-core/CANONICAL/

# Verify file format
file .providence-core/CANONICAL/mandate.spec
file .providence-core/CANONICAL/guidelines.dsl

# Check for syntax errors
python -m py_compile .providence-wizard/compile_artifacts.py

# Run with verbose output
cd .providence-wizard
python compile_artifacts.py --verbose

# If still failing: Rollback to previous backup
```

### ❌ CLI Installation Fails

```bash
# Check Python version
python --version  # Must be 3.11+

# Check dependencies
pip list | grep -E "typer|msgpack|click"

# Reinstall dependencies
pip install --force-reinstall -r requirements-cli.txt

# Test CLI
python -m cli --help
```

### ❌ Validation Fails After Deployment

```bash
# Run detailed validation
providence governance validate --verbose

# Check fingerprints
cat .providence-wizard/compiled/metadata-core.json | grep fingerprint
cat .providence-wizard/compiled/metadata-client-template.json | grep fingerprint

# Compare with expected
cat CHANGELOG.md | grep -i "fingerprint\|35efc54"

# If mismatch: Recompile from backup
```

---

## 📚 Related Documentation

**See also:**

- [OPERATIONS.md](./OPERATIONS.md) — Daily operational procedures
- [MONITORING.md](./MONITORING.md) — Deployment monitoring
- [MAINTENANCE.md](./MAINTENANCE.md) — Ongoing maintenance
- [architecture.md](../../canonical/specifications/architecture.md) — Architecture overview

---

## ✅ Final Deployment Checklist

Before declaring deployment complete:

```
Pre-Deployment (30 min before)
[ ] All tests passing (124/124)
[ ] Governance validated
[ ] Backup created and verified
[ ] Team notified of maintenance window

Deployment (During window)
[ ] Artifacts compiled
[ ] CLI deployed
[ ] Immediate validation passed
[ ] Performance baseline recorded

Post-Deployment (30 min after)
[ ] Monitoring shows normal operation
[ ] No error spikes in logs
[ ] Sample projects deployable
[ ] Team confirms access
[ ] Changes documented and tagged

Deployment Successful ✅
Status: Ready for production use
Next review: [Date + 1 week]
```
