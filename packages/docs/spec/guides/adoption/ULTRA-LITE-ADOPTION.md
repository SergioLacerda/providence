# ⚡ SDD ULTRA-LITE — Zero-Config Adoption

**For:** Solo developers, prototypes, MVPs, 2-person teams
**Setup Time:** 5 minutes
**Commitment:** Minimal (upgrade to LITE anytime)

---

## What is ULTRA-LITE?

Absolute minimum viable version of SDD with:

- ✅ **5 core principles** (vs 10 LITE, 15 FULL)
- ✅ **3 essential rules** (vs 5 LITE, 16 FULL)
- ✅ **5 DoD checkpoints** (vs 10 LITE, 45 FULL)
- ✅ Single `.ai-constitution.md` file
- ✅ No external dependencies
- ✅ Pure async-first thinking

**When to use ULTRA-LITE:**

- Solo developer prototyping
- 2-person startup MVP
- Learning SDD core concepts (5 min intro)
- Rapid proof-of-concept
- Side project with AI agent
- Before committing to LITE

---

## Quick Start (5 Minutes)

```bash
# 1. Create constitution file (1 min)

# Option A: Quick inline version (fastest)cat > .providence/constitution.md << 'EOF'
# Ultra-Lite Constitution- Clean Domain: Business logic free of framework
- Async Everything: No blocking I/O
- Explicit Rules: Document your choices
- Test Pyramid: Unit → Integration → E2E
- Progressive Disclosure: Grow as needed
EOF

# Option B: Use template (more structured)# cp EXECUTION/spec/guides/adoption/templates/lite-constitution.yaml .providence/constitution.yaml
# 2. Set three rules (1 min)echo "✅ Rule 1: All I/O operations are async"
echo "✅ Rule 2: No framework code in domain layer"
echo "✅ Rule 3: Every feature has a test"

# 3. Validate with 5 DoD checkpoints (3 min)# ✅ Code written (domain logic in domain/)# ✅ Tests passing (pytest tests/)# ✅ Types valid (mypy src/)# ✅ No blocking I/O# ✅ Async pattern used
# Total: 5 minutesecho "✅ ULTRA-LITE ready!"
```

---

## ULTRA-LITE vs LITE vs FULL

| Aspect | ULTRA-LITE | LITE | FULL |
|--------|-----------|------|------|
| **Setup Time** | 5 min | 15 min | 40 min |
| **Principles** | 5 | 10 | 15 |
| **Rules** | 3 | 5 | 16 |
| **DoD Checkpoints** | 5 | 10 | 45 |
| **Documentation** | 1 file | Docs/ | Full spec/ |
| **Pre-commit** | None | Basic | Full |
| **Tests Required** | Unit | Core | All |
| **Architecture Tests** | No | Basic | Comprehensive |
| **Upgrade Path** | LITE | FULL | — |
| **Best For** | Prototype | Small team | Production |
| **Cognitive Load** | Minimal | Low | High |

---

## The 5 Core ULTRA-LITE Principles

### 1️⃣ **Clean Domain**Business logic isolated from framework. Framework stays in adapter layer

### 2️⃣ **Async Everything**All I/O is async. No blocking calls. Think: `async def`, not `def`

### 3️⃣ **Explicit Rules**Document your choices. "Why?" matters more than "What?"

### 4️⃣ **Test Pyramid**Write unit tests (fast), integration tests (medium), e2e tests (slow). Ratio: 70:20:10

### 5️⃣ **Progressive Disclosure**Start minimal. Grow governance as team grows. ULTRA-LITE → LITE → FULL

---

## The 3 Essential Rules

### Rule 1: Async Everything```python

# ✅ GOODasync def fetch_user(user_id: int) -> User

    return await db.query(User).filter_by(id=user_id).first()

# ❌ BADdef fetch_user(user_id: int) -> User

    return db.query(User).filter_by(id=user_id).first()  # Blocking!

```

### Rule 2: No Framework in Domain```python
# ✅ GOOD - domain/ folderclass User:
    id: int
    name: str
    email: str

# ❌ BAD - domain/ folderfrom fastapi import Depends
class User(BaseModel):
    id: int
    name: str
```

### Rule 3: Every Feature Has a Test```python

# ✅ GOOD - tests/test_user_repository.pyasync def test_fetch_user_returns_user()

    result = await fetch_user(1)
    assert result.id == 1

# ❌ BAD - No test file```

---

## 5 DoD Checkpoints

Before committing, verify:

- [ ] **Code is in domain/** — Business logic not in adapter layer
- [ ] **All I/O is async** — No `def` functions doing I/O
- [ ] **Tests pass** — `pytest tests/` succeeds
- [ ] **Types valid** — `mypy src/` has no errors
- [ ] **No framework bleed** — Domain has zero FastAPI/Flask imports

---

## Example Project Structure

```
my-project/
├── .providence/
│   └── constitution.md          ← Your 5 principles
│
├── src/
│   ├── domain/
│   │   ├── user.py              ← Pure business logic
│   │   └── repository.py         ← Async interfaces
│   │
│   └── adapters/
│       ├── db.py                ← FastAPI/Database layer
│       └── api.py               ← HTTP layer
│
├── tests/
│   ├── test_user.py             ← Domain tests
│   ├── test_repository.py        ← Async tests
│   └── test_api.py              ← Integration tests
│
└── requirements.txt
```

---

## Upgrade Path

**When your team grows beyond ULTRA-LITE:**

### Step 1: Pick LITE → [LITE-ADOPTION.md](./LITE-ADOPTION.md)- 10 principles (add 5 more)

- 5 rules (add 2 more)
- 10 DoD criteria (add 5 more)
- Setup pre-commit hooks
- Add governance automation

### Time: 10 minutesAll ULTRA-LITE code stays valid. Just add layers on top

---

## Philosophy

**ULTRA-LITE is not a compromise.**

It's the **essential kernel** of SDD thinking:

- Clean separation of concerns
- Async-first architecture
- Explicit governance
- Test discipline
- Grow as needed

Perfect for:

- **Solopreneurs** starting a project
- **Startups** validating an idea
- **Researchers** prototyping algorithms
- **Learning** how SDD works

Grow to LITE when:

- 3+ people on team
- Clear roadmap for 6+ months
- Need predictable quality

Grow to FULL when:

- 5+ people
- Production mission-critical
- Regulatory requirements

---

## Next Steps

**Ready to start?**

1. Create `.providence/constitution.md` (copy the 5 principles above)
2. Create `.providence/rules.md` (copy the 3 rules above)
3. Create `tests/` folder (start with 1 test file)
4. Begin coding with async-first mindset
5. Check DoD checklist before each commit

**Questions?**

- Want more structure? → [LITE-ADOPTION.md](./LITE-ADOPTION.md)
- Want full governance? → [FULL-ADOPTION.md](./FULL-ADOPTION.md)
- Want comparison? → [INDEX.md](./INDEX.md)

---

**Philosophy: Start tiny, think big, scale intentionally.** 🚀

*ULTRA-LITE adoption: 5 principles. 3 rules. Infinite potential.*
