# 🎯 Feature Implementation Checklist

Version: 1.2
**Quick reference for agents implementing new features**

---

# 📖 START HERE

**First time implementing a feature?** Read [architecture.md](./architecture.md)

It provides the COMPLETE sequence with time estimates and links to each spec.

---

# ⚠️ EXECUTION AWARENESS (MANDATORY)

Before implementing any feature:

1. **Read:** `.providence/source/execution-state/_current.md` (in your project)
   - Check current focus, in-progress work, and "Next Actions"
   - Verify you're NOT conflicting with active threads

2. **If applicable:** Check `.providence/source/threads/` for active work
   - Do NOT touch other threads
   - Follow isolated thread's "Next Steps"

3. **After completion:** Update execution-state with:
   - Decisions taken
   - Risks flagged
   - Open questions
   - Next actions for subsequent work

---

# 🚀 BEFORE YOU CODE

## Step 0: Ask Clarifying Questions

- [ ] Is this modifying existing domain logic or adding new?
- [ ] Does it need to persist data?
- [ ] Does it interact with external services (LLM, DB, API)?
- [ ] Does it have user-facing endpoints?
- [ ] Is it async-capable?

---

# 📋 FEATURE ANATOMY CHECKLIST

## Layer 1: Define Domain Rules (`domain/`)

**When you need:** Business logic, entities, rules
**File naming:** `<plural>/<entity>.py`
**Example path:** `domain/narratives/narrative.py`

```python
# ✅ Domain entity - NO external dependencies
class Narrative:
    def __init__(self, id: str, content: str):
        self.id = id
        self.content = content

    def is_valid(self) -> bool:
        return len(self.content) > 0
```

**Checklist:**

- [ ] No imports from `application`, `infrastructure`, `interfaces`
- [ ] Only domain logic (business rules)
- [ ] Testable in isolation (no mocks)
- [ ] Type hints present
- [ ] Async-safe (no blocking I/O)

---

## Layer 2: Define Port/Contract (`application/ports/`)

**When you need:** To abstract infrastructure access
**File naming:** `<entity>_<operation>_port.py`
**Example path:** `application/ports/narrative_repository_port.py`

```python
# ✅ Protocol (abstract interface)
from typing import Protocol


class NarrativeRepositoryPort(Protocol):
    async def get(self, id: str) -> Narrative: ...
    async def save(self, narrative: Narrative) -> None: ...
```

**Checklist:**

- [ ] No implementation (only interface)
- [ ] Returns domain entities (or DTOs)
- [ ] All methods are `async`
- [ ] No business logic
- [ ] Clear documentation

---

## Layer 3: Create UseCase (`application/usecases/`)

**When you need:** To orchestrate business logic
**File naming:** `<verb><entity>_usecase.py`
**Example path:** `application/usecases/retrieve_narrative_usecase.py`

```python
# ✅ UseCase - orchestration only
class RetrieveNarrativeUseCase:
    def __init__(
        self,
        repository_port: NarrativeRepositoryPort,  # Port!
        llm_port: LLMServicePort,
    ):  # Port!
        self.repository = repository_port
        self.llm = llm_port

    async def execute(self, id: str) -> Narrative:
        narrative = await self.repository.get(id)
        # Orchestrate - don't implement logic here
        return narrative
```

**Checklist:**

- [ ] Named `<Verb><Entity>UseCase`
- [ ] Depends on Ports, NOT Adapters
- [ ] Single responsibility (one use case per class)
- [ ] All methods are `async`
- [ ] No domain imports (Ports abstract them)
- [ ] Constructor receives Ports (dependency injection)
- [ ] Has `execute()` method (execute pattern)

---

## Layer 4: Create Adapter (`infrastructure/adapters/`)

**When you need:** To implement a Port for a specific backend
**File naming:** `<technology><entity>_adapter.py`
**Example path:** `infrastructure/adapters/json_narrative_adapter.py`

