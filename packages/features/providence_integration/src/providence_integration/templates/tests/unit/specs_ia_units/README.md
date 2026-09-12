"""
Sergio-Driven Development (SDD) Compliance Tests — Architecture Validation

This folder contains tests that validate your project's compliance with SPEC architecture principles.

## Purpose

These tests ensure:
✅ Layer isolation (domain doesn't import infrastructure)
✅ Port abstraction (infrastructure only via ports)
✅ Thread isolation (concurrent work doesn't interfere)
✅ SPEC specialization compliance (project-specific rules)
✅ Architecture contract satisfaction (domain contracts)

## Key Difference from Unit Tests

| Aspect | Unit Tests | SDD Tests (specs_ia_units) |
|--------|-----------|---------------------------|
| What | Single function/class works | Architecture follows SPEC |
| Where | tests/unit/ | tests/unit/specs_ia_units/ |
| Frequency | Every change | Before commit |
| Scope | Business logic | Architectural rules |
| Failure | Bug in feature | Violation of architecture |

## What Belongs Here

### ✅ INCLUDE
- Layer isolation tests
- Port contract validation
- Thread isolation checks
- Architecture pattern compliance
- Domain purity verification
- Infrastructure abstraction validation

### ❌ EXCLUDE
- Business logic tests (go in tests/unit/)
- Integration tests (go in tests/integration/)
- Performance tests (go in tests/performance/)
- UI tests (go in tests/ui/)

## Running Tests

```bash
# All SDD compliance tests
pytest tests/unit/specs_ia_units/ -v

# Specific test category
pytest tests/unit/specs_ia_units/test_layer_isolation.py -v

# With coverage
pytest tests/unit/specs_ia_units/ --cov=src --cov-report=html

# Before commit (must pass)
pytest tests/unit/specs_ia_units/ -v --tb=short
```

## Mandatory Requirements

Before your PR can merge:

- [ ] All layer isolation tests passing
- [ ] All port contract tests passing
- [ ] All thread isolation tests passing
- [ ] Specialization compliance verified
- [ ] Architecture contracts satisfied
- [ ] Coverage >= 80% for domain layer
- [ ] No infrastructure imports in domain

Run this command to verify:
```bash
pytest tests/unit/specs_ia_units/ -v && echo "✅ All SDD tests passed"
```

## Creating New Tests

If you discover a new architectural requirement:

1. **Identify category:** isolation / contracts / compliance / threads?
2. **Add test:** In appropriate file (or create new one)
3. **Run:** `pytest tests/unit/specs_ia_units/ -v`
4. **Include in PR:** Add test + feature together

Example:

```python
# In test_layer_isolation.py (or new file)

def test_runtime_layer_respects_ports(self):
    \"\"\"Runtime should never import infrastructure directly.\"\"\"
    runtime_files = Path("src/runtime").rglob("*.py")

    for file in runtime_files:
        content = file.read_text()
        assert "from src.infrastructure" not in content, \
            f"{file}: runtime imports infrastructure"
```

## Related Documentation

- **Architecture spec:** Read `docs/ia/CANONICAL/specifications/architecture.md`
- **Ports & adapters:** Read `docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md`
- **Layer isolation:** Read `docs/ia/CANONICAL/specifications/architecture.md#layer-isolation`
- **Project specialization:** Read `docs/ia/custom/{project}/SPECIALIZATIONS/`

## Integration with CI/CD

These tests should run in GitHub Actions before merge:

```yaml
# In .github/workflows/ci.yml

- name: Validate SPEC Architecture
  run: pytest tests/unit/specs_ia_units/ -v --tb=short
```

## Monthly Review

Each month, review architecture compliance:

```bash
# Run with coverage report
pytest tests/unit/specs_ia_units/ -v --cov=src --cov-report=html

# Check report
open htmlcov/index.html

# Verify coverage >= 80% for domain
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Test fails: "domain imports infrastructure" | Move to application layer or use port |
| Test fails: "port has no adapter" | Create adapter in infrastructure |
| Test fails: "thread interference" | Isolate thread-local state |
| Test fails: "contract not satisfied" | Implement missing method |

## Standard Test Files

New projects should have:

- `test_layer_isolation.py` — Domain/App/Infrastructure boundaries
- `test_port_contracts.py` — Port implementations validated
- `test_thread_isolation.py` — Thread-safe modifications
- `test_specialization_compliance.py` — Project-specific rules
- `test_architecture_contracts.py` — Domain contracts

Start with layer isolation, add others as needed.

---

**Last Updated:** 2026-04-19
**SPEC Version:** 2.1
**Status:** Mandate Established
"""
