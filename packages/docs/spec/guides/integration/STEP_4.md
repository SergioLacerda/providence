# ✅ STEP 4 — Validate Setup

**Goal:** Run validation script and verify SDD framework is working
**Duration:** 5 minutes
**Complexity:** Simple (run 1 script)
**Prerequisites:** Steps 1-3 complete

---

## 📍 Where Are You?

You have:

- ✅ Project directories created (Step 1)
- ✅ Template files copied (Step 2)
- ✅ `.spec.config` configured (Step 3)
- ❓ Need to validate everything works

You're about to:

- Run PHASE 0 validation script
- Create `.providence/` infrastructure
- Pass VALIDATION_QUIZ (basic knowledge check)
- Move to Step 5 (commit)

---

## 🚀 Run Validation

### From Your Project Directory

```bash
cd /path/to/your-project

# Run PHASE 0 setup
python $(grep spec_path .spec.config | cut -d' ' -f3)docs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

**Breaking down the command:**

```bash
# Part 1: Get the spec_path from .spec.config
$(grep spec_path .spec.config | cut -d' ' -f3)
# Returns: ../providence (or your absolute path)

# Part 2: Run the script
python [path-from-part-1]docs/spec/SCRIPTS/phase-0-agent-onboarding.py
# Results: Runs PHASE 0 setup
```

### Simplified Alternative

If the command above doesn't work:

```bash
# If providence is in sibling directory
python ../providencedocs/spec/SCRIPTS/phase-0-agent-onboarding.py

# Or if you know the full path
python /path/to/providencedocs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

---

## 📝 Expected Output

The script will:

1. **Verify Framework**

   ```
   ✅ Found providence at: [path]
   ✅ CANONICAL/ structure verified
   ✅ Framework integrity check: PASS
   ```

2. **Create Infrastructure**

   ```
   ✅ Creating .providence/context-aware/
   ✅ Creating .providence/runtime/
   ✅ Populating search indices...
   ```

3. **Run VALIDATION_QUIZ**

   ```
   VALIDATION_QUIZ: SDD Framework Knowledge (8 questions)
   Question 1/8: What is the main purpose of ports?
   > (provide answer)
   ```

4. **Result**

   ```
   ✅ Quiz passed (6/8 = 75%)
   ✅ Infrastructure ready
   ✅ Your project is integrated with SDD framework
   ```

---

## 🎓 VALIDATION_QUIZ Basics

The quiz tests your understanding of SDD principles.

**Example questions:**

- What is a PORT in hexagonal architecture?
- Name one of the 16 mandatory rules
- What does AGENT_HARNESS stand for?
- When should tests be written?
- What is thread isolation?

**How to answer:**

- Just type your answer and press `Enter`
- Short answers are fine (doesn't need to be perfect)
- Aim for ≥80% to pass (6 out of 8)
- If you fail, you can run again

**Tips:**

- Read `constitution.md` and `ia-rules.md` if stuck
- The framework is about governance and autonomy
- Tests are written during implementation (TDD)
- Ports separate layers from external dependencies

---

## ✅ Verify Infrastructure Created

After the script finishes, verify `.providence/` was created:

```bash
# Check .providence/ exists
ls -la .providence/

# Should show:
# drwxr-xr-x  context-aware/
# drwxr-xr-x  runtime/
# -rw-r--r--  README.md
```

### Check Contents

```bash
# Verify context-aware/
ls .providence/context-aware/
# Should show: task-progress/, analysis/, runtime-state/

# Verify runtime/ (search indices)
ls .providence/runtime/
# Should show: search-keywords.md, spec-canonical-index.md, spec-guides-index.md, README.md

# Check file sizes
wc -l .providence/runtime/search-keywords.md
# Should show: 703 lines
```

---

## 🆘 Troubleshooting

### Issue: "Python not found"

```bash
# Python is not installed or not in PATH

# Solution: Install Python
# On macOS: brew install python3
# On Ubuntu: sudo apt install python3
# On Windows: Download from python.org

# Verify installation
python3 --version
# Should show: Python 3.8+

# Then use python3 instead of python
python3 $(grep spec_path .spec.config | cut -d' ' -f3)docs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

### Issue: ".spec.config not found"

```bash
# .spec.config wasn't copied or is in wrong location

# Check:
ls -la .spec.config

# If missing, copy it:
cp ../providence/INTEGRATION/templates/.spec.config .

# Then re-run validation
python $(grep spec_path .spec.config | cut -d' ' -f3)docs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

### Issue: "spec_path points to wrong location"

```bash
# .spec.config has wrong path

# Fix it:
nano .spec.config
# Edit: spec_path = ../providence

# Then re-run validation
python $(grep spec_path .spec.config | cut -d' ' -f3)docs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

### Issue: "VALIDATION_QUIZ score too low"

```bash
# You didn't pass (need ≥80%)

# This is OK! You can:
# 1. Read documentation and try again
# 2. Just press Ctrl+C to skip
# 3. Answer best you can (doesn't block progress)

# To try again later:
python ../providencedocs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

### Issue: Script Hangs or Never Completes

```bash
# Something is stuck (rare)

# Solution: Press Ctrl+C to cancel
# (Ctrl+C in terminal)

# Then:
1. Check if .providence/ was partially created
2. Delete .providence/ if corrupted: rm -rf .providence/
3. Run validation again

# If still stuck, check:
ls ../providencedocs/spec/SCRIPTS/
# Should show: phase-0-agent-onboarding.py
```

---

## 📊 After Validation

Once validation passes:

```bash
# Check git status
git status

# Should show new files (untracked):
# .providence/context-aware/
# .providence/runtime/
# (You'll commit these in Step 5)

# Preview what you'll commit
git add .
git status
# Should show green (staged for commit)

# Unstage (we'll do this in Step 5):
git reset
```

---

## ✅ Ready for Step 5?

Once validation passes, proceed to:

**→ [STEP_5.md](./STEP_5.md)**

Commit all changes to git.

---

## 🎉 What Was Created

By running PHASE 0 validation, you now have:

```
.providence/
├── context-aware/
│   ├── task-progress/        (for tracking tasks during development)
│   ├── analysis/              (for documenting decisions)
│   └── runtime-state/         (for persisting state)
├── runtime/
│   ├── README.md
│   ├── search-keywords.md     (703 lines - searchable doc index)
│   ├── spec-canonical-index.md
│   └── spec-guides-index.md
└── README.md                  (explains this directory)
```

Your developers will use these files during PHASE 0 (initial setup) and ongoing development.

---

**Estimated time:** 5 minutes
**Difficulty:** Simple
**Next step:** Commit to git
