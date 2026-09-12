# ADR-004 — SkillEngine Split: SkillRegistry + SkillExecutor + Facade

**Status:** Accepted
**Date:** 2026-05-19
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

`SkillEngine` was a 414-line class mixing two independent responsibilities:

1. **Registry** (~197 lines): loading skills from disk, deduplication, lookup by name, export in 6 formats
2. **Execution** (~217 lines): `run_skill` template, command execution, telemetry, footer policy

Both responsibilities had different change reasons, different collaborators, and different test scopes. The registry was tested via `engine.list_skills()` / `engine.get_skill()`. The executor was tested via `engine.run_skill()`. There was no reason for these to share a class boundary.

---

## Decision

**Split `SkillEngine` into three units:**

| Class | File | Responsibility |
|---|---|---|
| `SkillRegistry` | `_skill_registry.py` | Disk loading, list, get, export |
| `SkillExecutor` | `_skill_executor.py` | `run_skill`, `_execute_commands`, telemetry, footer policy |
| `SkillEngine` | `skills.py` | 4-method facade delegating to registry + executor |

`SkillEngine.__init__` creates both collaborators:

```python
class SkillEngine:
    def __init__(self, sink=None, project_root=None):
        self._registry = SkillRegistry(_REGISTRY, root)
        self._executor = SkillExecutor(self._registry, sink)

    def list_skills(self):
        return self._registry.list_skills()

    def get_skill(self, name):
        return self._registry.get_skill(name)

    def export_skills_payload(self, fmt):
        return self._registry.export_skills_payload(fmt)

    def run_skill(self, name, **kw):
        return self._executor.run_skill(name, **kw)
```

---

## Consequences

**Positive:**

- `SkillRegistry` is independently testable with any fallback dict — no `SkillEngine` needed
- `SkillExecutor` is independently testable with a real `SkillRegistry(fallback, tmp_path)` — no full engine needed
- Adding a new export format = edit `SkillRegistry` only
- Zero breaking changes: all callers use `SkillEngine` unchanged

**Negative:**

- Three files instead of one (`_skill_registry.py`, `_skill_executor.py`, `skills.py`)
- `_REGISTRY` must stay in `skills.py` to avoid circular imports (see ADR-005)

**Files:**

- `packages/core/providence_runtime/src/providence_runtime/_skill_registry.py`
- `packages/core/providence_runtime/src/providence_runtime/_skill_executor.py`
- `packages/core/providence_runtime/src/providence_runtime/skills.py`
- `packages/core/providence_runtime/tests/test_skill_registry.py`
- `packages/core/providence_runtime/tests/test_skill_executor.py`
