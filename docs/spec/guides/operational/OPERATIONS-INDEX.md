# 📖 SDD v3.0 Operational Documentation Index

**Production operations guides for SDD Framework v3.0**

**Version:** 3.0 | **Date:** April 22, 2026 | **For:** DevOps, Site Reliability Engineers, System Administrators

---

## 🎯 Quick Start

**Select your role:**

| Role | Purpose | Start Here |
|------|---------|------------|
| **🏥 DevOps/SRE** | Operate SDD in production | [OPERATIONS.md](#operations) |
| **🚀 Release Manager** | Deploy SDD updates | [DEPLOYMENT.md](#deployment) |
| **👁️ Monitoring Specialist** | Monitor system health | [MONITORING.md](#monitoring) |
| **🛠️ Systems Administrator** | Maintain infrastructure | [MAINTENANCE.md](#maintenance) |
| **📊 Tech Lead** | Understand operational model | [Overview](#overview) |

---

## 📚 Documentation Map

### 🎯 Overview

**What is SDD v3.0 from an operational perspective?**

- **Architecture:** CORE (immutable) + CLIENT (customizable) governance
- **Deployment Model:** Stateless, file-based configuration
- **Runtime:** CLI tool + Wizard pipeline
- **Data:** Compiled msgpack artifacts + metadata
- **SLA:** 99.9% availability, <500ms load time

**Read:** [SDD Architecture Overview](.providence-core/README.md)

### 📋 Operations <a name="operations"></a>

**Daily operational procedures and common tasks**

| Task | Duration | Link |
|------|----------|------|
| Morning health check | 5 min | [OPERATIONS.md: Daily Operations](./OPERATIONS.md#daily-operations) |
| Load governance | 2 min | [OPERATIONS.md: Load Config](./OPERATIONS.md#2-load-governance-configuration-2-min) |
| Initialize new project | 30 min | [OPERATIONS.md: New Project](./OPERATIONS.md#3-initialize-new-project-30-min) |
| Troubleshooting | 10-30 min | [OPERATIONS.md: Troubleshooting](./OPERATIONS.md#troubleshooting) |
| Performance tuning | 15-30 min | [OPERATIONS.md: Performance](./OPERATIONS.md#performance) |

**Read:** [OPERATIONS.md](./OPERATIONS.md)

### 🚀 Deployment <a name="deployment"></a>

**Production deployment and rollback procedures**

| Phase | Duration | Link |
|-------|----------|------|
| Pre-deployment checklist | 15 min | [DEPLOYMENT.md: Pre-Deployment](./DEPLOYMENT.md#pre-deployment-checklist) |
| Deployment steps | 5-15 min | [DEPLOYMENT.md: Deployment](./DEPLOYMENT.md#deployment-steps) |
| Post-deployment verification | 10-20 min | [DEPLOYMENT.md: Validation](./DEPLOYMENT.md#post-deployment-verification) |
| Rollback procedures | 10-30 min | [DEPLOYMENT.md: Rollback](./DEPLOYMENT.md#rollback-procedures) |

**Read:** [DEPLOYMENT.md](./DEPLOYMENT.md)

### 👁️ Monitoring <a name="monitoring"></a>

**Health checks, metrics, and alerting**

| Component | Check | Frequency | Link |
|-----------|-------|-----------|------|
| **System Health** | Artifacts, CLI, validation | Daily | [MONITORING.md: Health Dashboard](./MONITORING.md#1-morning-health-dashboard-5-min) |
| **Performance** | Load time, validation time | Every 30 min | [MONITORING.md: Metrics](./MONITORING.md#2-metric-collection-every-30-min) |
| **Alerts** | Failures, high load, disk | Real-time | [MONITORING.md: Alerting](./MONITORING.md#alerting) |
| **Diagnostics** | Detailed analysis | As-needed | [MONITORING.md: Diagnostics](./MONITORING.md#diagnostic-commands) |

**Read:** [MONITORING.md](./MONITORING.md)

### 🛠️ Maintenance <a name="maintenance"></a>

**Long-term system upkeep and optimization**

| Task | Frequency | Duration | Link |
|------|-----------|----------|------|
| **Daily Backup** | Every day | 15 min | [MAINTENANCE.md: Daily Tasks](./MAINTENANCE.md#daily-tasks-15-min) |
| **Weekly Cleanup** | Every week | 1 hour | [MAINTENANCE.md: Weekly Tasks](./MAINTENANCE.md#weekly-tasks-1-hour) |
| **Monthly Refresh** | Every month | 2-3 hours | [MAINTENANCE.md: Monthly Tasks](./MAINTENANCE.md#monthly-tasks-2-3-hours) |
| **Quarterly Updates** | Every quarter | 2-4 hours | [MAINTENANCE.md: Quarterly](./MAINTENANCE.md#quarterly-upgrades-2-4-hours) |

**Read:** [MAINTENANCE.md](./MAINTENANCE.md)

---

## 📍 When to Use Each Guide

### 🚨 Something is Wrong

**Problem:** System not working
**Action:** Go to [OPERATIONS.md: Troubleshooting](./OPERATIONS.md#troubleshooting)

```
Check:
1. Is artifact missing? → Recompile
2. Is validation failing? → Check fingerprints
3. Is CLI broken? → Reinstall
4. Is load time slow? → Check I/O
```

### 📦 Need to Deploy

**Problem:** Deploying to production
**Action:** Follow [DEPLOYMENT.md](./DEPLOYMENT.md) checklist

```
Steps:
1. Pre-deployment checks (15 min)
2. Backup current environment (5 min)
3. Compile & deploy (5 min)
4. Validate deployment (20 min)
5. Document changes (5 min)
```

### 📊 Need to Monitor

**Problem:** Check if system is healthy
**Action:** Run [MONITORING.md: Health Dashboard](./MONITORING.md#1-morning-health-dashboard-5-min)

```
Commands:
./scripts/health-check.sh          # Daily morning
providence governance validate             # Verify integrity
./scripts/collect-metrics.sh        # Performance tracking
```

### 🛠️ Need to Maintain

**Problem:** Regular upkeep, cleanup, refresh
**Action:** Follow [MAINTENANCE.md schedule](./MAINTENANCE.md#maintenance-schedule)

```
Daily:     Backup + health check
Weekly:    Cleanup + performance review
Monthly:   Artifact refresh + compliance
Quarterly: System update + disaster recovery drill
```

---

## 🔍 Key Concepts

### Operational Model

| Component | Type | Importance | Details |
|-----------|------|-----------|---------|
| **Governance Core** | Immutable | 🔴 Critical | 4 rules, cannot be changed at runtime |
| **Governance Client** | Mutable | 🟠 Important | 151 guidelines, teams select which to use |
| **Compiled Artifacts** | Runtime | 🔴 Critical | msgpack binaries, must exist and be valid |
| **CLI Tool** | Interface | 🟠 Important | Provides access to governance system |
| **Wizard Pipeline** | Process | 🟡 Standard | Single guided-flow project initialization |

### Critical Files

```
.providence-core/
├── CANONICAL/
│   ├── mandate.spec          ← Core governance source
│   ├── guidelines.dsl        ← Client governance source
│   └── metadata.json         ← Framework metadata
└── [operational guides below]
    ├── OPERATIONS.md         ← Daily operations
    ├── DEPLOYMENT.md         ← Deployment checklist
    ├── MONITORING.md         ← Health monitoring
    └── MAINTENANCE.md        ← System upkeep

.providence-wizard/
└── compiled/
    ├── governance-core.compiled.msgpack
    ├── governance-client-template.compiled.msgpack
    ├── metadata-core.json
    ├── metadata-client-template.json
    └── DEPLOYMENT_MANIFEST.json

generated/client/build/final-template/
└── .providence/
    ├── compiled/
    │   ├── governance-core.compiled.msgpack
    │   ├── governance-client-template.compiled.msgpack
    │   ├── metadata-core.json
    │   └── metadata-client-template.json
    └── DEPLOYMENT_MANIFEST.json
```

### Performance Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Load Time** | <200ms | >500ms |
| **Validate Time** | <300ms | >1s |
| **Generate Time** | <500ms | >2s |
| **Error Rate** | 0% | >0.1% |
| **Uptime** | 99.9% | <99% |

---

## 🆘 Support Matrix

| Issue | Guide | Command |
|-------|-------|---------|
| **Artifact missing** | Operations | `python .providence-wizard/compile_artifacts.py` |
| **Validation failed** | Operations | `providence governance validate --verbose` |
| **Load time slow** | Monitoring | `time providence governance load` |
| **Deployment failed** | Deployment | See rollback procedures |
| **Disk space low** | Maintenance | `./scripts/weekly-cleanup.sh` |
| **Corruption detected** | Maintenance | Check backups, restore from latest |

---

## 📅 Implementation Timeline

**For new SDD deployment:**

```
Day 1 (30 min)
├── Read: README.md + OPERATIONS.md overview
├── Setup: Health check script
└── Action: Deploy with DEPLOYMENT.md checklist

Week 1 (2 hours)
├── Setup: Daily backup automation
├── Setup: Health monitoring dashboard
├── Setup: Alert system
└── Action: Daily health checks

Week 2+ (Ongoing)
├── Daily (15 min): Health check + backup
├── Weekly (1 hour): Cleanup + performance review
├── Monthly (2-3 hours): Artifact refresh + compliance
└── Quarterly (2-4 hours): Updates + disaster recovery drill
```

---

## 🔗 Navigation

**Other important documentation:**

- **Framework Overview:** [CORE__START_HERE.md](./CORE__START_HERE.md)
- **Architecture Details:** [.providence-core/NAVIGATION.md](./NAVIGATION.md)
- **Specific Operational Tasks:** [OPERATIONS.md](./OPERATIONS.md)
- **Troubleshooting Deep-Dive:** [TROUBLESHOOTING_SPEC_VIOLATIONS.md](./TROUBLESHOOTING_SPEC_VIOLATIONS.md)
- **Integration Workflow:** [INTEG_INDEX.md](../integration/INTEG_INDEX.md)

---

## 📞 Getting Help

**For operational questions:**

1. **Check these guides** — 90% of issues covered
2. **Review troubleshooting** — Specific issue diagnostic
3. **Search documentation** — Look in spec/guides/
4. **Escalate** — Contact SDD framework team

**When escalating, provide:**

- OS and environment info
- Exact command run
- Full error message
- Recent changes made
