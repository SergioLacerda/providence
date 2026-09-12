# 👁️ SDD v3.0 Monitoring Guide

**Health monitoring, metrics collection, and alerting procedures**

**Version:** 3.0 | **Date:** April 22, 2026 | **Status:** Production Ready

---

## 📊 Monitoring Overview

### Health Model

**SDD Framework operates as a distributed system with these components:**

| Component | Type | Monitored | SLA |
|-----------|------|-----------|-----|
| **Core Governance** | Immutable | Yes | 100% available |
| **Client Guidelines** | Mutable | Yes | 100% available |
| **Compiled Artifacts** | Cache | Yes | <500ms load |
| **CLI Tool** | Application | Yes | <1s response |
| **Wizard Pipeline** | Process | Yes | <5min end-to-end |

### Key Metrics

| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| **Artifact Load Time** | Performance | <200ms | >500ms |
| **Validation Duration** | Performance | <300ms | >1s |
| **Fingerprint Match** | Integrity | 100% | Any mismatch |
| **Disk Space** | Capacity | 10GB+ | <1GB free |
| **Error Rate** | Reliability | 0% | >0.1% |

---

## 📈 Daily Monitoring

### 1. Morning Health Dashboard (5 min)

```bash
#!/bin/bash
# Save as: scripts/health-check.sh

echo "=== SDD Framework Health Check ==="
echo "Time: $(date)"
echo ""

# 1. Artifact availability
echo "📦 Artifacts:"
if [ -f ".providence-wizard/compiled/governance-core.compiled.msgpack" ]; then
    SIZE=$(du -h .providence-wizard/compiled/governance-core.compiled.msgpack | cut -f1)
    echo "  ✅ Core artifact: $SIZE"
else
    echo "  ❌ Core artifact: MISSING"
fi

if [ -f ".providence-wizard/compiled/governance-client-template.compiled.msgpack" ]; then
    SIZE=$(du -h .providence-wizard/compiled/governance-client-template.compiled.msgpack | cut -f1)
    echo "  ✅ Client artifact: $SIZE"
else
    echo "  ❌ Client artifact: MISSING"
fi

echo ""

# 2. CLI availability
echo "⚙️  CLI Status:"
if command -v sdd &> /dev/null; then
    VERSION=$(providence version 2>/dev/null || echo "ERROR")
    echo "  ✅ CLI available: $VERSION"
else
    echo "  ❌ CLI not found in PATH"
fi

echo ""

# 3. Governance validation
echo "🔐 Governance:"
VALIDATION=$(providence governance validate 2>&1)
if echo "$VALIDATION" | grep -q "✅"; then
    echo "  ✅ Validation passed"
else
    echo "  ❌ Validation failed"
    echo "  Details: $VALIDATION"
fi

echo ""

# 4. Disk space
echo "💾 Disk Space:"
USAGE=$(df -h . | awk 'NR==2 {print $5}')
FREE=$(df -h . | awk 'NR==2 {print $4}')
echo "  Usage: $USAGE"
echo "  Free: $FREE"

echo ""
echo "=== Health Check Complete ==="
```

**Run daily:**

```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

### 2. Metric Collection (Every 30 min)

```bash
#!/bin/bash
# Save as: scripts/collect-metrics.sh

METRICS_FILE="metrics/sdd-metrics-$(date +%Y%m%d).log"
mkdir -p metrics

# Timestamp
echo "=== Metrics: $(date +%Y-%m-%d\ %H:%M:%S) ===" >> "$METRICS_FILE"

# Performance metrics
echo "LOAD_TIME=$(( SECONDS = 0; providence governance load > /dev/null; echo $SECONDS ))" >> "$METRICS_FILE"
echo "VALIDATE_TIME=$(( SECONDS = 0; providence governance validate > /dev/null; echo $SECONDS ))" >> "$METRICS_FILE"

# Artifact sizes
echo "CORE_SIZE=$(stat -f%z .providence-wizard/compiled/governance-core.compiled.msgpack 2>/dev/null || echo 'N/A')" >> "$METRICS_FILE"
echo "CLIENT_SIZE=$(stat -f%z .providence-wizard/compiled/governance-client-template.compiled.msgpack 2>/dev/null || echo 'N/A')" >> "$METRICS_FILE"

# Disk usage
echo "DISK_USAGE=$(du -sh . | cut -f1)" >> "$METRICS_FILE"

