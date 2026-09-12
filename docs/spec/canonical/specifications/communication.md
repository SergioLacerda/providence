# 📢 Communication Standards

**How to document decisions, risks, and discoveries in SDD framework**

---

## 🎯 Purpose

Communication standards ensure:

- ✅ Decisions are documented before they're forgotten
- ✅ Risks are visible to the team
- ✅ Code reviews have context
- ✅ Future developers understand WHY choices were made

---

## 📝 Checkpoint Documentation

Every feature gets a checkpoint entry. This is THE source of truth.

### Location

File: `.providence/source/execution-state/_current.md`

### Template

```markdown
# Checkpoint Entry

[DATE @ AGENT_NAME]

**TASK:** [Feature/bug/improvement name]

**DECISIONS:**
- Decision 1: Why this way?
- Decision 2: Why NOT that way?

**ARCHITECTURE:**
- [If major changes] How does this fit into the system?
- [If extending existing] What was extended?

**TESTING:**
- Test approach: [TDD? Coverage %?]
- Edge cases tested: [List]
- Performance implications: [If any]

**QUESTIONS OPEN:**
- Q1: [What needs discussion]? (Owner: whoever)
- Q2: [What remains unresolved after code review]? (Owner: reviewer)

**RISKS:**
- R1: [Potential issue] - Mitigation: [how to prevent]
- R2: [Design debt] - Timeline: [when to pay it]

**LEARNINGS:**
- Learned: [Something surprising]
- Applied: [What pattern/rule was key]

**STATUS:** [complete/ready-for-review/blocked/etc]
```

### Example

```markdown
# Checkpoint Entry

[2026-04-19 @ copilot-agent-2]

**TASK:** Implement campaign narrative caching

**DECISIONS:**
- Chose TTL-based expiration (30 min) over LRU
  - Reason: Campaigns evolve frequently, stale data risk
- Kept backward compatible with old cache format
  - Reason: Rolling deployment, multiple servers active

**ARCHITECTURE:**
- Extended CacheService with TTLCache adapter
- Followed ports/adapters pattern (ADR-003)
- New file: src/infrastructure/cache/ttl_cache.py

**TESTING:**
- TDD: Tests written first, 95% coverage
- Edge cases: Empty cache, expired entries, concurrent access
- Performance: Cache hit rate >80% in benchmark

**QUESTIONS OPEN:**
- Should TTL be global or per-campaign? (Owner: tech lead)
- Need monitoring for cache efficiency? (Decision: in review)

**RISKS:**
- Active sessions may invalidate on deploy
  - Mitigation: Use rolling restart, 5-min cache extension
- Cache memory growth with N campaigns
  - Timeline: Monitor in Q2, cap if needed

**LEARNINGS:**
- Redis TTL commands simpler than expected
- Thread isolation made testing much easier

**STATUS:** Ready for review
```

---

## 💬 Code Comments

Comments explain WHY, not WHAT. Code shows WHAT.

### Good Comment Pattern

```python
# WHY are we doing this?
# (Not: WHAT are we doing - code shows that)

# We cache narrative responses for 30 min because:
# 1. Narratives don't change frequently
# 2. Cache hit rate is >80% in production
# 3. TTL prevents stale data during campaign evolution
cache_ttl = 30 * 60  # seconds
```

### Bad Comment Pattern

```python
# ❌ Restating what code already says
cache_ttl = 30 * 60  # Set cache TTL to 30 minutes

# ❌ Being vague
# Do some caching stuff
# Performance optimization
```

### ADR Reference in Comments

When following an architectural decision, reference it:

```python
# Following ADR-003 (Ports & Adapters Pattern)
# Never import concrete implementations directly
from src.domain.ports import CachePort  # ✅ Abstract port
from src.infrastructure.cache import RedisCache  # ❌ Concrete impl

cache: CachePort = RedisCache()  # Inject adapter
```

---

## 📋 Decision Format (In Code)

When code embodies a decision:

```python
"""
DECISION: Use append-only storage (ADR-006)

Why:
- Enables audit trail of all changes
- Immutable history prevents data corruption
- Time-travel debugging becomes possible

Consequence:
- Slightly more disk usage (mitigation: archive old data)
- Queries must handle temporal dimension
"""


class AppendOnlyLog:
    def append(self, entry: Entry) -> None:
        # Implementation follows ADR-006 patterns
        pass
```

---

## ⚠️ Risk Documentation

### In Checkpoint (Strategic Risks)

```markdown
**RISKS:**
- R1: Cache invalidation on deploys
  - Severity: Medium
  - Likelihood: High
  - Mitigation: Rolling restart + cache extension
  - Owner: DevOps
  - Timeline: Monitor for Q2
```

### In Code (Tactical Risks)

```python
# WARNING: Edge case not handled in MVP
# If campaign updated while caching in progress:
# - Old data may be served for 30 min
# Tracked in: issue #456
# Fix timeline: Q2 optimization phase


def get_cached_narrative(campaign_id: str) -> str:
    # Implementation
    pass
```

