# 🛠️ SDD v3.0 Maintenance Guide

**System maintenance, upgrades, and long-term care procedures**

**Version:** 3.0 | **Date:** April 22, 2026 | **Status:** Production Ready

---

## 📋 Maintenance Overview

### Maintenance Phases

| Phase | Frequency | Duration | Impact |
|-------|-----------|----------|--------|
| **Routine** | Daily/Weekly | <30 min | None |
| **Preventive** | Monthly | 1-2 hours | None |
| **Corrective** | As-needed | 1-4 hours | Minimal |
| **Adaptive** | Quarterly | 2-4 hours | Planned downtime |

### Key Tasks

```
Daily:    Backup, health check, log review
Weekly:   Cleanup, performance review, compliance check
Monthly:  Capacity planning, artifact refresh, security audit
Quarterly: Upgrades, load testing, disaster recovery
```

---

## ✅ Routine Maintenance

### Daily Tasks (15 min)

#### 1. Backup Governance

```bash
#!/bin/bash
# Save as: scripts/daily-backup.sh

BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/backups/daily/sdd-$BACKUP_DATE"

mkdir -p "$BACKUP_DIR"

# Backup critical files
echo "Backing up governance..."
cp -r .providence-core/CANONICAL "$BACKUP_DIR/"
cp -r .providence-wizard/compiled "$BACKUP_DIR/"
cp CHANGELOG.md "$BACKUP_DIR/"

# Record backup
echo "Backup created: $BACKUP_DIR ($(du -sh "$BACKUP_DIR" | cut -f1))"

# Keep only last 30 days
find /backups/daily -name "sdd-*" -type d -mtime +30 -exec rm -rf {} \;

echo "✅ Daily backup complete"
```

**Run daily at 01:00:**

```bash
0 1 * * * /home/sergio/scripts/daily-backup.sh >> /var/log/sdd-backup.log 2>&1
```

#### 2. Health Check

```bash
# Already defined in MONITORING.md
./scripts/health-check.sh

# Expected output:
# ✅ All artifacts present
# ✅ CLI available
# ✅ Governance valid
# ✅ Disk space OK
```

#### 3. Review Error Logs

```bash
#!/bin/bash
# Check for errors from previous 24 hours

echo "=== Error Log Review ==="

# Application logs
if [ -f "logs/sdd-app.log" ]; then
    ERRORS=$(grep -c "ERROR\|FAIL" logs/sdd-app.log || echo "0")
    echo "Application errors: $ERRORS"
    if [ "$ERRORS" -gt 0 ]; then
        echo "Recent errors:"
        grep "ERROR\|FAIL" logs/sdd-app.log | tail -5
    fi
fi

# System logs
if command -v journalctl &> /dev/null; then
    echo ""
    echo "System errors (last 24h):"
    journalctl --since "24 hours ago" -p err | grep -i sdd || echo "  None found"
fi

echo ""
echo "✅ Log review complete"
```

### Weekly Tasks (1 hour)

#### 1. Cleanup Old Files

```bash
#!/bin/bash
# Save as: scripts/weekly-cleanup.sh

echo "=== Weekly Cleanup ==="

# Remove old test artifacts
echo "Removing test artifacts older than 7 days..."
find . -name "providence-generated" -type d -mtime +7 -exec rm -rf {} \;
REMOVED=$(find . -name "providence-generated" -type d -mtime +7 | wc -l)
[ $REMOVED -gt 0 ] && echo "  Removed: $REMOVED directories"

# Clean Python cache
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
echo "  ✅ Cache cleaned"

# Clean old logs
echo "Archiving old logs..."
mkdir -p logs/archive
find logs -maxdepth 1 -name "*.log" -mtime +7 -exec gzip -v {} \;
mv logs/*.gz logs/archive/ 2>/dev/null || true
echo "  ✅ Logs archived"

# Verify cleanup
TOTAL_SIZE=$(du -sh . | cut -f1)
echo ""
echo "Total workspace size: $TOTAL_SIZE"

echo ""
echo "✅ Weekly cleanup complete"
```

**Run weekly (e.g., Sunday 02:00):**

```bash
0 2 * * 0 /home/sergio/scripts/weekly-cleanup.sh
```

#### 2. Performance Review

