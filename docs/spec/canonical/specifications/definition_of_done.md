# ✅ DEFINITION OF DONE — Merge Validation Checklist

**Version:** 1.0
**Status:** MANDATORY — Use this for every merge
**Purpose:** Single source of truth for "Is this ready?"

---

# 🎯 WHAT THIS IS

This is the COMPLETE validation checklist before code is merged.

It consolidates requirements from:

- [Testing Specification](./testing.md)
- [Architecture Specification](./architecture.md)
- [Core Rules](../core/rules/)
- [Mandates & Policies](../core/)

---

# 📋 CHECKLIST: ARCHITECTURE COMPLIANCE

Before merge, verify:

## Layer Boundaries

- [ ] Domain layer contains NO external dependencies
- [ ] Domain layer contains NO async/await
- [ ] Domain classes represent pure business rules
- [ ] Application layer contains only orchestration logic
- [ ] Application layer does NOT contain infrastructure details
- [ ] Infrastructure layer contains port implementations only
- [ ] Infrastructure layer does NOT expose domain concepts
- [ ] Interfaces layer contains only entry points (routes, CLI, etc.)
- [ ] Interfaces layer does NOT contain business logic

## Port & Adapter Pattern

- [ ] All external dependencies go through Ports
- [ ] Ports defined in `application/ports/`
- [ ] Adapters implement Ports in `infrastructure/adapters/`
- [ ] No direct imports of adapters in domain/application
- [ ] No direct imports of infrastructure in domain
- [ ] Port names follow convention: `<Entity>RepositoryPort` or `<Entity>ServicePort`
- [ ] Adapter names follow convention: `<Technology><Entity>Adapter`

## Async Rules

- [ ] All I/O operations are async
- [ ] All Port methods are async
- [ ] All UseCase methods are async
- [ ] All Adapter methods are async
- [ ] No blocking operations in code
- [ ] All `async def` methods use `await` for async calls
- [ ] No `asyncio.run()` in application code
- [ ] No `time.sleep()` in application code

## Storage & Vector Index

- [ ] Storage Ports abstract data persistence
- [ ] Vector index accessed only through VectorIndexPort
- [ ] No direct ChromaDB calls outside port
- [ ] Storage is NOT source of truth (JSON is source of truth)
- [ ] Vector index is treated as BLACK BOX (never couple to implementation)
- [ ] Error handling maps infra errors to domain errors

---

# 🧪 CHECKLIST: TESTING COMPLIANCE

Before merge, verify:

## Domain Layer Tests

- [ ] All domain tests are UNIT tests
- [ ] Domain tests use ZERO mocks
- [ ] Domain tests are pure functions (deterministic)
- [ ] Domain tests have ZERO external dependencies
- [ ] All domain edge cases are tested
- [ ] Domain tests run in <100ms

**Example:**

```python
def test_player_gains_experience():
    player = Player(id="p1", xp=100)
    player.gain_xp(50)
    assert player.xp == 150  # Pure function, no mocks
```

## UseCase Layer Tests

- [ ] UseCase tests mock ONLY Ports
- [ ] UseCase tests do NOT mock Adapters
- [ ] UseCase tests do NOT call real infrastructure
- [ ] UseCase tests verify behavior via mocked ports
- [ ] UseCase tests validate error handling
- [ ] UseCase tests validate async/await properly
- [ ] Mock port behavior reflects actual port contracts

**Example:**

```python
async def test_get_player():
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = Player(id="p1")
    usecase = GetPlayerUseCase(repository=mock_repo)

    result = await usecase.execute("p1")

    assert result.id == "p1"
    mock_repo.get_by_id.assert_called_once_with("p1")
```

## Adapter Layer Tests

- [ ] Adapter tests use REAL backends (or test containers)
- [ ] Adapter tests do NOT mock Port interfaces
- [ ] Adapter tests verify actual I/O behavior
- [ ] Adapter tests clean up resources properly
- [ ] Adapter tests handle errors correctly

**Example:**

```python
async def test_json_adapter_saves_player(tmp_path):
    adapter = JsonPlayerAdapter(storage_path=tmp_path)
    player = Player(id="p1", name="Hero")

    await adapter.save(player)

    saved = await adapter.get_by_id("p1")
    assert saved.name == "Hero"
```

## Interface Layer Tests

- [ ] Interface tests mock ONLY UseCases
- [ ] Interface tests do NOT call real infrastructure
- [ ] Interface tests validate HTTP/CLI behavior
- [ ] Interface tests verify error responses
- [ ] Interface tests validate input validation

**Example:**

```python
async def test_get_player_route(client, mock_usecase):
    mock_usecase.execute.return_value = Player(id="p1")

    response = await client.get("/players/p1")

    assert response.status_code == 200
```

