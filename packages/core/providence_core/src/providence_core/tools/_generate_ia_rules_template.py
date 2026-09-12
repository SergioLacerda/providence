from __future__ import annotations

from typing import Any


def generate_ia_rules_specialization(config: dict[str, Any]) -> str:
    project = config["PROJECT_NAME"]
    ports = config.get("PRIMARY_PORTS", ["StoragePort", "LLMPort"])
    threads = config.get("CONCURRENT_THREADS", ["WorkerThread"])
    return f"""# IA-FIRST Execution Rules — {project} Specialization

**Project:** {project}
**Version:** 1.0
**Generated:** {config.get("GENERATED_AT", "2026-04-19")}
**Based on:** /docs/ia/CANONICAL/rules/ia-rules.md

---

## 📋 Overview

This document specifies the 16 execution protocols from CANONICAL adapted for {project}.

**Critical ports:** {", ".join(ports) if isinstance(ports, list) else ports}
**Concurrent threads:** {", ".join(threads) if isinstance(threads, list) else threads}
**Max parallel work:** {config.get("MAX_CONCURRENT_THREADS", "4")} threads

---

## ✅ Protocol Specializations (16 Total)

### Protocol 1: Read CANONICAL Rules First

**Generic:** "Every agent session starts by reading ia-rules.md"

**{project} requirement:**
```
Every agent session MUST:
  1. Read: /docs/ia/CANONICAL/rules/ia-rules.md (5 min)
  2. Read: /docs/ia/CANONICAL/rules/constitution.md (5 min)
  3. Read: /docs/ia/custom/{project}/SPECIALIZATIONS/ia-rules-{project}-specific.md (3 min)
  4. Choose task PATH: A/B/C/D from QUICK_START.md

Result: Agent understands both generic and {project}-specific rules
Time: ~15 min before starting work
```

---

### Protocol 2-16: [Additional Protocols]

[Each protocol would follow similar specialization pattern...]

---

## 🔗 References

- Generic rules: [CANONICAL/rules/ia-rules.md](../../CANONICAL/rules/ia-rules.md)
- Constitutional specialization: [constitution-{project}-specific.md](./constitution-{project}-specific.md)
- Configuration: [SPECIALIZATIONS_CONFIG.md](./SPECIALIZATIONS_CONFIG.md)

"""
