# ✅ Bash Implementation

**Status:** Complete
**Shell:** Bash 4+
**Framework:** Pure shell (no dependencies)

---

## 🚀 Running the Tests

### Prerequisites

```bash
# Check bash version (need 4+)
bash --version

# Should output: GNU bash, version 4.x.x or higher
```

### INTEGRATION Flow Test

```bash
cd /home/sergio/dev/providence

# Make script executable
chmod +x tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh

# Run
bash tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh
```

**Expected Output:**
```
================================================================================
🚀 PHASE 5: INTEGRATION FLOW FUNCTIONAL TEST (Bash)
================================================================================
✅ Created test project: /tmp/integration_test_xxx

📋 TEST STEP 1: Setup Project Structure
  ✅ Created directory: .github/
  ✅ Created directory: .vscode/
  ✅ Created directory: .cursor/
  ✅ Created directory: scripts/
  ✅ Created directory: .providence/
  ✅ STEP 1 PASSED: All directories created

... (steps 2-5) ...

================================================================================
📊 TEST SUMMARY
================================================================================
✅ PASS: test_step_1
✅ PASS: test_step_2
✅ PASS: test_step_3
✅ PASS: test_step_4
✅ PASS: test_step_5

Total: 5/5 tests passed

✅ INTEGRATION FLOW: READY FOR PRODUCTION
```

### EXECUTION Flow Test

```bash
chmod +x tests/integration/phase_5_examples/examples/bash/test-execution-flow.sh
bash tests/integration/phase_5_examples/examples/bash/test-execution-flow.sh
```

**Expected Output:**
```
✅ EXECUTION FLOW: READY FOR PRODUCTION
```

---

## 📦 Dependencies

**Standard Unix tools only:**

- `bash` — 4+ (built-in on most systems)
- `mkdir` — Create directories (POSIX)
- `rm` — Remove files (POSIX)
- `grep` — Text search (POSIX)
- `mktemp` — Create temp files (POSIX)

**All available on:**
- macOS
- Linux (Ubuntu, Debian, Red Hat, etc.)
- Git Bash (Windows)
- WSL (Windows Subsystem for Linux)

---

## 🔧 Implementation Details

### Architecture

```bash
#!/bin/bash

# State variables
TEST_DIR=""
STEP_RESULTS=()

# Setup
setup_test_project() { ... }

# Cleanup (runs on exit)
cleanup() { ... }
trap cleanup EXIT

# Tests
test_step_1_setup() { ... }
test_step_2_templates() { ... }
# ... steps 3-5 ...

# Main runner
main() { ... }

# Entry point
main
exit $?
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `setup_test_project()` | Create temp directory |
| `cleanup()` | Remove temp directory |
| `test_step_1_setup()` | Test step 1 |
| `test_step_2_templates()` | Test step 2 |
| ... | ... |
| `main()` | Run all tests and report |

---

## 🧪 Testing Strategy

### Creating Directories

```bash
# Python: os.makedirs()
# JavaScript: fs.mkdirSync()
# Bash:
mkdir -p "$TEST_DIR/$d"
```

### Writing Files

```bash
# Python: f.write()
# JavaScript: fs.writeFileSync()
# Bash:
cat > "$file_path" << 'EOF'
[spec]
spec_path = ../providence
EOF
```

### Checking File Existence

```bash
# Python: os.path.exists()
# JavaScript: fs.existsSync()
# Bash:
if [ -f "$file_path" ]; then
  # File exists
fi
```

### Searching in Files

```bash
# Python: "text" in content
# JavaScript: content.includes("text")
# Bash:
if grep -q "spec_path" "$file_path"; then
  # Found
fi
```

### Storing Results

```bash
# Store pass/fail
STEP_RESULTS+=("1:PASS")
STEP_RESULTS+=("2:FAIL")

# Later, count results
for result in "${STEP_RESULTS[@]}"; do
  if [[ "$result" == *":PASS" ]]; then
    ((passed++))
  fi