## General Testing Rules

- [ ] All tests are deterministic (same input = same output)
- [ ] All tests are isolated (no shared state between tests)
- [ ] All tests are readable (clear test names, clear assertions)
- [ ] Test file organization matches code organization
- [ ] Test names follow convention: `test_<action>_<context>_<expected>`
- [ ] All async tests properly await coroutines
- [ ] No ignored tests (no `@skip` or `@pytest.mark.skip`)
- [ ] Test coverage is reasonable (>80% for business logic)

## Anti-Patterns to Avoid

- [ ] ❌ No real LLM calls in tests
- [ ] ❌ No real database writes during tests
- [ ] ❌ No real network calls during tests
- [ ] ❌ No tests that depend on execution order
- [ ] ❌ No tests that depend on external state
- [ ] ❌ No test-specific flags in production code
- [ ] ❌ No modifications of production code to satisfy tests
- [ ] ❌ No mocking of concrete adapters (mock ports only)

---

# 📝 CHECKLIST: CODE QUALITY

Before merge, verify:

## Naming Conventions

- [ ] Classes follow naming convention: `<Concept><Type>` (e.g., `PlayerRepository`)
- [ ] UseCase names follow convention: `<Action><Entity>UseCase` (e.g., `GetPlayerUseCase`)
- [ ] Port names follow convention: `<Entity><Operation>Port` (e.g., `PlayerRepositoryPort`)
- [ ] Adapter names follow convention: `<Technology><Entity>Adapter` (e.g., `JsonPlayerAdapter`)
- [ ] Method names are verbs (get, save, update, delete, etc.)
- [ ] Boolean properties start with `is_` or `has_`
- [ ] Constants are UPPER_CASE
- [ ] Private methods/attributes start with `_`

## Documentation

- [ ] All public classes have docstrings
- [ ] All public methods have docstrings
- [ ] Docstrings explain PURPOSE, not implementation
- [ ] Complex logic has inline comments
- [ ] Ports have clear contract documentation
- [ ] Error conditions are documented

## Error Handling

- [ ] All infra errors are caught and mapped to domain errors
- [ ] No bare `except` clauses
- [ ] All expected errors are tested
- [ ] Error messages are descriptive
- [ ] Errors flow from infra → application → domain

## Type Hints

- [ ] All function parameters have type hints
- [ ] All function returns have type hints
- [ ] All class attributes have type hints
- [ ] Async functions properly type `Awaitable` or async return
- [ ] No `Any` types without justification

## Imports

- [ ] No circular imports
- [ ] Imports follow layer hierarchy (domain never imports from application/infra)
- [ ] No unused imports
- [ ] Imports organized: stdlib → third-party → local
- [ ] No wildcard imports

## No Test-Specific Code

- [ ] ❌ No `if TEST_MODE:` in production code
- [ ] ❌ No `if is_test():` in production code
- [ ] ❌ No conditional logic based on test environment
- [ ] ❌ No test-only attributes or methods
- [ ] ❌ No `pytest.mark.skipif` for missing implementation

**Verification:** Scan with:

```bash
grep -r "TEST_MODE\|is_test\|test_flag" src/
```

Result should be EMPTY.

---

# 🧬 CHECKLIST: FUNCTIONALITY

Before merge, verify:

## All Tests Pass

- [ ] `pytest tests/unit/` passes
- [ ] `pytest tests/integration/` passes
- [ ] `pytest tests/architecture/` passes
- [ ] `pytest tests/quality/` passes
- [ ] No test failures
- [ ] No test warnings (unless intentional)

## Feature Complete

- [ ] All acceptance criteria met
- [ ] All happy paths tested
- [ ] All error paths tested
- [ ] Edge cases handled
- [ ] No TODOs or FIXMEs left in code

## Architecture Validation

- [ ] Import-linter passes: `python -m importlinter lint`
- [ ] Type checking passes: `mypy src/`
- [ ] Linting passes: `ruff check src/`
- [ ] No violations of layer boundaries

## Strict Auto-Fix Hygiene (Mandatory)

- [ ] `ruff check --fix .` executed when available
- [ ] Formatter executed when configured (`ruff format .` or `black .`)
- [ ] Re-run completed after auto-fix: `ruff check .` then `mypy .` then `pytest`
- [ ] If post-fix validation fails, delivery is BLOCKED

## Vector Index Specific

If using VectorIndexPort:

- [ ] VectorIndexPort is accessed through DI injection only
- [ ] No direct imports of ChromaDB in non-adapter code
- [ ] Vector operations tested through Port mocks
- [ ] Fallback behavior tested if index fails
- [ ] No coupling to vector index schema in domain/application

