# 🌐 Phase 5 Testing — Framework-Agnostic Implementation

**Status:** Framework defines WHAT to test (specs)
**Flexibility:** Implement HOW in any language/framework
**Examples:** Python, JavaScript, Bash, Go (and more)

---

## 📋 Philosophy

### Separation of Concerns

```
SPEC (framework-agnostic)
  ↓
  ├── SPEC_INTEGRATION_FLOW.md (what to test)
  └── SPEC_EXECUTION_FLOW.md (what to test)
       ↓
    IMPLEMENTATIONS (language-specific)
       ├── python/test_*.py
       ├── javascript/test-*.js
       ├── bash/test-*.sh
       ├── go/test_*.go
       └── your_language/test_*
```

### Rules

✅ **DO:**
- Follow the spec exactly
- Test all requirements
- Report clear pass/fail
- Clean up after yourself
- Exit with code 0 (pass) or 1 (fail)

❌ **DON'T:**
- Modify the actual framework
- Skip cleanup
- Change test requirements
- Mix implementation details into spec
- Guess on pass/fail criteria

---

## 🚀 Running Examples

### Python (Reference Implementation)

```bash
cd /home/sergio/dev/providence

# Run INTEGRATION test
python3 tests/integration/phase_5_examples/examples/python/example_integration_flow.py

# Run EXECUTION test
python3 tests/integration/phase_5_examples/examples/python/example_execution_flow.py
```

### JavaScript/Node.js

```bash
cd /home/sergio/dev/providence

# Make sure Node.js 14+ is installed
node --version

# Run INTEGRATION test
node tests/integration/phase_5_examples/examples/javascript/test-integration-flow.js

# Run EXECUTION test
node tests/integration/phase_5_examples/examples/javascript/test-execution-flow.js
```

### Bash/Shell

```bash
cd /home/sergio/dev/providence

# Make scripts executable
chmod +x tests/integration/phase_5_examples/examples/bash/*.sh

# Run INTEGRATION test
bash tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh

# Run EXECUTION test
bash tests/integration/phase_5_examples/examples/bash/test-execution-flow.sh
```

### Go (Coming Soon)

```bash
cd /home/sergio/dev/providence

# Run INTEGRATION test
go run tests/integration/phase_5_examples/examples/go/test_integration_flow.go

# Run EXECUTION test
go run tests/integration/phase_5_examples/examples/go/test_execution_flow.go
```

---

## 🎯 Understanding the Specs

### SPEC_INTEGRATION_FLOW.md

**What it defines:**
- 5 steps that must be tested
- Requirements for each step
- Expected output format
- Pass/fail criteria
- Cleanup requirements

**What it doesn't specify:**
- Programming language
- Testing framework
- Assertion library
- How to create directories (use language idioms)

### SPEC_EXECUTION_FLOW.md

**What it defines:**
- 7 tests that must be run
- Requirements for each test
- File paths that must exist
- Expected output format
- Pass/fail criteria

**What it doesn't specify:**
- How to check file existence (language-specific)
- How to parse markdown (any parser is fine)
- How to format output (just match structure)

---

## 📝 Adding Your Own Implementation

### Step 1: Choose Your Language

Example: Go

### Step 2: Create the File

```bash
mkdir -p tests/integration/phase_5_examples/examples/go
touch tests/integration/phase_5_examples/examples/go/test_integration_flow.go
```

### Step 3: Read the Spec

Study `SPEC_INTEGRATION_FLOW.md` carefully:
- What are the 5 steps?
- What must each step check?
- What's the expected output?
- What's the pass/fail criteria?

### Step 4: Implement

Use your language's idioms:

```go
package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	fmt.Println("Testing STEP 1: Setup Project Structure")

	// Create directories
	dirs := []string{".github", ".vscode", ".cursor", "scripts", ".providence"}
	for _, d := range dirs {
		// Check spec: requirement is to create these directories
		if err := os.MkdirAll(filepath.Join(testDir, d), 0755); err != nil {
			fmt.Printf("❌ Failed to create %s\n", d)
			return
		}
		fmt.Printf("✅ Created directory: %s/\n", d)
	}

	fmt.Println("✅ STEP 1 PASSED")
}
```

### Step 5: Test Your Implementation

```bash
# Verify it runs without errors
go run tests/integration/phase_5_examples/examples/go/test_integration_flow.go

# Check output matches spec format
# Should show: ✅ Created directory: .github/ (etc.)
```

### Step 6: Document in README.md

Add to `tests/integration/phase_5_examples/examples/README.md`:

```markdown
### Go

Status: ✅ Complete

Run:
```bash
go run test_integration_flow.go
```
```

### Step 7: Commit

