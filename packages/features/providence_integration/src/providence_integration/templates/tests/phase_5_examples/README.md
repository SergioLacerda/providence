# 🚀 Phase 5: Functional Testing (Framework-Agnostic)

**Purpose:** Validate both INTEGRATION and EXECUTION flows work end-to-end
**Location:** `/tests/integration/phase_5_examples/`
**Type:** Fake/mock tests (don't modify framework)
**Duration:** 10-15 minutes
**Philosophy:** Specs define WHAT to test; implementations show HOW in any language

---

## 📋 What is Phase 5?

Phase 5 runs functional tests to ensure both flows are production-ready:

- **INTEGRATION Flow Test:** Simulates creating a new project (5 steps)
- **EXECUTION Flow Test:** Validates framework documentation structure

Both tests are "fake" - they don't modify the actual framework, just verify it works.

### Key Feature: Framework-Agnostic

Tests are **not tied to a specific language or framework**:
- Specifications define requirements (WHAT to test)
- Implementations exist in Python, JavaScript, Bash, Go, etc.
- Add implementations in your language by following the spec

---

## 🚀 Quick Start

### Run Python Tests (Reference Implementation)

```bash
cd /home/sergio/dev/providence

# Run INTEGRATION flow test
python tests/integration/phase_5_examples/examples/python/example_integration_flow.py

# Run EXECUTION flow test
python tests/integration/phase_5_examples/examples/python/example_execution_flow.py

# Or run both
bash tests/integration/phase_5_examples/run_all_tests.sh
```

### Run JavaScript Tests

```bash
cd /home/sergio/dev/providence

# Run INTEGRATION flow test
node tests/integration/phase_5_examples/examples/javascript/test-integration-flow.js

# Run EXECUTION flow test
node tests/integration/phase_5_examples/examples/javascript/test-execution-flow.js
```

### Run Bash Tests

```bash
cd /home/sergio/dev/providence

# Make scripts executable
chmod +x tests/integration/phase_5_examples/examples/bash/*.sh

# Run INTEGRATION flow test
bash tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh

# Run EXECUTION flow test
bash tests/integration/phase_5_examples/examples/bash/test-execution-flow.sh
```

### Run Tests in Your Language

See: [examples/README.md](./examples/README.md) for how to implement in Go, Rust, TypeScript, etc.

---

## 📊 Test Details

### Directory Structure

```
/tests/integration/phase_5_examples/
  ├── README.md                          # This file
  ├── SPEC_INTEGRATION_FLOW.md           # What to test (agnóstico)
  ├── SPEC_EXECUTION_FLOW.md             # What to test (agnóstico)
  ├── run_all_tests.sh                   # Master test runner (Python ref impl)
  │
  ├── examples/                          # Language-specific implementations
  │   ├── README.md                      # How to implement in your language
  │   ├── python/
  │   │   ├── test_integration_flow.py   # Python implementation
  │   │   └── test_execution_flow.py
  │   ├── javascript/
  │   │   ├── test-integration-flow.js   # Node.js implementation
  │   │   └── test-execution-flow.js
  │   ├── bash/
  │   │   ├── test-integration-flow.sh   # Bash implementation
  │   │   └── test-execution-flow.sh
  │   └── go/                            # Planned
  │       ├── test_integration_flow.go
  │       └── test_execution_flow.go
```

### Understanding the Structure

**Two Separate Concerns:**

1. **SPECS** (Framework-Agnostic)
   - `SPEC_INTEGRATION_FLOW.md` — What requirements each test must satisfy
   - `SPEC_EXECUTION_FLOW.md` — What requirements each test must satisfy
   - Language-independent: any language can implement these

2. **IMPLEMENTATIONS** (Language-Specific)
   - `examples/python/` — Python with unittest/pytest
   - `examples/javascript/` — Node.js
   - `examples/bash/` — Shell scripting
   - `examples/go/` — Go testing
   - Add your language here!

---

## 🌐 Framework-Agnostic Philosophy

### Why Specs + Implementations?

**Problem:** Every project uses different tech stacks.

- Python project → pytest
- Node project → Jest, Mocha, Vitest
- Go project → go test
- Rust project → Cargo test
- etc.

**Solution:** Separate WHAT from HOW

```
SPEC_INTEGRATION_FLOW.md
├─ "Test must create 5 directories"  ← WHAT (language-agnostic)
└─ (doesn't say how: mkdir, os.mkdir, fs.mkdirSync, etc.)

examples/python/example_integration_flow.py
└─ Uses os.makedirs() ← HOW (Python-specific)

examples/javascript/test-integration-flow.js
└─ Uses fs.mkdirSync() ← HOW (JavaScript-specific)

examples/bash/test-integration-flow.sh
└─ Uses mkdir -p ← HOW (Bash-specific)
```

### Rules

1. **Specs are immutable** — They define the contract
2. **Implementations vary** — Follow language idioms
3. **Output must match** — All implementations show same format
4. **Tests are equivalent** — All test the same requirements
5. **Easy to add languages** — Copy spec, write implementation

### Example

**What all implementations do (from spec):**
```
✅ Created directory: .github/
✅ Created directory: .vscode/
✅ Created directory: .cursor/
✅ Created directory: scripts/
✅ Created directory: .providence/
✅ STEP 1 PASSED: All directories created
```

**How Python does it:**
```python
for d in dirs:
    os.makedirs(os.path.join(self.test_dir, d), exist_ok=True)
```

**How JavaScript does it:**
```javascript
for (const d of dirs) {
    fs.mkdirSync(path.join(this.testDir, d), { recursive: true });
}
```

**How Bash does it:**
```bash
for d in "${dirs[@]}"; do
    mkdir -p "$TEST_DIR/$d"
done
```

**Result:** Same test, 3 different implementations, all follow the spec.

---

## 🧪 Test Details

### INTEGRATION Flow Test

Tests the 5-step INTEGRATION onboarding process:

1. **STEP 1:** Setup project structure
   - Creates: `.github/`, `.vscode/`, `.cursor/`, `scripts/`, `.providence/`

2. **STEP 2:** Copy templates
   - Validates: `INTEGRATION/templates/` has all 8 template files

3. **STEP 3:** Configure `.spec.config`
   - Creates: `.spec.config` with `spec_path` pointing to framework

4. **STEP 4:** Run validation
   - Creates: `.providence/context-aware/`, `.providence/runtime/`

5. **STEP 5:** Commit to git
   - Verifies: All files ready for `git add`

**Expected Result:**
```
✅ STEP 1: Setup structure - PASS
✅ STEP 2: Copy templates - PASS
✅ STEP 3: Configure .spec.config - PASS
✅ STEP 4: Run validation - PASS
✅ STEP 5: Commit to git - PASS

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

---

### EXECUTION Flow Test (`example_execution_flow.py`)

Tests the 7-phase EXECUTION workflow structure:

1. **Entry Points**
   - `README.md`, `_START_HERE.md`, `NAVIGATION.md`, `INDEX.md`

2. **CANONICAL Layer** (immutable authority)
   - Constitution, Rules, Conventions
   - ADRs (6+ decisions)
   - Specifications (definition-of-done, communication, etc.)

3. **Guides Layer** (operational)
   - Onboarding guides (11+ files)
   - Operational guides (5+ files)
   - Emergency procedures (6+ files)
   - Reference docs (FAQ, GLOSSARY, etc.)

4. **Runtime Layer** (search indices)
   - `search-keywords.md`
   - `spec-canonical-index.md`
   - `spec-guides-index.md`

5. **Custom Layer** (project-specific)
   - Project directories in `custom/`

6. **Markdown Links**
   - Validates link format in key files

7. **AI-First Design**
   - `.providence-index.md`, `README.md`, `.spec.config` at root

**Expected Result:**
```
✅ Entry Points - PASS
✅ CANONICAL Layer - PASS
✅ Guides Layer - PASS
✅ Runtime Layer - PASS
✅ Custom Layer - PASS
✅ Markdown Links - PASS
✅ AI-First Design - PASS

✅ EXECUTION FLOW: READY FOR PRODUCTION
```

---

## 🔍 Understanding Test Output

### Green Checkmarks ✅
Test passed - framework is good

### Red X ❌
Test failed - there's an issue

### Yellow Warning ⚠️
Optional component missing (not critical)

### Examples

```bash
# All good
✅ INTEGRATION FLOW: READY FOR PRODUCTION

# Needs attention
❌ Entry point missing: _START_HERE.md

# Optional warning
⚠️ FAQ.md (optional guide file)
```

---

## 🎯 Adding Your Language Implementation

### Quick Process

1. **Read the spec**
   - [SPEC_INTEGRATION_FLOW.md](./SPEC_INTEGRATION_FLOW.md)
   - [SPEC_EXECUTION_FLOW.md](./SPEC_EXECUTION_FLOW.md)

2. **Create folder**
   ```bash
   mkdir -p tests/integration/phase_5_examples/examples/go
   ```

3. **Implement in your language**
   - Follow spec requirements exactly
   - Use language idioms
   - Match output format

4. **Test it**
   ```bash
   go run tests/integration/phase_5_examples/examples/go/test_integration_flow.go
   ```

5. **Submit PR**
   - Include both test_integration_flow.* and test_execution_flow.*
   - Update examples/README.md with your language status

### Example: Adding Go

```bash
# Create files
touch tests/integration/phase_5_examples/examples/go/test_integration_flow.go
touch tests/integration/phase_5_examples/examples/go/test_execution_flow.go

# Implement following SPEC_INTEGRATION_FLOW.md and SPEC_EXECUTION_FLOW.md

# Test
go run tests/integration/phase_5_examples/examples/go/test_integration_flow.go

# Commit
git add tests/integration/phase_5_examples/examples/go/
git commit -m "feat: Add Phase 5 tests in Go"
```

See: [examples/README.md](./examples/README.md) for detailed instructions

---

## 📈 Pass Criteria

- **INTEGRATION Flow:** All 5 steps must pass (100%)
- **EXECUTION Flow:** 90%+ of checks must pass
  - All critical: entry points, CANONICAL layer, Guides, Runtime
  - Optional: some specification files may be missing

---

## 🔧 Manual Testing (Alternative)

If you prefer to test manually:

### INTEGRATION Flow Manual Test

```bash
# Create a test directory
mkdir /tmp/test-project
cd /tmp/test-project

# Follow INTEGRATION/CHECKLIST.md step-by-step
# - Step 1: Create directories
# - Step 2: Copy templates
# - Step 3: Edit .spec.config
# - Step 4: Run validation script
# - Step 5: Verify git staging

# Verify success
ls -la .spec.config .providence/context-aware/
```

### EXECUTION Flow Manual Test

```bash
# Start at EXECUTION entry point
cat EXECUTION/_START_HERE.md

# Follow a scenario (e.g., "New Developer")
# Verify you can navigate to key docs

# Test search keywords
grep "PHASE" EXECUTION/spec/runtime/search-keywords.md
```

---

## 📝 Test Results Log

After running tests, results are printed to console. To save them:

```bash
# Save INTEGRATION test results
python tests/integration/phase_5_examples/test_integration_flow.py | tee /tmp/integration_test.log

# Save EXECUTION test results
python tests/integration/phase_5_examples/test_execution_flow.py | tee /tmp/execution_test.log
```

---

## 🚀 Next: Phase 6

Once Phase 5 tests pass ✅:

1. Review test output
2. Fix any failures
3. Re-run tests until all pass
4. Proceed to Phase 6: Final Commit

---

## 🆘 Troubleshooting

### Test fails: "Entry point missing: _START_HERE.md"

**Solution:**
```bash
# Check if file exists
ls EXECUTION/_START_HERE.md

# If missing, it's a structural issue
# Review PHASE_3_4_COMPLETE.md for status
```

### Test fails: "Template not found"

**Solution:**
```bash
# Check INTEGRATION/templates/
ls -la INTEGRATION/templates/

# Verify .spec.config exists
ls INTEGRATION/templates/.spec.config
```

### Python ImportError

**Solution:**
```bash
# Make sure you're running from repo root
cd /home/sergio/dev/providence

# Check Python version (need 3.8+)
python3 --version
```

---

## 📊 Quality Gate

Phase 5 tests are your quality gate before deployment:

✅ Pass all tests → Framework is production-ready
❌ Failures → Fix issues, re-test

---

**Phase 5: Functional Testing**
Run tests • Review results • Fix issues • Proceed to Phase 6

Generated: April 19, 2026