---

# 📊 CHECKLIST: DOCUMENTATION

Before merge, verify:

## Code Documentation

- [ ] New files added to documentation if appropriate
- [ ] Module docstring explains purpose
- [ ] Complex decisions documented with comments
- [ ] References to related specs where applicable

## Architecture Documentation

- [ ] If architecture changed, update `docs/ia/specs/_shared/architecture.md`
- [ ] If new layer introduced, update `docs/ia/specs/_shared/project-structure.md`
- [ ] If new pattern introduced, update `docs/ia/specs/_shared/design-decisions.md`

## Testing Documentation

- [ ] Test patterns documented if novel
- [ ] Test setup documented if complex
- [ ] Mock strategies documented if unusual

---

# 🔄 CHECKLIST: EXECUTION STATE

Before merge, verify:

## Update Runtime State

- [ ] `execution-state/_current.md` updated with completion summary (in `.providence/source/`)
- [ ] If complex: checkpoint created in `.providence/source/checkpoints/`
- [ ] Decisions documented
- [ ] Risks flagged
- [ ] "Next Actions" updated for next agent

---

# 📋 QUICK CHECKLIST (For Humans)

If you're pressed for time, verify AT MINIMUM:

- [ ] All tests pass
- [ ] No layer boundary violations
- [ ] No test-specific code in production
- [ ] All ports are async
- [ ] All infrastructure is behind ports
- [ ] Tests mock ports, not adapters
- [ ] Error handling maps errors correctly
- [ ] Code follows naming conventions
- [ ] Import-linter passes
- [ ] execution_state.md updated

---

# ⚠️ COMMON FAILURES

Watch out for:

1. **Async/await issues**
   - Problem: Tests don't `await` UseCase calls
   - Fix: Ensure all async calls are awaited

2. **Wrong mocking**
   - Problem: Tests mock adapters instead of ports
   - Fix: Mock only interfaces (ports), not implementations

3. **Test-specific code**
   - Problem: Production code has `if TEST_MODE:`
   - Fix: Remove all test-specific branches

4. **Layer violations**
   - Problem: Domain imports from infrastructure
   - Fix: Always go through ports

5. **Blocking I/O**
   - Problem: Adapter uses `open()` instead of async file I/O
   - Fix: Use async I/O throughout

6. **Missing tests**
   - Problem: Feature has no test coverage
   - Fix: Ensure all layers have tests

---

# ✅ SIGN-OFF

Before clicking "Merge":

```python
# Domain logic is pure
assert domain_layer_has_zero_external_deps()

# Application orchestrates ports
assert application_uses_only_ports()

# Infrastructure implements ports
assert infrastructure_implements_all_ports()

# Testing is correct
assert tests_mock_ports_not_adapters()
assert all_tests_pass()

# Code quality verified
assert import_linter_passes()
assert mypy_passes()
assert ruff_passes()

# Documentation updated
assert execution_state_updated()

# ✅ READY TO MERGE!
```

---

# 🎓 EXAMPLE: Complete Feature Validation

**Feature:** Add player experience points

**Validation Steps:**

1. **Architecture** ✅
   - [ ] Player in domain (no deps)
   - [ ] GetPlayerXPUseCase in application (uses ports)
   - [ ] JsonPlayerAdapter in infrastructure (implements port)
   - [ ] GET /players/:id/xp in interfaces (calls usecase)

2. **Testing** ✅
   - [ ] test_player_xp.py: Domain unit tests (no mocks)
   - [ ] test_get_player_xp_usecase.py: UseCase tests (mock port)
   - [ ] test_json_player_adapter.py: Adapter tests (real storage)
   - [ ] test_player_xp_route.py: Route tests (mock usecase)

3. **Code Quality** ✅
   - [ ] All async
   - [ ] Naming correct
   - [ ] Docstrings present
   - [ ] No test flags

4. **Validation** ✅
   - [ ] pytest passes
   - [ ] import-linter passes
   - [ ] mypy passes
   - [ ] execution_state.md updated

**Result:** ✅ Ready to merge!

---

# 📞 QUESTIONS?

If you're unsure about ANY checkbox:

1. See [Testing Specification](./testing.md) (testing details)
2. See [Architecture Specification](./architecture.md) (pattern details)
3. See [Core Rules](../core/rules/) (naming/style details)
4. See [Mandates & Policies](../core/) (execution rules)

---

# 🚀 FINAL WORD

This checklist looks long, but it's checking ONE thing:

**"Is this code high-quality, well-tested, and architecturally sound?"**

If you follow this checklist, the answer is always YES. ✅
