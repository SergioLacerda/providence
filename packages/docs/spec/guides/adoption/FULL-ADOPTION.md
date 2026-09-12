# 🔵 Providence FULL — Complete Governance Adoption

**For:** Production teams, strict quality requirements, regulated industries
**Setup Time:** 40 minutes
**Commitment:** High (all 45 DoD criteria, 7-phase workflow)

---

## What is FULL?

Complete SDD implementation with:

- ✅ **15 constitutional principles**
- ✅ **16 mandatory rules**
- ✅ **45 Definition of Done criteria**
- ✅ **7-phase development workflow**
- ✅ Advanced architecture compliance
- ✅ Full AI agent integration
- ✅ Complete auditability & traceability

**When to use FULL:**

- Production teams building mission-critical software
- Regulated industries (compliance requirements)
- Large codebases (500+ lines of code)
- Distributed teams needing clear governance
- Onboarding requires explicit rules
- Change audit trails mandatory

---

## Quick Start (40 minutes)

```bash
# 1. Run setup wizard (5 min)
python EXECUTION/tools/setup-wizard.py --mode=full

# 2. Initialize all pre-commit hooks (10 min)
./scripts/setup-precommit-full.sh

# 3. Set up comprehensive tests (15 min)
pytest tests/architecture/test_layers.py -v
pytest tests/compliance/test_definition_of_done.py -v

# 4. Configure CI/CD governance (10 min)
./.github/workflows/sdd-compliance.yml

# Total: 40 minutes
echo "✅ FULL adoption complete!"
```

---

## The 15 Complete Principles

### Core Principles (1-5)

1. **Clean Architecture Foundation**
2. **Async-First Design**
3. **Ports & Adapters Pattern**
4. **Immutable Decisions (ADRs)**
5. **Explicit Governance Rules**

### Quality Principles (6-10)

1. **Zero Framework Bleed**
2. **Type Safety**
3. **Comprehensive Testing**
4. **Documentation as Code**
5. **Autonomous Developers**

### Enterprise Principles (11-15)

1. **Technology Stack Immutable**
2. **Data Governance**
3. **Security by Default**
4. **Performance as Requirement**
5. **Operational Excellence**

See [Rules Index](../../canonical/core/rules/INDEX.md) for full details.

---

## The 16 Mandatory Rules

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | All code in layers 1-5 must be framework-agnostic | Linting |
| 2 | All I/O must be async | Linting |
| 3 | All external deps through Ports | Code review |
| 4 | Type hints on all functions | Pre-commit |
| 5 | Docstrings for why (not what) | Pre-commit |
| 6 | ADRs for major decisions | Git hook |
| 7 | Domain tests: 100% coverage, zero mocks | CI/CD |
| 8 | UseCase tests: mock ports only | CI/CD |
| 9 | Integration tests for critical paths | CI/CD |
| 10 | No circular imports | Linting |
| 11 | No print() statements (use logging) | Linting |
| 12 | All errors mapped to HTTP status | Code review |
| 13 | Sensitive data never in logs | Security scan |
| 14 | Performance tests for bottlenecks | CI/CD |
| 15 | Runbook updated with changes | Checklist |
| 16 | Incident response documented | Checklist |

---

## The 45 Definition of Done Criteria

Organized by category:

### Architecture Compliance (9 items)

- [ ] Layer boundaries enforced (test passes)
- [ ] No framework imports in domain layers
- [ ] No framework imports in entity layers
- [ ] No framework imports in value objects
- [ ] Ports properly implemented (all methods)
- [ ] Adapters implement full port contract
- [ ] Error mapping in Layer 5 complete
- [ ] Security model implemented (all layers)
- [ ] Documentation for architecture decisions

### Async Compliance (8 items)

- [ ] No blocking operations in event loop
- [ ] No `time.sleep()` — use `asyncio.sleep()`
- [ ] All I/O operations are async
- [ ] All Port methods are async
- [ ] All UseCase methods are async
- [ ] All Adapter methods are async
- [ ] Connection pooling configured
- [ ] Timeout handling implemented

### Testing - Domain Layer (6 items)

- [ ] 100% code coverage
- [ ] Zero mocks used
- [ ] All edge cases tested
- [ ] All error paths tested
- [ ] All business rules validated
- [ ] Tests run in < 100ms

### Testing - UseCase Layer (7 items)

- [ ] Ports mocked, adapters not
- [ ] Success paths tested
- [ ] Error paths tested
- [ ] Port contract verified
- [ ] Transaction handling tested
- [ ] Concurrent request handling tested
- [ ] Timeout behavior tested

### Testing - Integration (6 items)

- [ ] Adapter contract tests pass
- [ ] Database migrations tested
- [ ] Cache invalidation tested
- [ ] Message queue delivery tested
- [ ] External API integration tested
- [ ] Retry logic tested

### Testing - E2E (5 items)

- [ ] Critical user journeys tested
- [ ] Happy path end-to-end
- [ ] Error recovery end-to-end
- [ ] Performance baseline met
- [ ] Load test (50+ concurrent) passed

