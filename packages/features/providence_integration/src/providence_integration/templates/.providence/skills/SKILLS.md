# SDD Skills Registry

Available skills for governed execution.

## `compress-context` v1.0.0

**Category:** economy
**Risk:** low
**Status:** active

Reduce context footprint while preserving governance context.

**YAML:** `.providence/skills/compress-context/skill.yaml`

## `diagnose` v1.0.0

**Category:** analysis
**Risk:** low
**Status:** active

Diagnose runtime/workspace problems with governed checks.

**YAML:** `.providence/skills/diagnose/skill.yaml`

## `review-architecture` v1.0.0

**Category:** architecture
**Risk:** high
**Status:** active

Review architecture adherence against SDD mandates.

**YAML:** `.providence/skills/review-architecture/skill.yaml`

## `stabilize` v1.0.0

**Category:** operations
**Risk:** medium
**Status:** active

Run stabilization checks before handoff.

**YAML:** `.providence/skills/stabilize/skill.yaml`

## `validate-governance` v1.1.0

**Category:** governance
**Risk:** medium
**Status:** active

Validate governance integrity and runtime preflight.

**YAML:** `.providence/skills/validate-governance/skill.yaml`

---

## Using Skills

Load a skill via CLI:

```bash
sdd skill <name> --execute
```

Or programmatically:

```python
from sdd_runtime.skills import SkillEngine

engine = SkillEngine()
result = engine.run_skill("diagnose", execute=True)
```