```python
# ✅ Adapter - implements a Port
class JsonNarrativeAdapter(NarrativeRepositoryPort):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def get(self, id: str) -> Narrative:
        # Implementation using specific technology
        data = await self._read_json(id)
        return Narrative(**data)

    async def save(self, narrative: Narrative) -> None:
        await self._write_json(narrative.id, narrative.dict())
```

**Checklist:**

- [ ] Named `<Technology><Entity>Adapter`
- [ ] Implements Port protocol
- [ ] No domain logic (mapping only)
- [ ] All methods are `async`
- [ ] Specific to one backend technology
- [ ] Error handling maps to domain exceptions
- [ ] Can have multiple adapters for same Port ✅

---

## Layer 5: Handle Errors Across Layers (`domain/` → `application/` → `infrastructure/`)

**Key Rule:** Map errors DOWN the stack, NOT UP

**Error Flow:**

```
Infrastructure (ChromaDB error, File error, API error)
    ↓ [Map to Domain Error]
Application (UseCase catches, maps error)
    ↓ [Throw Domain Error]
Domain (Explicit domain exceptions)
    ↓ [Interface catches, converts to HTTP/Discord response]
```

### Domain Errors: Define Explicitly

```python
# ✅ Domain errors - represent business failures
class NarrativeNotFoundError(Exception):
    """Thrown when narrative doesn't exist."""

    pass


class InvalidNarrativeError(Exception):
    """Thrown when narrative violates business rules."""

    pass
```

**Checklist:**

- [ ] Errors named `<Noun>Error`
- [ ] Inherit from `Exception` or specific base
- [ ] Have docstrings explaining when thrown
- [ ] Specific (not generic `Exception`)

### Application Errors: Map Infrastructure Errors

```python
# ✅ UseCase catches infra errors, maps to domain
class RetrieveNarrativeUseCase:
    async def execute(self, id: str) -> Narrative:
        try:
            narrative = await self.repository.get(id)
        except FileNotFoundError:
            # Infra error → map to domain error
            raise NarrativeNotFoundError(f"Narrative {id} not found")

        return narrative
```

**Checklist:**

- [ ] Adapter methods may throw technical errors
- [ ] UseCase catches technical errors
- [ ] UseCase maps to domain errors
- [ ] Never let infra errors escape UseCase

### Interface Errors: Convert Domain Errors to Responses

```python
# ✅ Route catches domain errors, converts to response
@router.get("/{id}")
async def get_narrative(id: str):
    try:
        result = await executor.execute(RetrieveNarrativeUseCase, {"id": id})
        return NarrativeSchema.from_domain(result)
    except NarrativeNotFoundError:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    except InvalidNarrativeError:
        return JSONResponse(status_code=400, content={"error": "Invalid narrative"})
```

**Checklist:**

- [ ] Catches domain errors
- [ ] Converts to HTTP status codes (or Discord responses)
- [ ] Returns clear error messages
- [ ] No stack traces in response

### Adapter Errors: Be Explicit About Failure Modes

```python
# ✅ Adapter documents failure modes
class JsonNarrativeAdapter:
    """
    Failure modes:
    - FileNotFoundError: Storage file doesn't exist
    - JSONDecodeError: Storage corrupted
    - IOError: Permission denied
    """

    async def get(self, id: str) -> Narrative:
        try:
            data = await self._read_json()
            return Narrative(**data)
        except FileNotFoundError:
            # Re-raise as-is, let UseCase map to domain
            raise
        except json.JSONDecodeError:
            # Log infrastructure issue, re-raise
            logger.error("Corrupted storage")
            raise
```

**Checklist:**

- [ ] Docstring lists failure modes
- [ ] Technical errors propagate as-is
- [ ] No catching and hiding errors
- [ ] Logging for observability

### Error Handling Summary

