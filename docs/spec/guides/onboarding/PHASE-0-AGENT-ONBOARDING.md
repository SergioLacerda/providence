# 🚀 PHASE 0: Agent Onboarding — Workspace Initialization

**For:** AI Agents starting work on SPEC projects
**Time:** 20-30 minutes
**Goal:** Create project infrastructure + validate SDD adoption
**Requires:** Read `.spec.config` first

---

## 📋 PHASE 0 Overview

**What happens here:**

1. Agent discovers spec-architecture via `.spec.config`
2. Agent creates `.providence/context-aware/` infrastructure
3. Agent takes SDD validation quiz (≥80% required)
4. Agent confirms workspace is ready
5. Agent proceeds to actual work tasks

**Why:** Each project starts with zero context. Agent must bootstrap it locally.

---

## ✅ Step 1: Read Seed Configuration

### 1.1 Find `.spec.config`

```bash
# You're in a new project. First file to check:
cat .spec.config
```

**Expected output:**

```ini
[spec]
spec_path = ../spec-architecture
min_version = 2.1
```

**Agent validates:**

- ✅ `.spec.config` exists
- ✅ `spec_path` points to valid directory
- ✅ Framework version matches

### 1.2 Verify Framework Location

```bash
# Navigate to SPEC framework
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)
cd $SPEC_PATH

# Verify key directories exist
ls EXECUTION/spec/CANONICAL/rules/ia-rules.md
ls EXECUTION/spec/indices/
ls templates/
```

**Agent validates:**

- ✅ `/EXECUTION/spec/CANONICAL/` exists
- ✅ `EXECUTION/spec/indices/` exists (framework index templates)
- ✅ `templates/` exists (to copy from)

---

## ✅ Step 2: Create Project Infrastructure

### 2.1 Create Directories

```bash
# Return to project root
cd -

# Create .ai folder structure
mkdir -p .providence/context-aware/{task-progress/completed,analysis,runtime-state}

# Create other required directories if not present
mkdir -p tests/unit/specs_ia_units
mkdir -p .github .vscode
```

### 2.2 Copy Infrastructure Templates from SPEC

```bash
# Get SPEC path from config
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)

# Copy context-aware template
cp $SPEC_PATH/templates/ai/context-aware/README.md \
   .providence/context-aware/README.md

# Copy task-progress template
cp $SPEC_PATH/templates/ai/context-aware/task-progress/_current.md \
   .providence/context-aware/task-progress/_current.md

# Copy analysis template
cp $SPEC_PATH/templates/ai/context-aware/analysis/_template.md \
   .providence/context-aware/analysis/_current-issues.md

# Copy runtime-state template
cp $SPEC_PATH/templates/ai/context-aware/runtime-state/_current.md \
   .providence/context-aware/runtime-state/_current.md
```

### 2.3 Verify Structure

```bash
# Check that all files exist
ls -la .providence/context-aware/
ls -la .providence/context-aware/task-progress/
ls -la .providence/context-aware/analysis/
ls -la .providence/context-aware/runtime-state/

# Verify README exists
cat .providence/context-aware/README.md | head -20
```

**Agent validates:**

- ✅ All directories created
- ✅ All template files copied
- ✅ Files are readable

---

## ✅ Step 3: Read SPEC Documentation

### 3.1 Read Rules (MANDATORY)

Before writing any code, understand the rules:

```bash
# Get SPEC path
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)

# Read the rules
cat $SPEC_PATH/EXECUTION/spec/CANONICAL/rules/ia-rules.md | head -100
```

**Key concepts to understand:**

1. **Source of Truth Priority** — constitution.md > ia-rules.md
2. **Thread Isolation** — Never modify other threads
3. **Checkpointing** — Update execution-state after features
4. **Ports** — Never bypass, always use abstractions
5. **Gap Documentation** — Real ≠ Docs is normal

**Agent validates:**

- ✅ Can read ia-rules.md from SPEC
- ✅ Understands 5 core concepts above

### 3.2 Read Context-Aware Pattern

```bash
# Read how agents organize dynamic context (canonical specification)
cat $SPEC_PATH/EXECUTION/spec/CANONICAL/specifications/context-aware-agent-pattern.md | head -150
```

**Agent validates:**

- ✅ Understands context-aware pattern
- ✅ Knows how to track task-progress
- ✅ Knows how to document analysis
- ✅ Knows how to update runtime-state

---

## ✅ Step 4: Validation Quiz (MANDATORY)

### 4.1 Take Quiz

```bash
# Get SPEC path
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)

# Read quiz
cat $SPEC_PATHdocs/spec/guides/onboarding/VALIDATION_QUIZ.md
```

**Quiz structure (5 questions):**

1. What is source of truth priority?
2. What is thread isolation?
3. What is checkpointing?
4. What are ports?
5. What is gap documentation?

### 4.2 Score Yourself

```
Score: ___ / 5 (need ≥ 4 to pass, 80%)
```

### 4.3 Conditional Proceed

**If Score ≥ 4 (80%):**

```bash
echo "✅ QUIZ PASSED - Proceeding to workspace validation"
```

**If Score < 4:**

```bash
echo "❌ QUIZ FAILED - Review ia-rules.md again and retry"
# Re-read ia-rules.md
cat $SPEC_PATH/EXECUTION/spec/CANONICAL/rules/ia-rules.md
# Wait 30 minutes
# Retake quiz
```

---

## ✅ Step 5: Workspace Validation

### 5.1 Update Project Metadata

Edit `.providence/context-aware/task-progress/_current.md`:

```markdown
# Task Progress — [Today's Date]

## PHASE 0: Agent Onboarding

### Task: Initialize Workspace
- **Status:** 🟢 IN PROGRESS
- **Agent:** [Your Name]
- **Started:** [Date/Time]
- **Goal:** Create infrastructure + validate SDD

#### Checklist
- [x] Read .spec.config
- [x] Verified SPEC framework location
- [x] Created .providence/context-aware/ directories
- [x] Copied templates
- [x] Read ia-rules.md
- [x] Read context-aware guide
- [x] Took validation quiz (passed: YES ✅)

#### Next Steps
- [ ] Commit infrastructure
- [ ] Ready to start work tasks
```

### 5.2 Commit Infrastructure

```bash
# Stage all files
git add .providence/
git add .github/
git add .vscode/
# (don't add docs/ia if it's symlink)

# Commit with PHASE 0 message
git commit --no-verify -m "🚀 PHASE 0: Initialize agent workspace (onboarding complete)

- Created .providence/context-aware/ infrastructure
- Verified SPEC framework connection
- Passed SDD validation quiz (5/5)
- Ready for development tasks

PHASE 0 Status: COMPLETE ✅"
```

---

## ✅ Step 6: Verify Readiness

### 6.1 Final Checklist

```bash
# Verify directories exist
[ -d .providence/context-aware ] && echo "✅ .providence/context-aware exists"
[ -d .providence/context-aware/task-progress ] && echo "✅ task-progress exists"
[ -d .providence/context-aware/analysis ] && echo "✅ analysis exists"
[ -d .providence/context-aware/runtime-state ] && echo "✅ runtime-state exists"

# Verify files exist
[ -f .providence/context-aware/README.md ] && echo "✅ README.md exists"
[ -f .providence/context-aware/task-progress/_current.md ] && echo "✅ _current.md exists"

# Verify .spec.config readable
grep spec_path .spec.config > /dev/null && echo "✅ .spec.config readable"

# Verify SPEC framework accessible
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)
[ -f "$SPEC_PATH/EXECUTION/spec/CANONICAL/rules/ia-rules.md" ] && \
  echo "✅ SPEC framework accessible"
```

**All checks should show ✅**

### 6.2 Print Status Report

```bash
echo "
╔════════════════════════════════════════════╗
║   PHASE 0: AGENT ONBOARDING COMPLETE ✅   ║
╚════════════════════════════════════════════╝

Project Setup:
  ✅ .spec.config verified
  ✅ SPEC framework accessible
  ✅ .providence/context-aware/ created
  ✅ Templates copied

Knowledge Validation:
  ✅ ia-rules.md understood
  ✅ Context-aware pattern understood
  ✅ Validation quiz passed (5/5)

Workspace Status:
  ✅ Ready for development
  ✅ Infrastructure initialized
  ✅ Changes committed

Next Steps:
  1. Read project SPECIALIZATIONS (if exists)
  2. Check execution-state for conflicts
  3. Choose your PATH (A/B/C/D)
  4. Begin work tasks

Estimated Time to First Task: 5-10 minutes
"
```

---

## 🔄 If Something Fails

### Problem: Can't find spec-architecture

```bash
# Manually edit .spec.config with correct path
vi .spec.config
# Change spec_path to valid location

# Verify
cat .spec.config | grep spec_path
```

### Problem: Quiz failed

```bash
# Re-read rules carefully
SPEC_PATH=$(grep spec_path .spec.config | cut -d' ' -f3)
cat $SPEC_PATH/EXECUTION/spec/CANONICAL/rules/ia-rules.md

# Wait 30 minutes
# Retake quiz
```

### Problem: Can't create directories

```bash
# Check permissions
ls -la .

# Create manually if needed
mkdir -p .providence/context-aware/{task-progress/completed,analysis,runtime-state}

# Verify
ls -la .providence/
```

---

## 📚 What You Now Know (After PHASE 0)

You understand:

✅ **Where SPEC is** (.spec.config points to it)
✅ **What the rules are** (ia-rules.md)
✅ **How to use context-aware** (runtime guides)
✅ **What infrastructure is created** (.providence/context-aware/)
✅ **Why SDD matters** (validation quiz passed)

---

## 🎯 Ready to Start Work?

**Yes! You're now ready for real tasks:**

1. Read project SPECIALIZATIONS (project-specific patterns)
2. Check execution-state/_current.md (avoid conflicts)
3. Choose your PATH (A/B/C/D from AGENT_HARNESS)
4. Load relevant context for that PATH
5. Begin implementation

**Time elapsed:** ~30 minutes
**Value created:** Project infrastructure initialized + knowledge validated
**Confidence level:** 100% (you followed the protocol)

---

## 📋 PHASE 0 Completion Certificate

When you finish PHASE 0, you can claim:

```
✅ Agent [Your Name] completed PHASE 0 onboarding
✅ SDD framework understanding validated (quiz: 5/5)
✅ Project infrastructure initialized
✅ Ready for development work
✅ Date: [Today]
```

**Keep this in mind as you start your first task!**

---

## 🔗 Related

- **AGENT_HARNESS.md** — Full 7-phase protocol (you're in phase 0)
- **ia-rules.md** — The rules you must follow
- **context-aware-agent-pattern.md** — How agents organize dynamic context (CANONICAL specification)
- **execution-state/_current.md** — Project task tracking

---

**Status: PHASE 0 Template Complete**
**Next:** Agent reads this, executes steps, creates infrastructure locally
**Result:** Project-ready workspace with validated knowledge