done
```

### Color Output

```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}✅ Success${NC}"
echo -e "${RED}❌ Failed${NC}"
echo -e "${YELLOW}⚠️  Warning${NC}"
```

---

## 🎯 Quick Bash Reference

### String Operations

```bash
# Length
echo ${#string}

# Substring
echo ${string:0:5}

# Find and replace
echo ${string//old/new}

# Empty check
if [ -z "$var" ]; then echo "empty"; fi
```

### Array Operations

```bash
# Create array
ITEMS=("a" "b" "c")

# Loop
for item in "${ITEMS[@]}"; do
  echo "$item"
done

# Add to array
ITEMS+=("d")

# Length
echo ${#ITEMS[@]}
```

### File Operations

```bash
# File exists
[ -f "$file" ]

# Directory exists
[ -d "$dir" ]

# File readable
[ -r "$file" ]

# File writable
[ -w "$file" ]
```

### Control Flow

```bash
# If/else
if [ condition ]; then
  echo "yes"
else
  echo "no"
fi

# While loop
while [ condition ]; do
  echo "looping"
done

# Case statement
case "$var" in
  "value1") echo "one" ;;
  "value2") echo "two" ;;
esac
```

---

## 🐛 Troubleshooting

### "permission denied"

```
test-integration-flow.sh: Permission denied
```

**Solution:**
```bash
chmod +x tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh
bash tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh
```

### "command not found: mktemp"

```
command not found: mktemp
```

**Solution:** mktemp is standard on macOS/Linux. On Windows:
```bash
# Use Git Bash or WSL
# Or manually create temp dir:
TEST_DIR="/tmp/test_$$"
mkdir -p "$TEST_DIR"
```

### "bad substitution"

```
bad substitution
```

**Cause:** Using non-bash shell (e.g., sh, dash)

**Solution:**
```bash
# Force bash
bash test-integration-flow.sh

# Or check shebang
head -1 test-integration-flow.sh
# Should be: #!/bin/bash
```

### Colors not showing

```
# Output shows: \033[0;32m✅\033[0m instead of colored ✅
```

**Cause:** Terminal doesn't support color codes

**Solution:** Redirect to TTY or use `script` command:
```bash
bash test-integration-flow.sh | cat
# vs
bash test-integration-flow.sh  # directly in terminal
```

### Temp directory not cleaned up

```
# /tmp/ has leftover * directories
```

**Solution:**
```bash
# The script should auto-cleanup with trap
# If not, manually:
rm -rf /tmp/*
```

---

## 🚀 Advanced Usage

### Running from another script

```bash
# Source the script
source tests/integration/phase_5_examples/examples/bash/test-integration-flow.sh

# Call functions
setup_test_project
test_step_1_setup
cleanup
```

### Capturing output

```bash
# Redirect to file
bash test-integration-flow.sh > test_output.log 2>&1

# Pipe to another command
bash test-integration-flow.sh | grep "PASS"
```

### Running multiple times

```bash
#!/bin/bash
for i in {1..3}; do
  echo "Run $i:"
  bash test-integration-flow.sh
done
```

---

## 📊 Metrics

- **Test Count:** 2 (INTEGRATION + EXECUTION)
- **Sub-tests:** 5 + 7 = 12 total
- **Lines of Code:** ~250 total
- **Execution Time:** ~2 seconds
- **Dependencies:** 0 (standard Unix tools)

---

## 🔗 Related

- [../SPEC_INTEGRATION_FLOW.md](../SPEC_INTEGRATION_FLOW.md) — What to test
- [../SPEC_EXECUTION_FLOW.md](../SPEC_EXECUTION_FLOW.md) — What to test
- [../README.md](../README.md) — Phase 5 overview
- [../examples/README.md](../examples/README.md) — Other implementations

---

**Bash Implementation**
Framework-Agnostic Testing with Language-Specific Implementation