# Error count
ERROR_COUNT=$(grep -c "ERROR\|FAILED" logs/*.log 2>/dev/null || echo "0")
echo "ERROR_COUNT=$ERROR_COUNT" >> "$METRICS_FILE"

echo "" >> "$METRICS_FILE"

echo "✅ Metrics collected: $METRICS_FILE"
```

---

## 🚨 Alerting

### Alert Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| **Artifact missing** | 🔴 CRITICAL | Check disk, recompile |
| **Load time >500ms** | 🟠 WARNING | Check I/O, review performance |
| **Fingerprint mismatch** | 🔴 CRITICAL | Investigate tampering |
| **Disk space <1GB** | 🟡 CAUTION | Cleanup and monitor |
| **Error rate >0.1%** | 🟠 WARNING | Review error logs |
| **Validation failure** | 🔴 CRITICAL | Full diagnostics |

### Alert Implementation

```bash
#!/bin/bash
# Save as: scripts/alerts.sh

check_artifacts() {
    if [ ! -f ".providence-wizard/compiled/governance-core.compiled.msgpack" ]; then
        echo "🚨 ALERT: Core artifact missing!"
        echo "Action: Recompile with: python .providence-wizard/compile_artifacts.py"
        return 1
    fi
    return 0
}

check_validation() {
    if ! providence governance validate &>/dev/null; then
        echo "🚨 ALERT: Governance validation failed!"
        echo "Action: Run 'providence governance validate' for details"
        return 1
    fi
    return 0
}

check_disk_space() {
    AVAILABLE=$(df . | awk 'NR==2 {print $4}')
    if [ "$AVAILABLE" -lt 1048576 ]; then  # 1GB in KB
        echo "🚨 ALERT: Low disk space! Available: $(echo "scale=2; $AVAILABLE/1024/1024" | bc)GB"
        return 1
    fi
    return 0
}

check_performance() {
    START=$(date +%s%N)
    providence governance load > /dev/null
    END=$(date +%s%N)
    DURATION=$(( (END - START) / 1000000 ))  # Convert to ms

    if [ "$DURATION" -gt 500 ]; then
        echo "⚠️  WARNING: Load time high! Duration: ${DURATION}ms"
        return 1
    fi
    return 0
}

# Run all checks
check_artifacts && check_validation && check_disk_space && check_performance
```

---

## 📊 Metrics Dashboard

### Real-Time Metrics

```bash
#!/bin/bash
# Save as: scripts/dashboard.sh
# Requires: watch command

watch -n 10 '
echo "=== SDD Health Dashboard ==="
echo "Updated: $(date)"
echo ""
echo "Performance:"
echo "  Load time: $(( SECONDS = 0; providence governance load > /dev/null; echo $SECONDS )ms"
echo "  Validate time: $(( SECONDS = 0; providence governance validate > /dev/null; echo $SECONDS )ms"
echo ""
echo "Artifacts:"
ls -lh .providence-wizard/compiled/ | grep msgpack | awk "{print \"  \" \$NF \": \" \$5}"
echo ""
echo "System:"
echo "  Disk: $(df -h . | awk '\''NR==2 {print $5 \" used, \" $4 \" free}'\''"
echo "  Memory: $(free -h | awk '\''NR==2 {print $3 \" used, \" $7 \" available}'\''"
'
```

### Weekly Report

```bash
#!/bin/bash
# Save as: scripts/weekly-report.sh

WEEK=$(date +%Y-W%V)
REPORT="reports/sdd-report-$WEEK.md"

cat > "$REPORT" << EOF
# SDD Weekly Monitoring Report

**Week:** $WEEK
**Generated:** $(date)

## Summary

- **Uptime:** [Calculate from logs]
- **Average Load Time:** [Calculate from metrics]
- **Total Validations:** [Count]
- **Failed Validations:** [Count]
- **Error Count:** [Count]

## Performance Trends

| Metric | Monday | Tuesday | Wednesday | Thursday | Friday |
|--------|--------|---------|-----------|----------|--------|
| Load Time (ms) | - | - | - | - | - |
| Validation Time (ms) | - | - | - | - | - |
| Error Count | - | - | - | - | - |

## Incidents

[List any incidents]

## Actions Taken

- [ ] Performance baseline updated
- [ ] Capacity check completed
- [ ] Backup verified
- [ ] Security audit completed

## Recommendations

[List recommendations for next week]

EOF

echo "✅ Report generated: $REPORT"
```

---

## 🔍 Diagnostic Commands

### System Health

```bash
# Comprehensive health check
echo "=== SDD System Health ==="

# 1. Governance state
echo "1. Governance:"
providence governance validate --verbose

# 2. Artifacts
echo ""
echo "2. Artifacts:"
cd .providence-wizard/compiled
md5sum * > /tmp/artifact.md5
echo "Checksums recorded"

# 3. Performance
echo ""
echo "3. Performance:"
for i in {1..5}; do
    time providence governance load > /dev/null
done

# 4. System resources
echo ""
echo "4. System Resources:"
ps aux | grep -E "sdd|wizard|python" | grep -v grep
du -sh .providence-*
free -h

echo ""
echo "=== Health Check Complete ==="
```

### Performance Profiling

```bash
#!/bin/bash
# Profile governance operations

echo "=== Performance Profile ==="
echo "Testing: $1 (50 iterations)"

TIMES=()
for i in {1..50}; do
    START=$(date +%s%N)
    providence governance load > /dev/null 2>&1
    END=$(date +%s%N)
    DURATION=$(( (END - START) / 1000000 ))  # ms
    TIMES+=($DURATION)
done

# Calculate statistics
MIN=${TIMES[0]}
MAX=${TIMES[0]}
SUM=0

for t in "${TIMES[@]}"; do
    [ "$t" -lt "$MIN" ] && MIN=$t
    [ "$t" -gt "$MAX" ] && MAX=$t
    SUM=$(( SUM + t ))
done

AVG=$(( SUM / ${#TIMES[@]} ))

echo ""
echo "Results:"
echo "  Iterations: ${#TIMES[@]}"
echo "  Min: ${MIN}ms"
echo "  Max: ${MAX}ms"
echo "  Average: ${AVG}ms"
echo "  Total: ${SUM}ms"
```

### Integrity Verification

```bash
#!/bin/bash
# Verify data integrity

echo "=== Integrity Verification ==="

# 1. File existence
echo "1. Files:"
[ -f ".providence-wizard/compiled/governance-core.compiled.msgpack" ] && echo "  ✅ Core" || echo "  ❌ Core missing"
[ -f ".providence-wizard/compiled/governance-client-template.compiled.msgpack" ] && echo "  ✅ Client" || echo "  ❌ Client missing"

# 2. Checksums
echo ""
echo "2. Checksums:"
cd .providence-wizard/compiled
md5sum * | while read hash file; do
    echo "  $file: $hash"
done
cd -

# 3. Fingerprints
echo ""
echo "3. Fingerprints:"
python3 << 'PYTHON'
import json

# Expected fingerprints
EXPECTED = {
    'core': '35efc54d3e353daaf633fad531562f1da97ec17814193b7ac44b2e9ef12daddd',
    'client': '2247922049fc14d93c174fb22a584e5640f3d456980ef57107a4083187591e38'
}

# Load metadata
with open('.providence-wizard/compiled/metadata-core.json') as f:
    core_meta = json.load(f)
with open('.providence-wizard/compiled/metadata-client-template.json') as f:
    client_meta = json.load(f)

# Compare
for key, expected in EXPECTED.items():
    if key == 'core':
        actual = core_meta.get('fingerprint')
    else:
        actual = client_meta.get('fingerprint')

    if actual == expected:
        print(f"  ✅ {key}: Match")
    else:
        print(f"  ❌ {key}: Mismatch!")
        print(f"     Expected: {expected}")
        print(f"     Got: {actual}")
PYTHON

# 4. Validation
echo ""
echo "4. Validation:"
providence governance validate | grep -E "✅|❌"
```

---

## 🔐 Compliance Monitoring

### Governance Compliance

```bash
#!/bin/bash
# Monitor governance compliance

echo "=== Governance Compliance ==="

# 1. Core immutability
echo "1. Core Immutability:"
if git diff HEAD .providence-core/CANONICAL/mandate.spec | grep -q "^[+-]"; then
    echo "  ⚠️  Core rules changed (expected if authorized)"
else
    echo "  ✅ Core rules unchanged"
fi

# 2. Client modifications
echo ""
echo "2. Client Modifications:"
MODIFIED=$(git status --porcelain .providence-core/CANONICAL/guidelines.dsl)
if [ -n "$MODIFIED" ]; then
    echo "  ℹ️  Client rules modified"
    git diff .providence-core/CANONICAL/guidelines.dsl
else
    echo "  ✅ Client rules unchanged since last commit"
fi

# 3. Configuration drift
echo ""
echo "3. Configuration Drift:"
git diff .providence-integration/
```

---

## 📋 Monitoring Checklist

### Daily (Morning)

```
[ ] Run health check: ./scripts/health-check.sh
[ ] Verify artifacts exist
[ ] Check governance validation passes
[ ] Review error logs from previous day
[ ] Confirm disk space >1GB
```

### Weekly (Monday)

```
[ ] Generate weekly report
[ ] Review performance trends
[ ] Audit compliance changes
[ ] Backup verification
[ ] Team health meeting
```

### Monthly (1st of month)

```
[ ] Full system audit
[ ] Capacity planning review
[ ] Performance baseline update
[ ] Security review
[ ] Governance compliance audit
[ ] Plan upcoming maintenance
```

### Quarterly

```
[ ] Full system upgrade testing
[ ] Load testing (simulated traffic)
[ ] Disaster recovery drill
[ ] Documentation review
[ ] Team training
```

---

## 📞 Monitoring Support

**For issues identified by monitoring:**

1. **High load times**
   - Check: Disk I/O, CPU usage
   - Action: Review performance profile
   - See: OPERATIONS.md #Performance

2. **Artifact issues**
   - Check: File existence, size
   - Action: Recompile artifacts
   - See: OPERATIONS.md #Troubleshooting

3. **Validation failures**
   - Check: Fingerprints, file integrity
   - Action: Run diagnostics
   - See: DEPLOYMENT.md #Rollback

4. **Disk space low**
   - Check: Space usage, old files
   - Action: Run cleanup
   - See: OPERATIONS.md #Cleanup

---

## 📚 Related Documentation

- [OPERATIONS.md](./OPERATIONS.md) — Daily operations
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Deployment procedures
- [MAINTENANCE.md](./MAINTENANCE.md) — Maintenance tasks