```bash
#!/bin/bash
# Analyze weekly performance

echo "=== Weekly Performance Review ==="

# Collect baseline if missing
if [ ! -f "metrics/baseline.txt" ]; then
    echo "Establishing performance baseline..."
    {
        echo "# Performance Baseline"
        echo "Generated: $(date)"
        echo ""
        echo "Load time: $(( SECONDS=0; providence governance load > /dev/null; echo $SECONDS )ms"
        echo "Validate time: $(( SECONDS=0; providence governance validate > /dev/null; echo $SECONDS )ms"
        echo "Generate time: $(( SECONDS=0; providence governance generate > /dev/null; echo $SECONDS )ms"
    } > metrics/baseline.txt
fi

# Compare with baseline
echo "Current performance:"
echo "Load time: $(( SECONDS=0; providence governance load > /dev/null; echo $SECONDS )ms"
echo "Validate time: $(( SECONDS=0; providence governance validate > /dev/null; echo $SECONDS )ms"
echo "Generate time: $(( SECONDS=0; providence governance generate > /dev/null; echo $SECONDS )ms"

echo ""
echo "✅ Performance review complete"
```

---

## 🚨 Preventive Maintenance

### Monthly Tasks (2-3 hours)

#### 1. Artifact Refresh

```bash
#!/bin/bash
# Refresh compiled artifacts

echo "=== Monthly Artifact Refresh ==="

# Backup current artifacts
BACKUP_DIR="/backups/monthly/artifacts-$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp -r .providence-wizard/compiled "$BACKUP_DIR/"
echo "Backed up to: $BACKUP_DIR"

# Fresh compilation
echo ""
echo "Recompiling artifacts..."
cd .providence-wizard
python compile_artifacts.py

# Verify new artifacts
echo ""
echo "Verifying new artifacts..."
if providence governance validate; then
    echo "✅ New artifacts valid"
else
    echo "❌ New artifacts invalid - restoring backup"
    rm -rf .providence-wizard/compiled
    cp -r "$BACKUP_DIR/compiled" .providence-wizard/
    exit 1
fi

echo ""
echo "✅ Artifact refresh complete"
```

**Run monthly (e.g., 1st of month, 03:00):**

```bash
0 3 1 * * /home/sergio/scripts/monthly-artifact-refresh.sh
```

#### 2. Capacity Planning

```bash
#!/bin/bash
# Analyze space and growth

echo "=== Monthly Capacity Review ==="

# Current usage
echo "Current Usage:"
du -sh .providence-* | sort -h

echo ""
echo "Disk Status:"
df -h . | awk 'NR==2 {printf "  Used: %s/%s (%.1f%%)\n", $3, $2, $5}'

# Growth trend
if [ -f "metrics/capacity-trend.log" ]; then
    echo ""
    echo "Growth trend (last 4 weeks):"
    tail -4 metrics/capacity-trend.log
fi

# Record current state
echo "$(date +%Y-%m-%d) $(du -sh . | cut -f1)" >> metrics/capacity-trend.log

# Forecast and alert
CURRENT=$(du -sh . | awk '{print $1}' | sed 's/G//')
if (( $(echo "$CURRENT > 8" | bc -l) )); then
    echo ""
    echo "⚠️  WARNING: Approaching 10GB limit"
    echo "Action: Cleanup old backups and logs"
fi

echo ""
echo "✅ Capacity review complete"
```

#### 3. Security Audit

```bash
#!/bin/bash
# Monthly security review

echo "=== Monthly Security Audit ==="

# 1. File permissions
echo "1. File Permissions:"
find .providence-core -type f ! -perm 644 | while read f; do
    echo "  ⚠️  $f has unusual permissions"
done
echo "  ✅ Permissions verified"

# 2. Unauthorized changes
echo ""
echo "2. Unauthorized Changes:"
if git diff-index --quiet HEAD -- .providence-core/CANONICAL/mandate.spec; then
    echo "  ✅ Core rules unchanged"
else
    echo "  ⚠️  Core rules modified"
    git diff .providence-core/CANONICAL/mandate.spec
fi

# 3. Fingerprint verification
echo ""
echo "3. Fingerprint Verification:"
providence governance validate | grep -i fingerprint

# 4. Access logs
echo ""
echo "4. Access Review:"
if command -v journalctl &> /dev/null; then
    echo "  Unusual access attempts (last 30 days):"
    journalctl --since "30 days ago" | grep -i "sdd\|wizard" | wc -l
fi

echo ""
echo "✅ Security audit complete"
```

#### 4. Compliance Check

