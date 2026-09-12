# ADR-005 — `_REGISTRY` Stays in `skills.py` (Circular Import Avoidance)

**Status:** Accepted
**Date:** 2026-05-19
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

After the SkillEngine split (ADR-004), the natural placement for `_REGISTRY` (the hardcoded dict of 8 `SkillDefinition` objects) appeared to be `_skill_registry.py` alongside `SkillRegistry`. However, `_REGISTRY` depends on `SkillDefinition` and `TOKEN_BUDGET_*` from `_skill_contracts`, while `SkillRegistry` only depends on `SkillDefinition`. Moving `_REGISTRY` there would be semantically clean.

The problem arises when `skills.py` imports from both `_skill_registry.py` and `_skill_executor.py`:

```
skills.py
  → _skill_registry.py  (SkillRegistry)
  → _skill_executor.py  (SkillExecutor, handlers)
    → _skill_registry.py  (SkillRegistry)
```

If `_REGISTRY` were in `_skill_registry.py` and `skills.py` also imported `_REGISTRY` from there, the import chain would be:

```
skills.py → _skill_registry.py → _skill_contracts.py   ✓ (no cycle)
```

This is actually fine. The real issue was a different concern: `SkillExecutor` in `_skill_executor.py` needs to call `self._registry.get_skill()` — it does NOT import `_REGISTRY`. So moving `_REGISTRY` to `_skill_registry.py` would not create a cycle.

**However**, the `get_skill` implementation in `SkillRegistry` has a special behavior: when `_registry_source == "hardcoded"`, it reads from `self._fallback` (a live reference to the dict passed at construction) rather than from `self._skills` (a copy). This allows test code to mutate `_REGISTRY` after construction and have `get_skill` see the mutations — a pattern used in `test_run_skill_deprecated_emits_warning`.

---

## Decision

**`_REGISTRY` stays in `skills.py`. `SkillRegistry` receives it as a constructor parameter.**

```python
# skills.py
_REGISTRY: dict[str, SkillDefinition] = { ... }

class SkillEngine:
    def __init__(self, ...):
        self._registry = SkillRegistry(_REGISTRY, root)  # pass by reference
```

`SkillRegistry.__init__` stores the reference:

```python
class SkillRegistry:
    def __init__(self, fallback: dict[str, SkillDefinition], project_root: Path):
        self._fallback = fallback  # live reference, not a copy
```

`get_skill` reads from `self._fallback` when `_registry_source == "hardcoded"`, preserving the test mutation pattern.

---

## Consequences

**Positive:**

- No circular imports — `_skill_registry.py` has zero dependency on `skills.py`
- `SkillRegistry` is generic and testable with any `dict[str, SkillDefinition]`
- Test mutations to `_REGISTRY` remain visible to `SkillRegistry.get_skill` after construction

**Negative:**

- `_REGISTRY` is logically "registry data" but lives in the "facade" module — slightly non-obvious placement
- Developers moving skills must know to edit `skills.py`, not `_skill_registry.py`

**Files:**

- `packages/core/providence_runtime/src/providence_runtime/skills.py` — `_REGISTRY` definition
- `packages/core/providence_runtime/src/providence_runtime/_skill_registry.py` — `SkillRegistry._fallback`
- `packages/core/providence_runtime/tests/test_skill_registry.py` — `test_get_skill_reflects_live_fallback_mutations`
