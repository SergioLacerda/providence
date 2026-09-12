from __future__ import annotations

from typing import Any


def generate_constitution_specialization(config: dict[str, Any]) -> str:
    project = config["PROJECT_NAME"]
    entities = config.get("PRIMARY_DOMAIN_OBJECTS", "domain objects")
    max_concurrent = config.get("MAX_CONCURRENT_ENTITIES", "50+")
    team_size = config.get("TEAM_SIZE", "unknown")
    return f"""# Constitutional Principles — {project} Specialization

**Project:** {project}
**Version:** 1.0
**Generated:** {config.get("GENERATED_AT", "2026-04-19")}
**Based on:** /docs/ia/CANONICAL/rules/constitution.md

---

## 📋 Overview

This document maps the 15 generic constitutional principles from CANONICAL
to {project}-specific constraints and implementation guidelines.

**Team size:** {team_size} developers
**Scale:** {max_concurrent} concurrent entities
**Primary entities:** {", ".join(entities) if isinstance(entities, list) else entities}

---

## ✅ Principle Specializations

### 1. Single Responsibility Per Layer

**Generic:** Each layer must have exactly one reason to change

**{project} specialization:**
```
Domain Layer:
  ├─ Campaign entity (campaign lifecycle, state transitions)
  ├─ Encounter entity (encounter logic)
  ├─ Character entity (character state)
  └─ Narrative entity (narrative generation orchestration)

Application Layer:
  ├─ CreateCampaignUseCase
  ├─ UpdateCampaignUseCase
  ├─ GenerateNarrativeUseCase
  └─ RetrieveCampaignUseCase

Infrastructure Layer:
  ├─ PostgreSQL adapter (persistence)
  ├─ ChromaDB adapter (vector index)
  ├─ OpenAI adapter (LLM)
  └─ Blinker adapter (message bus)
```

**Constraint:** Each domain entity responsible for exactly one business concept
**Validation:** Mismatch detected by architecture tests → CI/CD failure

---

### 2. All Code is Async-First

**Generic:** No blocking operations (except bootstrap)

**{project} specialization:**
```
Async requirements:
  ✅ campaign_service.py — All methods async
  ✅ narrative_generator.py — All methods async
  ✅ vector_index_adapter.py — All methods async
  ✅ llm_adapter.py — All methods async

Allowed blocking:
  ✓ Bootstrap initialization (pyproject.toml: startup tasks)
  ✓ Test fixtures (conftest.py)
  ✓ Migration scripts (one-time operations)

Validation:** pytest detects sync functions in runtime code → FAIL
```

**Constraint:** Zero blocking I/O in production hot paths

---

### 3. Ports & Adapters Mandatory

**Generic:** Infrastructure never accessed directly

**{project} specialization:**
```
Mandatory ports:
  - StoragePort: all database access
  - VectorIndexPort: all embedding operations
  - LLMPort: all LLM interactions
  - MessageBusPort: all event distribution
  - ConfigPort: all configuration access

Example violation (FORBIDDEN):
  ❌ import chromadb; chromadb.search(...)
  ✅ self.vector_index_port.search(...)

Validation:** Import checker blocks chromadb, openai, psycopg2 in domain/
```

**Constraint:** 100% port usage, 0% direct infrastructure imports in domain/app

---

### 4. Data Model Authority

**Generic:** Domain entities are source of truth, not external systems

**{project} specialization:**
```
Source of truth:
  - Campaign state: Campaign entity (domain/)
  - Character stats: Character entity (domain/)
  - Narrative history: Narrative entity (domain/)
  - Embeddings: Derived from Narrative (ChromaDB is cache only)

Acceptable lag:
  - Campaign→Database: <100ms
  - Campaign→MessageBus: <50ms
  - Campaign→ChromaDB: <5 minutes (cache refresh)

Validation:** If ChromaDB and Campaign disagree: Campaign wins, ChromaDB recomputed
```

**Constraint:** Domain entities are immutable source of truth

---

### 5. Thread Isolation Mandatory

**Generic:** Each thread operates independently, no shared mutable state

**{project} specialization:**
```
Concurrent threads:
  - UpdateThread: polls for campaign changes
  - GenerationThread: generates narrative (calls LLM)
  - IndexThread: updates vector index
  - EventThread: distributes events via message bus

Isolation rules:
  - UpdateThread can ONLY write: Campaign
  - GenerationThread can ONLY write: Narrative
  - IndexThread can ONLY write: ChromaDB
  - No thread shares mutable state
"""