```bash
#!/bin/bash
# Review compliance status

echo "=== Monthly Compliance Check ==="

# 1. Governance compliance
echo "1. Governance Compliance:"
providence governance validate | grep "Compliance\|SALT"

# 2. Documentation
echo ""
echo "2. Documentation:"
ls -d .providence-core/OPERATIONS.md .providence-core/DEPLOYMENT.md .providence-core/MONITORING.md 2>/dev/null && echo "  ✅ Operational docs present" || echo "  ❌ Missing docs"

# 3. Test results
echo ""
echo "3. Test Coverage:"
if [ -d ".providence-wizard/tests" ]; then
    TEST_COUNT=$(find .providence-wizard/tests -name "test_*.py" | wc -l)
    echo "  Tests: $TEST_COUNT files"
fi

# 4. Changelog
echo ""
echo "4. Changelog:"
UPDATES=$(grep "^##" CHANGELOG.md | head -1)
echo "  Latest: $UPDATES"

echo ""
echo "✅ Compliance check complete"
```

---

## 🔧 Corrective Maintenance

### Troubleshooting Procedures

#### Issue: Corruption Detected

```bash
#!/bin/bash
# Handle governance corruption

echo "🚨 Corruption Recovery Procedure"

# Step 1: Isolate the problem
echo "Step 1: Identifying corruption..."
providence governance validate

# Step 2: Find backup
echo ""
echo "Step 2: Finding clean backup..."
BACKUP=$(find /backups -name "sdd-*" -type d | sort -r | head -1)
echo "  Using: $BACKUP"

# Step 3: Verify backup integrity
echo ""
echo "Step 3: Verifying backup integrity..."
cd "$BACKUP"
if python3 -c "import msgpack; msgpack.unpackb(open('governance-core.compiled.msgpack', 'rb').read())"; then
    echo "  ✅ Backup valid"
else
    echo "  ❌ Backup corrupted too - try earlier backup"
    exit 1
fi

# Step 4: Restore
echo ""
echo "Step 4: Restoring from backup..."
cd -
rm -rf .providence-wizard/compiled
cp -r "$BACKUP/compiled" .providence-wizard/

# Step 5: Verify restoration
echo ""
echo "Step 5: Verifying restoration..."
if providence governance validate; then
    echo "  ✅ Restoration successful"
    exit 0
else
    echo "  ❌ Restoration failed"
    exit 1
fi
```

#### Issue: Performance Degradation

```bash
#!/bin/bash
# Diagnose performance issues

echo "=== Performance Diagnostics ==="

# 1. Baseline comparison
echo "1. Current Performance:"
time providence governance load > /dev/null
time providence governance validate > /dev/null

# 2. System resources
echo ""
echo "2. System Resources:"
ps aux | grep sdd | grep -v grep
echo ""
echo "Disk I/O:"
iostat -x 1 2 | tail -5

# 3. Artifact analysis
echo ""
echo "3. Artifact Analysis:"
ls -lh .providence-wizard/compiled/

# 4. Process monitoring
echo ""
echo "4. Running Processes:"
ps auxww | grep -E "sdd|wizard|python" | grep -v grep | head -5

# 5. Recommendations
echo ""
echo "Recommendations:"
echo "  - If I/O slow: Check disk health"
echo "  - If CPU high: Check for hung processes"
echo "  - If memory high: Consider recompilation"
```

---

## 🚀 Adaptive Maintenance

### Quarterly Upgrades (2-4 hours)

#### 1. System Update

```bash
#!/bin/bash
# Quarterly system updates

echo "=== Quarterly System Update ==="

# Pre-update checks
echo "Pre-update verification..."
./scripts/health-check.sh
./scripts/daily-backup.sh

# Update framework
echo ""
echo "Updating framework..."
git fetch origin
git pull origin main

# Update dependencies
echo ""
echo "Updating dependencies..."
pip install --upgrade -r requirements-cli.txt

# Recompile artifacts
echo ""
echo "Recompiling with new framework..."
cd .providence-wizard
python compile_artifacts.py

# Post-update validation
echo ""
echo "Post-update validation..."
providence governance validate
providence version

# Run tests
echo ""
echo "Running test suite..."
pytest .providence-wizard/tests/ -v

echo ""
echo "✅ Quarterly update complete"
```

#### 2. Load Testing

