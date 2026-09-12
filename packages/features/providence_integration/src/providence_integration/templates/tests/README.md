# 🧪 Test Templates — INTEGRATION

**Purpose:** Templates and examples for testing during project INTEGRATION

**Structure:**
```
INTEGRATION/templates/tests/
├── specs_ia_units/                     (Architecture Compliance Tests)
│   ├── test_layer_isolation_template.py
│   ├── test_port_contracts_template.py
│   ├── test_thread_isolation_template.py
│   └── __init__.py
│
└── phase_5_examples/                   (Phase 5 Functional Testing Examples)
    ├── README.md                        (How to implement)
    ├── SPEC_INTEGRATION_FLOW.md        (What to test - spec agnostic)
    ├── SPEC_EXECUTION_FLOW.md          (What to test - spec agnostic)
    ├── run_all_tests.sh                (Master runner)
    ├── test_*.py                       (Python reference implementation)
    └── examples/
        ├── python/                     (Python examples)
        ├── javascript/                 (JavaScript examples)
        └── bash/                       (Bash examples)
```

---

## 📋 specs_ia_units/ — Architecture Compliance

**What:** Verify framework rules and patterns

**When to use:** Copy these templates during PHASE 0 (Step 7)

**How:**
```bash
# During INTEGRATION:
cp INTEGRATION/templates/tests/unit/specs_ia_units/*.py \
   your-project/tests/unit/specs_ia_units/

# Edit files: replace [project_name] with your package
pytest tests/unit/specs_ia_units/ -v
```

**Includes:**
- ✅ Layer isolation validation
- ✅ Port contract compliance
- ✅ Thread isolation checks

---

## 📋 phase_5_examples/ — Functional Testing

**What:** Language-specific examples for Phase 5 functional testing

**When to use:** Reference during project development (Phase 5)

**Structure:**
- `SPEC_INTEGRATION_FLOW.md` — Framework-agnostic (what to test)
- `SPEC_EXECUTION_FLOW.md` — Framework-agnostic (what to test)
- `examples/python/` — Reference Python implementation
- `examples/javascript/` — JavaScript implementation
- `examples/bash/` — Bash implementation

**How:**
```bash
# Reference for your language
cat INTEGRATION/templates/tests/phase_5_examples/examples/python/

# Implement in your language following SPEC documents
cat INTEGRATION/templates/tests/phase_5_examples/SPEC_INTEGRATION_FLOW.md
cat INTEGRATION/templates/tests/phase_5_examples/SPEC_EXECUTION_FLOW.md
```

---

## 🚀 Usage in INTEGRATION Flow

### Step 1: Architecture Tests (PHASE 0)
```bash
cp -r INTEGRATION/templates/tests/unit/specs_ia_units/ \
      your-project/tests/

# Edit templates
# Run: pytest tests/unit/specs_ia_units/ -v
```

### Step 2: Functional Tests (PHASE 5)
```bash
# Reference Phase 5 examples
cat INTEGRATION/templates/tests/phase_5_examples/README.md

# Implement for your project (language-specific)
# Use examples as reference
```

---

## ✅ Checklist

- [ ] Architecture tests copied and customized (Step 1)
- [ ] Specs-ia-units tests passing
- [ ] Phase 5 tests implemented (language-specific)
- [ ] Functional tests passing
- [ ] All tests in CI/CD pipeline

---

**Authority:** [Context Management Standards](../../../../../docs/spec/reference/templates/CONTEXT_MANAGEMENT_STANDARDS.md)
**Status:** INTEGRATION Template Directory
**Updated:** April 19, 2026