### Code Quality (8 items)

- [ ] Type hints on all functions
- [ ] Docstrings present (why, not what)
- [ ] Comments for non-obvious code
- [ ] No dead code
- [ ] No hardcoded values (all config)
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No CSRF vulnerabilities

### Documentation (6 items)

- [ ] Architecture Decision Record (ADR) created
- [ ] Why documented (not just what)
- [ ] Requirements traced to code
- [ ] Integration points documented
- [ ] Error codes documented
- [ ] Runbook updated

### Security (4 items)

- [ ] Authentication tokens validated
- [ ] Authorization enforced
- [ ] Sensitive data encrypted at rest
- [ ] Audit trail complete

### Performance (3 items)

- [ ] Response time < SLA
- [ ] Memory usage acceptable
- [ ] Database queries optimized

### Process (3 items)

- [ ] Code review approved
- [ ] Team consensus documented
- [ ] Stakeholder sign-off obtained

---

## The 7-Phase Workflow

Each feature follows 7 phases:

**Phase 0: Specification** (30 min)

- Write requirements
- Design architecture
- Identify tests needed

**Phase 1: Domain** (1-2 hours)

- Implement domain logic (pure functions, no mocks)
- Test domain 100% coverage
- No framework imports

**Phase 2: Adapters** (1-2 hours)

- Implement ports (abstract interfaces)
- Create adapters (concrete implementations)
- Test adapters independently

**Phase 3: UseCases** (1-2 hours)

- Orchestrate domain + adapters
- Implement error handling
- Test with mocked ports

**Phase 4: Integration** (1 hour)

- Integration tests with real adapters
- Test database, cache, queues
- Verify end-to-end

**Phase 5: API** (30 min)

- FastAPI controllers/routes
- Request/response validation
- Error mapping to HTTP status codes

**Phase 6: Compliance** (30 min)

- Run architecture tests
- Check all 45 DoD criteria
- Security scan
- Performance test

**Phase 7: Deployment** (Ready for merge)

- Code review approval
- CI/CD pipeline green
- Runbook updated
- Ready for production

---

## Coming from LITE?

Easy upgrade path:

```bash
# 1. Extend constitution (5 new principles)
cp LITE-constitution.yaml FULL-constitution.yaml
# Edit: Add 5 enterprise principles

# 2. Activate additional rules (11 more)
# Edit CI/CD pipeline to enable 16 rules (vs 5)

# 3. Extend tests (35 more DoD items)
pytest tests/full/ --cov

# 4. Enable 7-phase workflow
# Update EXECUTION/_START_HERE.md reference

# Total: 30 minutes to upgrade
echo "✅ Upgraded to FULL!"
```

→ **Full guide:** [LITE to FULL Migration](./LITE-TO-FULL-MIGRATION.md)

---

## Governance Checklist

Before marking PR as "ready to merge":

- [ ] All 45 DoD criteria met
- [ ] Architecture tests pass
- [ ] Tests coverage > 90%
- [ ] Pre-commit hooks pass
- [ ] Security scan clean
- [ ] Performance baseline met
- [ ] Code review approved
- [ ] ADR created
- [ ] Runbook updated
- [ ] CI/CD pipeline green

---

## Key Metrics We Track

(Published in v2.2)

- First PR approval rate
- Implementation time per phase
- Bug escape rate
- Knowledge retention (onboarding time)
- Team satisfaction score

---

## Integration with AI Agents

Providence FULL supports complete AI agent autonomy:

- All rules explicit in code
- Governance enforced via CI/CD
- Decisions documented (ADRs)
- Context available in `.ai-index.md`
- Checkpoints automated

Agents can execute full 7-phase workflow autonomously.

---

## When NOT to Use FULL

❌ **Small hobby projects** → Use LITE
❌ **Temporary spike/PoC** → Use LITE
❌ **Learning SDD** → Start with LITE

✅ **Production systems** → Use FULL
✅ **Regulated industries** → Use FULL
✅ **Distributed teams** → Use FULL
✅ **Mission-critical** → Use FULL

---

## Need Help?

**Getting started?**
→ [README](../../../README.md)

**Detailed workflow?**
→ [CORE__START_HERE.md](../operational/CORE__START_HERE.md)

**Reference?**
→ [Rules](../../canonical/core/rules/INDEX.md)

**Questions?**
→ [FAQ](../faq.md)

**Emergency?**
→ [Troubleshooting](../operational/TROUBLESHOOTING_SPEC_VIOLATIONS.md)

**Want to go lighter?**
→ [Back to LITE](./LITE-ADOPTION.md)

---

## What Happens Next?

1. **You adopt FULL** (40 min setup)
2. **Follow 7-phase workflow** for each feature
3. **All 45 DoD criteria** enforced
4. **Gather metrics** for v2.2 improvements
5. **Provide feedback** — shape the roadmap

No "one size fits all". SDD is collaborative. Your needs matter.

---

**Ready? Let's go:** [CORE__START_HERE.md](../operational/CORE__START_HERE.md)

*Framework under active development. Your feedback drives priorities.*