---

## 🎓 Design Decision Format

When documenting a design choice:

```python
"""
DESIGN DECISION: Use hexagonal architecture (ADR-001)

Context:
- Multiple interfaces (CLI, API, Discord bot)
- Frequent infrastructure changes

Options considered:
1. Monolithic MVC (rejected: tight coupling)
2. Microservices (rejected: too complex early)
3. Hexagonal: ✅ Chosen

Rationale:
- Clear separation of concerns
- Easy to swap implementations
- Testable in isolation

Constraints:
- Requires discipline (must use ports)
- Slightly more boilerplate

Trade-offs:
- More files (cost) for flexibility (benefit)
"""


class DomainService:
    def __init__(self, storage_port: StoragePort):
        self.storage = storage_port  # Always inject
```

---

## 📊 Metrics & Evidence

When a decision has performance implications:

```python
"""
PERFORMANCE DECISION: Cache with 30-min TTL

Evidence:
- Production data: 82% cache hit rate
- Response time: 10ms (cached) vs 450ms (uncached)
- Memory impact: <5% increase with N=1000 campaigns

Validation:
- Benchmark: src/tests/perf/cache_benchmark.py
- Result: >80% hit rate threshold met
- Monitor: metrics/cache_efficiency.py
"""
```

---

## 🔍 When to Document

| Situation | Document Where | Format |
|-----------|-----------------|--------|
| Feature complete | Checkpoint | Full template |
| Choosing algorithm | Code comment | WHY explanation |
| Following ADR | Code docstring | Reference ADR |
| Found issue | Code comment | WARNING + issue link |
| Performance choice | Code + checkpoint | Evidence-based |
| Design decision | Code docstring | Options + rationale |
| Risk identified | Checkpoint | Risk + mitigation |
| Learning discovered | Checkpoint | Insight + application |

---

## ✅ Documentation Checklist

For each checkpoint, verify:

- [ ] **Task:** Clear description of what was done
- [ ] **Decisions:** Why this way, not that way?
- [ ] **Architecture:** How does it fit? What was extended?
- [ ] **Testing:** What was tested? What's the coverage?
- [ ] **Questions:** What needs discussion? Who owns it?
- [ ] **Risks:** What could go wrong? How prevent?
- [ ] **Learnings:** What surprised you? What pattern helped?
- [ ] **Status:** Is this complete or blocked?

---

## 🎯 Excellence Criteria

Your communication is excellent when someone reading it 6 months later:

- ✅ Understands WHAT you built
- ✅ Understands WHY you built it that way
- ✅ Understands WHAT COULD GO WRONG
- ✅ Knows WHERE to find related code
- ✅ Can MAINTAIN or EXTEND it confidently

---

## 📞 Example: Complete Communication

### Code Level

```python
# ADR-003: Ports & Adapters Pattern
# We abstract storage behind a port to allow testing
# without a real database

from src.domain.ports import StoragePort


class NarrativeService:
    """
    DESIGN DECISION: Hexagonal architecture (ADR-001)

    Why:
    - Multiple interfaces need narrative data
    - Storage implementation may change
    - Must be testable without database
    """

    def __init__(self, storage: StoragePort):
        # Following ADR-003: inject abstract port, never concrete
        self.storage = storage

    def get_narrative(self, campaign_id: str) -> str:
        # WARNING: Long campaigns (>10K tokens) may timeout
        # Tracked in: issue #234
        # Mitigation: Pagination in Q2

        # Decision: Cache for 30 min
        # Evidence: 82% hit rate in production
        # See: metrics/cache_efficiency.py
        return self.storage.get_cached(campaign_id)
```

### Checkpoint Level

```markdown
[2026-04-19 @ copilot-agent-1]

**TASK:** Implement narrative caching with TTL

**DECISIONS:**
- Cache TTL: 30 minutes (vs LRU)
  - Campaigns evolve, stale data risk higher than memory
- Kept backward compatibility
  - Multiple servers in prod, rolling deploy needed

**ARCHITECTURE:**
- Extended CacheService (ADR-003 ports/adapters)
- New: src/infrastructure/cache/ttl_cache.py
- Followed hexagonal pattern (ADR-001)

**TESTING:**
- TDD: 100% tests first
- Coverage: 95% (code: 100%, integration: 85%)
- Edge cases: Expiry, concurrent access, empty cache
- Perf: 82% hit rate achieved (goal: >80%)

**RISKS:**
- Sessions invalidate on deploy
  - Mitigation: Rolling restart + 5-min extension
- Memory growth with N campaigns
  - Monitor Q2, cap if threshold exceeded

**LEARNINGS:**
- Redis TTL simpler than expected
- Thread isolation made testing trivial

**STATUS:** Ready for review
```

---

## 📖 Learn More

**For rules on communication:** See [Core Rules](../core/rules/) and [Mandates](../core/mandates/)

**For definition of done:** See [definition_of_done.md](./definition_of_done.md) (documentation section)

**For templates:** See this file (all sections contain templates)