| Layer | Responsibility |
|-------|-----------------|
| **Domain** | Define explicit error types |
| **Application** | Map infra errors → domain errors |
| **Infrastructure** | Raise technical errors (don't hide) |
| **Interface** | Convert domain errors → responses |

---

## Layer 6: Create Interface Endpoint (`interfaces/`)

**When you need:** User entry points (API, Discord, CLI)
**File naming:** Depends on interface type

### HTTP API (`interfaces/api/routes/`)

```python
# ✅ FastAPI route
router = APIRouter(prefix="/narratives")


@router.get("/{id}")
async def get_narrative(id: str, executor: ExecutorService = Depends()):
    result = await executor.execute(RetrieveNarrativeUseCase, {"id": id})
    return NarrativeSchema.from_domain(result)
```

**Checklist:**

- [ ] Input validated (Pydantic schema)
- [ ] Calls application layer only (never direct adapter)
- [ ] Maps to UseCase
- [ ] Maps domain output to API schema
- [ ] Error responses conform to spec

### Discord (`interfaces/discord/handlers/`)

```python
# ✅ Discord event handler
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    executor = app.resolve(ExecutorService)
    result = await executor.execute(RetrieveNarrativeUseCase, {"id": message.author.id})
```

**Checklist:**

- [ ] Async message handling
- [ ] Calls application layer
- [ ] Error responses to user
- [ ] Respects rate limits
- [ ] Logs interactions

---

## Layer 7: Create Command/Query DTO (`application/commands/` or `application/queries/`)

**When you need:** To define input contracts
**Example path:** `application/commands/retrieve_narrative_command.py`

```python
# ✅ Input DTO
@dataclass
class RetrieveNarrativeCommand:
    narrative_id: str
    include_metadata: bool = False
```

**Checklist:**

- [ ] All fields typed
- [ ] Validates constraints
- [ ] From interface layer inputs
- [ ] To UseCase inputs

---

## Layer 8: Create DI Module (`modules/`)

**When you need:** Wire dependencies together
**File naming:** `<feature>_module.py`
**Example path:** `modules/narrative_module.py`

```python
# ✅ Dependency Injection
class NarrativeModule:
    @staticmethod
    def build(container, ctx, services):
        # Resolve ports from container
        repository_port = container.resolve(NarrativeRepositoryPort)
        llm_port = container.resolve(LLMServicePort)

        # Create use case
        return RetrieveNarrativeUseCase(
            repository_port=repository_port,
            llm_port=llm_port,
        )
```

**Checklist:**

- [ ] One module per feature domain
- [ ] Builds complete usecase with dependencies
- [ ] Adapters resolved from container
- [ ] No hardcoding (use config)
- [ ] Testable (mocks via container)

---

# 🔀 COMMON PATTERNS

## Pattern 1: Simple CRUD Feature

```
✅ Create a narrative entry

domain/narratives/
├── narrative.py                 # Entity
└── narrative_id.py             # Value Object (ID)

application/
├── ports/
│   └── narrative_repository_port.py
├── usecases/
│   ├── create_narrative_usecase.py
│   ├── retrieve_narrative_usecase.py
│   └── update_narrative_usecase.py
└── commands/
    └── narrative_command.py

infrastructure/adapters/
├── json_narrative_adapter.py
├── chroma_narrative_adapter.py
└── postgres_narrative_adapter.py   # New tech? Add new adapter!

interfaces/
├── api/routes/
│   └── narrative_routes.py
└── discord/handlers/
    └── narrative_handler.py

modules/
└── narrative_module.py
```

---

## Pattern 2: Integration with External Service

```
✅ Integrate with LLM API

application/ports/
└── llm_service_port.py          # Abstraction

infrastructure/adapters/
├── openai_llm_adapter.py        # OpenAI impl
├── anthropic_llm_adapter.py     # Anthropic impl
└── mock_llm_adapter.py          # Testing impl

application/usecases/
└── generate_narrative_usecase.py # Uses port
```

---

## Pattern 3: Async Operation

```
✅ Everything async-safe

# ✅ All methods async
async def execute(...) -> Result:
    # Await all I/O
    data = await self.port.fetch()
    result = await self.process(data)
    await self.port.save(result)
    return result

# ❌ NEVER
def execute(...) -> Result:
    data = self.port.fetch()  # Blocking!
    return data
```

---

# ❌ ANTI-PATTERNS (FORBIDDEN)

| ❌ DON'T | ✅ DO INSTEAD |
|----------|-------------|
| Import adapter directly | Import Port, resolve Adapter via DI |
| Business logic in adapter | Map only, orchestrate in UseCase |
| Domain depends on everything | Domain depends on nothing |
| Blocking I/O in core layers | Always async/await |
| Hardcoded dependencies | Constructor injection + DI |
| Direct backend access in UseCase | Always through Ports |
| Skip error mapping | Map infra errors to domain errors |

---

# 🧪 TESTING CHECKLIST

**For detailed testing guidance:** See [testing.md](./testing.md)
**For testing validation rules:** See [testing.md](./testing.md)
**For testing clarification:** See [testing.md](./testing.md)

For each layer, ensure:

- [ ] **Domain:** Unit test (no mocks) — See testing.md "Domain Tests"
- [ ] **Port:** Mock tests in UseCase — See testing.md "UseCase Tests"
- [ ] **UseCase:** Integration test with mock ports — See testing.md "UseCase Tests"
- [ ] **Adapter:** Integration test with real backend (or stub) — See testing.md "Adapter Tests"
- [ ] **Interface:** E2E test via API/Discord — See testing.md "Interface Tests"
- [ ] **Errors:** Verify error mapping tested — See feature-checklist Layer 5

```python
# ✅ Test domain (no mocks)
def test_narrative_is_valid():
    narrative = Narrative(id="1", content="Story")
    assert narrative.is_valid()


# ✅ Test usecase (mock port)
async def test_retrieve_narrative():
    mock_port = MockNarrativeRepository()
    usecase = RetrieveNarrativeUseCase(mock_port)
    result = await usecase.execute("1")
    assert result.id == "1"


# ✅ Test adapter (real backend or stub)
async def test_json_adapter_saves():
    adapter = JsonNarrativeAdapter("/tmp/test.json")
    narrative = Narrative(id="1", content="Test")
    await adapter.save(narrative)
    retrieved = await adapter.get("1")
    assert retrieved.id == "1"
```

---

# 🚨 DECISION GATES

Before committing, ask:

1. **Is code in the right layer?**
   - [ ] Domain → no external deps
   - [ ] Application → orchestration only
   - [ ] Infrastructure → implements ports
   - [ ] Interface → entry points only

2. **Does it respect Ports & Adapters?**
   - [ ] Ports defined?
   - [ ] Adapter implements port?
   - [ ] No direct adapter usage?

3. **Is it async-safe?**
   - [ ] All I/O is `async`?
   - [ ] No blocking calls?
   - [ ] Proper `await` usage?

4. **Is it testable?**
   - [ ] Can mock external deps?
   - [ ] No test code in production?

5. **Is it documented?**
   - [ ] Docstrings present?
   - [ ] Type hints complete?

---

# 🔗 RELATED DOCUMENTS

- **[architecture.md](./architecture.md)** — START HERE! Complete sequence with time estimates
- **[definition_of_done.md](./definition_of_done.md)** — Merge validation checklist
- **[testing.md](./testing.md)** — Clarifies testing.md roles
- [Project Structure](./architecture.md) — Folder layout
- [Feature Template](./feature-checklist.md) — Complete example
- [Conventions](./communication.md) — Naming rules
- [Constitution](../core/rules/INDEX.md) — Non-negotiables
- [Testing Best Practices](./testing.md) — Testing strategies & patterns
- [Testing Strategy Spec](./testing.md) — Testing validation rules
- [Architecture](./architecture.md) — Layer responsibilities
- [Design Decisions](../../decisions/DECISIONS_APRIL_2026.md) — Architectural decisions record