```bash
git add tests/integration/phase_5_examples/examples/go/
git commit -m "feat: Add Phase 5 tests in Go"
```

---

## 🔍 Comparing Implementations

All implementations should produce similar output:

### Python
```
✅ PASS: test_step_1_setup
✅ PASS: test_step_2_templates
✅ PASS: test_step_3_config
✅ PASS: test_step_4_validate
✅ PASS: test_step_5_commit

Total: 5/5 tests passed

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

### JavaScript
```
✅ PASS: test_step_1_setup
✅ PASS: test_step_2_templates
✅ PASS: test_step_3_config
✅ PASS: test_step_4_validate
✅ PASS: test_step_5_commit

Total: 5/5 tests passed

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

### Bash
```
✅ PASS: test_step_1
✅ PASS: test_step_2
✅ PASS: test_step_3
✅ PASS: test_step_4
✅ PASS: test_step_5

Total: 5/5 tests passed

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

**Notice:** Output format is consistent across languages.

---

## 🧪 Testing Multiple Languages Together

Create a master test runner:

```bash
#!/bin/bash
# Run all language implementations

cd tests/integration/phase_5_examples/examples

echo "Running Python tests..."
python3 python/example_integration_flow.py || exit 1

echo "Running JavaScript tests..."
node javascript/test-integration-flow.js || exit 1

echo "Running Bash tests..."
bash bash/test-integration-flow.sh || exit 1

echo "All language implementations passed!"
```

---

## 🎓 Best Practices

### 1. Follow the Spec Exactly

✅ Spec says: "Create directories: .github, .vscode, .cursor, scripts, .providence"
✅ Your implementation: Creates all 5 directories
✅ Output: Reports each creation

❌ **Wrong:** Skip .providence directory (not in spec)
❌ **Wrong:** Create extra directories (not in spec)

### 2. Match Output Format

Spec defines: `✅ STEP X PASSED`
Your output: Exactly matches that format

Different languages? Fine. Different format? Bad.

### 3. Cleanup is Mandatory

Every test must:
- Create temporary directory
- Run tests
- Clean up (delete temp directory)
- No side effects on framework

### 4. Exit Codes Matter

```bash
exit 0  # All tests passed
exit 1  # Some tests failed
```

CI/CD systems depend on this.

### 5. Make it Idiomatic

```python
# ✅ Good: Pythonic
import tempfile
import pathlib

with tempfile.TemporaryDirectory() as tmpdir:
    path = pathlib.Path(tmpdir) / ".github"
    path.mkdir()
```

```javascript
// ✅ Good: JavaScripty
const fs = require('fs');
const path = require('path');
const os = require('os');

fs.mkdirSync(path.join(os.tmpdir(), 'test'), { recursive: true });
```

```bash
# ✅ Good: Bash-y
TEST_DIR=$(mktemp -d)
mkdir -p "$TEST_DIR/.github"
rm -rf "$TEST_DIR"
```

---

## 📊 Status of Implementations

| Language | INTEGRATION | EXECUTION | Status |
|----------|------------|-----------|--------|
| Python | ✅ | ✅ | Complete |
| JavaScript | ✅ | 🔄 | In Progress |
| Bash | ✅ | 🔄 | In Progress |
| Go | 📋 | 📋 | Planned |
| TypeScript | 📋 | 📋 | Planned |
| Rust | 📋 | 📋 | Planned |

✅ = Complete
🔄 = In Progress
📋 = Planned

---

## 🚀 Contributing New Implementations

### Process

1. Choose language
2. Create folder: `examples/{language}/`
3. Create test files
4. Test locally
5. Submit PR

### Template for new implementation:

```bash
# Create directory
mkdir -p tests/integration/phase_5_examples/examples/rust

# Create files
touch tests/integration/phase_5_examples/examples/rust/test_integration_flow.rs
touch tests/integration/phase_5_examples/examples/rust/test_execution_flow.rs

# Add to examples/README.md
echo "### Rust" >> tests/integration/phase_5_examples/examples/README.md
echo "Status: ✅ Complete" >> tests/integration/phase_5_examples/examples/README.md

# Commit
git add tests/integration/phase_5_examples/examples/rust/
git commit -m "feat: Add Phase 5 tests in Rust"
```

---

## 📞 Questions?

See the main spec files:
- [SPEC_INTEGRATION_FLOW.md](./SPEC_INTEGRATION_FLOW.md)
- [SPEC_EXECUTION_FLOW.md](./SPEC_EXECUTION_FLOW.md)

Check examples in your language of choice.

---

**Framework-Agnóstic Testing**
Specs define WHAT, implementations show HOW
Choose your language, follow the spec
