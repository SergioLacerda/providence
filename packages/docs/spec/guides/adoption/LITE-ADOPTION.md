# 🟢 Providence LITE — Minimal Governance Adoption

**For:** Teams wanting to experiment, small projects, learning SDD
**Setup Time:** 15 minutes
**Commitment:** Low (can upgrade to FULL anytime)

---

## What is LITE?

Minimal version of SDD with:

- ✅ **10 core constitutional principles** (vs 15 FULL)
- ✅ **5 mandatory rules** (vs 16 FULL)
- ✅ **10 essential DoD criteria** (vs 45 FULL)
- ✅ Basic pre-commit hooks
- ✅ Essential architecture tests
- ❌ NOT: 7-phase workflow, advanced compliance

**When to use LITE:**

- Learning SDD patterns
- Small teams (< 5 people)
- Side projects, experiments
- Onboarding new teams to governance concepts
- Validating if SDD fits your workflow

---

## Quick Start (15 minutes)

```bash
# 1. Copy LITE constitution template (2 min)
cp EXECUTION/spec/guides/adoption/templates/lite-constitution.yaml .providence/constitution.yaml

# 2. Customize for your project (5 min)
# Edit .providence/constitution.yaml with:
# - project_name
# - domain
# - customize the 5 principles for your domain
# - customize the 3 rules

# 3. Initialize basic tests (3 min)
mkdir -p tests/
cat > tests/test_constitution.py << 'EOF'
import os
def test_no_framework_in_domain():
    """Your constitution says: no framework imports in domain"""
    result = os.system('grep -r "import fastapi" src/domain/ 2>/dev/null')
    assert result != 0, "Framework leaked into domain!"
EOF

# 4. Commit your constitution (2 min)
git add .providence/constitution.yaml
git commit -m "Add Providence LITE constitution"

# 5. Verify setup (3 min)
pytest tests/test_constitution.py -v

# Total: 15 minutes
echo "✅ LITE adoption complete!"
```

**Need help customizing?**
→ See [Core Mandates](../../canonical/core/mandates/INDEX.md)

---

## LITE vs FULL Comparison

| Aspect | LITE | FULL |
|--------|------|------|
| **Setup Time** | 15 min | 40 min |
| **Principles** | 10 core | 15 total |
| **Rules** | 5 essential | 16 complete |
| **DoD Criteria** | 10 items | 45 items |
| **Tests Required** | Core layers | All layers |
| **Workflow** | 3 phases | 7 phases |
| **Pre-commit Checks** | 5 hooks | 12 hooks |
| **Architecture Validation** | Basic | Comprehensive |
| **Upgrade Path** | Yes → FULL | — |
| **Best For** | Learning | Production |

---

## The 10 Core LITE Principles

### 1. **Clean Architecture Basics**

- Domain layer isolated
- No framework bleed into domain
- Clear separation of concerns

### 2. **Async-First Mindset**

- All I/O is async
- No blocking calls in event loop
- `async def` for all services

### 3. **Ports & Adapters Pattern**

- Abstract external dependencies
- Multiple adapter implementations possible
- Domain knows no adapters

### 4. **Immutable Decisions (ADRs)**

- Document major architectural choices
- Why, not just what
- Link decisions to code

### 5. **Explicit Governance Rules**

- Rules live in code and docs
- No ambiguous "best practices"
- Everyone knows the rules

### 6. **Zero Framework Bleed**

- Framework stays in outer layers
- Business logic framework-agnostic
- Testable without framework

### 7. **Type Safety**

- Use Python type hints
- Pydantic for validation
- Benefits: IDE support, self-documentation

### 8. **Test Every Layer**

- Domain: pure, no mocks
- UseCase: mock ports only
- Integration: real adapters
- E2E: full stack

### 9. **Document Assumptions**

- Docstrings for why (not what)
- ADRs for decisions
- Code comments for non-obvious

### 10. **Autonomous Developers**

- Clear rules → less approval friction
- Developers operate confidently
- Governance enforced via CI, not meetings

---

## The 5 Essential LITE Rules

1. **Layer Validation** — Automated tests check layer boundaries
2. **Async Compliance** — No blocking calls (linting catches)
3. **Port Contracts** — All adapters implement ports fully
4. **Type Hints** — All functions have type annotations
5. **ADR Logging** — Major decisions documented in code

---

## The 10 Essential DoD Criteria

### Architecture (3 items)

- [ ] Clean architecture layers properly separated
- [ ] No framework imports in domain layers
- [ ] Ports properly abstracted

### Testing (3 items)

- [ ] Domain tests: 100% coverage, no mocks
- [ ] UseCase tests: mock ports only
- [ ] Integration tests: critical paths covered

### Code Quality (2 items)

- [ ] Type hints on all functions
- [ ] Docstrings present (why not what)

### Process (2 items)

- [ ] ADR documented for major decisions
- [ ] Pre-commit checks passing

---

## Setup Checklist

- [ ] Read this file (5 min)
- [ ] Run quick start script (15 min)
- [ ] Try your first feature following [ULTRA-LITE-ADOPTION.md](./ULTRA-LITE-ADOPTION.md)
- [ ] Ask questions → [FAQ](../faq.md)

---

## Upgrade to FULL

When you're ready for production and want comprehensive governance:

✅ **Conditions to consider upgrading:**

- Team is comfortable with basic SDD concepts
- Project growing (>500 lines code)
- Need production-grade compliance
- Multiple developers on same project

→ **[Upgrade Guide: LITE to FULL](./LITE-TO-FULL-MIGRATION.md)**

This gives you:

- 5 additional principles
- 11 more mandatory rules
- 35 additional DoD criteria
- Full 7-phase workflow
- Comprehensive testing + compliance

---

## Key Differences from FULL

### LITE Focuses On

✅ Learning core architecture concepts
✅ Getting started quickly
✅ Validation for small teams
✅ Easy upgrade path

### FULL Focuses On

✅ Production readiness
✅ Comprehensive compliance
✅ Regulated industries
✅ Mission-critical systems

---

## Need Help?

**Getting started?**
→ [ULTRA-LITE-ADOPTION.md](./ULTRA-LITE-ADOPTION.md)

**Have questions?**
→ [FAQ](../faq.md)

**Emergency?**
→ [Troubleshooting](../operational/TROUBLESHOOTING_SPEC_VIOLATIONS.md)

**Ready to upgrade?**
→ [LITE to FULL Migration](./LITE-TO-FULL-MIGRATION.md)

---

## What Happens Next?

1. **You adopt LITE** (15 min setup)
2. **Build 1-2 features** using LITE principles
3. **Gather feedback** on what works/what doesn't
4. **Decide:** Stay LITE or upgrade to FULL

No pressure. SDD is collaborative. Your experience shapes v2.2.

---

**Ready? Start here:** [ULTRA-LITE-ADOPTION.md](./ULTRA-LITE-ADOPTION.md)

*Framework under active development. Your feedback drives priorities.*