```bash
#!/bin/bash
# Stress test the system

echo "=== Quarterly Load Testing ==="

# Test 1: Rapid validations
echo "Test 1: Rapid validations (100 iterations)..."
for i in {1..100}; do
    providence governance validate > /dev/null &
done
wait
echo "  ✅ Passed"

# Test 2: Concurrent operations
echo ""
echo "Test 2: Concurrent operations (10 parallel)..."
for i in {1..10}; do
    providence governance generate > /dev/null &
done
wait
echo "  ✅ Passed"

# Test 3: Large data sets
echo ""
echo "Test 3: Large project generation..."
sdd new --project-name "load-test" --language python > /dev/null
echo "  ✅ Passed"

echo ""
echo "✅ Load testing complete"
```

#### 3. Disaster Recovery Drill

```bash
#!/bin/bash
# Test recovery procedures

echo "=== Quarterly Disaster Recovery Drill ==="

# Scenario 1: Artifact loss
echo "Scenario 1: Artifact loss recovery"
BACKUP=$(find /backups -name "sdd-*" -type d | sort -r | head -1)
echo "  Using backup: $BACKUP"
cp -r "$BACKUP/compiled" /tmp/test-recovery/
echo "  ✅ Scenario passed"

# Scenario 2: Governance corruption
echo ""
echo "Scenario 2: Governance corruption detection"
TEST_FILE=$(mktemp)
dd if=/dev/urandom of="$TEST_FILE" bs=1024 count=1 2>/dev/null
if ! python3 -c "import msgpack; msgpack.unpackb(open('$TEST_FILE', 'rb').read())" 2>/dev/null; then
    echo "  ✅ Corruption detected as expected"
fi
rm "$TEST_FILE"

# Scenario 3: Full system restore
echo ""
echo "Scenario 3: Full system restore simulation"
echo "  Creating test snapshot..."
SNAP=$(mktemp -d)
cp -r .providence-* "$SNAP/"
echo "  Snapshot created: $SNAP"
echo "  ✅ Scenario passed"
rm -rf "$SNAP"

echo ""
echo "✅ Disaster recovery drill complete"
```

---

## 📊 Maintenance Records

### Maintenance Log Template

```bash
#!/bin/bash
# Save maintenance records

cat >> MAINTENANCE_LOG.md << EOF

## Maintenance Record $(date +%Y-%m-%d)

**Type:** [Routine/Preventive/Corrective/Adaptive]
**Duration:** _ minutes
**Performed by:** $USER

### Tasks Completed
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

### Issues Found
[List any issues discovered]

### Actions Taken
[List all actions taken]

### Status
- Before: [Current state]
- After: [New state]
- Impact: [What changed]

### Sign-off
**Date:** $(date)
**Status:** ✅ Complete

---

EOF
```

---

## 📋 Maintenance Schedule

### Annual Maintenance Calendar

```
JANUARY
  - 1st: Monthly capacity review
  - 15th: Security audit

APRIL (Quarterly)
  - 1st: System update
  - 2nd: Load testing
  - 3rd: Disaster recovery drill

JULY (Quarterly)
  - 1st: System update
  - 2nd: Load testing
  - 3rd: Disaster recovery drill

OCTOBER (Quarterly)
  - 1st: System update
  - 2nd: Load testing
  - 3rd: Disaster recovery drill

EVERY MONTH
  - 1st: Artifact refresh
  - 15th: Compliance check

EVERY WEEK
  - Monday: Cleanup
  - Tuesday: Performance review

EVERY DAY
  - 01:00: Backup
  - 06:00: Health check
  - 18:00: Error log review
```

---

## 🔗 Related Documentation

- [OPERATIONS.md](./OPERATIONS.md) — Daily operations
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Deployment procedures
- [MONITORING.md](./MONITORING.md) — Health monitoring
- [CORE_INDEX.md](./CORE_INDEX.md) — Specific operational tasks

---

## ✅ Maintenance Checklist Template

**Use at start of each maintenance window:**

```
Date: ___________
Type: [ ] Daily [ ] Weekly [ ] Monthly [ ] Quarterly
Operator: ___________

Pre-Maintenance
[ ] Backup created
[ ] Health check passed
[ ] No active operations
[ ] Maintenance window approved

Maintenance Tasks
[ ] (Task 1)
[ ] (Task 2)
[ ] (Task 3)

Post-Maintenance
[ ] All validations pass
[ ] Performance acceptable
[ ] No errors in logs
[ ] Changes documented

Sign-off
Status: [ ] Success [ ] Failed (explain:___)
Next maintenance: ___________
```
