# 📋 INTEGRATION FLOW SPECIFICATION

**What:** Define requirements for testing INTEGRATION flow
**Implementation:** Language/framework-agnostic
**Examples:** Python, JavaScript, Bash, Go (provided)

---

## 🎯 Test Purpose

Validate that the **5-step INTEGRATION onboarding process** works correctly.

The test should:
1. ✅ Create a **temporary test project** (isolated, doesn't modify framework)
2. ✅ Simulate the **5 INTEGRATION steps**
3. ✅ Verify each step **succeeds**
4. ✅ Report **pass/fail for each step**
5. ✅ Clean up after execution

---

## 📋 STEP 1: Setup Project Structure

### What to test:
Project can create required directories

### Requirements:
- [ ] Create directory: `.github/`
- [ ] Create directory: `.vscode/`
- [ ] Create directory: `.cursor/`
- [ ] Create directory: `scripts/`
- [ ] Create directory: `.providence/`

### Success criteria:
All 5 directories exist and are accessible

### Expected output:
```
✅ Created directory: .github/
✅ Created directory: .vscode/
✅ Created directory: .cursor/
✅ Created directory: scripts/
✅ Created directory: .providence/
✅ STEP 1 PASSED: All directories created
```

---

## 📋 STEP 2: Copy Templates

### What to test:
Templates exist in framework and can be located

### Requirements:
Verify these files exist in `packages/features/providence_integration/src/providence_integration/templates/`:
- [ ] `.spec.config`
- [ ] `.github/copilot-instructions.md`
- [ ] `.vscode/ai-rules.md`
- [ ] `.vscode/settings.json`
- [ ] `.cursor/rules/spec.mdc`
- [ ] `.providence/README.md`

### Success criteria:
All 6 template files found and readable

### Expected output:
```
✅ Template found: .spec.config
✅ Template found: .github/copilot-instructions.md
✅ Template found: .vscode/ai-rules.md
✅ Template found: .vscode/settings.json
✅ Template found: .cursor/rules/spec.mdc
✅ Template found: .providence/README.md
✅ STEP 2 PASSED: All templates present
```

---

## 📋 STEP 3: Configure .spec.config

### What to test:
`.spec.config` can be created and configured

### Requirements:
- [ ] Create `.spec.config` file in test project
- [ ] Write: `[spec]` section
- [ ] Write: `spec_path = ../providence` (or appropriate path)
- [ ] File is readable

### Success criteria:
File exists, contains `spec_path` key, and is properly formatted

### Expected output:
```
✅ .spec.config created and configured
✅ STEP 3 PASSED: .spec.config valid
```

---

## 📋 STEP 4: Run Validation

### What to test:
`.providence/` infrastructure directories can be created (PHASE 0 preparation)

### Requirements:
- [ ] Create directory: `.providence/context-aware/`
- [ ] Create directory: `.providence/runtime/`
- [ ] Directories are accessible

### Success criteria:
Both subdirectories created and accessible

### Expected output:
```
✅ Created: .providence/context-aware/
✅ Created: .providence/runtime/
✅ STEP 4 PASSED: Validation structure created
```

---

## 📋 STEP 5: Commit to Git

### What to test:
All files are ready for git commit

### Requirements:
- [ ] `.spec.config` exists
- [ ] `.github/copilot-instructions.md` exists (created in test)
- [ ] `.vscode/ai-rules.md` exists (created in test)
- [ ] `.providence/README.md` exists (created in test)

### Success criteria:
All 4 key files exist and are readable (ready to `git add`)

### Expected output:
```
✅ File ready to commit: .spec.config
✅ File ready to commit: .github/copilot-instructions.md
✅ File ready to commit: .vscode/ai-rules.md
✅ File ready to commit: .providence/README.md
✅ STEP 5 PASSED: All files ready for git commit
```

---

## 🎯 Overall Test Result

### Pass Criteria:
- All 5 steps pass ✅

### Expected Final Output:
```
✅ PASS: test_step_1_setup
✅ PASS: test_step_2_templates
✅ PASS: test_step_3_config
✅ PASS: test_step_4_validate
✅ PASS: test_step_5_commit

Total: 5/5 tests passed

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

### Fail Result:
```
❌ FAIL: test_step_X_name
   Reason: [specific error]

Total: N/5 tests passed

❌ INTEGRATION FLOW: ISSUES FOUND
```

---

## 🔧 Implementation Guidelines

### Cleanup:
- [ ] Test must clean up temporary directory after completion
- [ ] No modifications to actual framework
- [ ] No side effects

### Reporting:
- [ ] Report each step clearly
- [ ] Show pass/fail for each step
- [ ] Summary at end
- [ ] Exit code: 0 (all pass), 1 (any fail)

### Error Handling:
- [ ] Catch exceptions
- [ ] Report specific error (not just "failed")
- [ ] Continue testing other steps if possible

---

## 📝 Implementation in Your Language

Choose implementation based on your tech stack:

### Python
See: `examples/python/example_integration_flow.py`

### JavaScript/TypeScript
See: `examples/javascript/test-integration-flow.js`

### Bash/Shell
See: `examples/bash/test-integration-flow.sh`

### Go
See: `examples/go/test_integration_flow.go`

### Other
Follow the spec above with your language's idioms

---

**Framework-Agnóstic Testing**
Specification defines WHAT, implementation defines HOW
