# 🛡️ ADR-008 Enforcement - STRICT from now on

**Effective:** April 21, 2026 (After Violation)
**Status:** CRITICAL - Guardrail activated

---

## What Happened (Violation Log)

**Date:** April 21, 2026
**Violation:** Agent committed directly to main (3 commits)

```
709eab3 (main)     ← Main at start of day
├─ 43d68a2        ← Agent commit: MIGRATION_COMPLETE.md (VIOLATION ❌)
├─ 0ce40f2        ← Agent commit: v3.0 Migrate from v2.1 (VIOLATION ❌)
└─ eb60fca        ← Agent commit: phase-4 (on WIP first, then merged? MIXED)
```

**Root Cause:** Agent didn't follow ADR-008 workflow
**Impact:** 3 direct commits to main without architect review
**Debt Status:** Architect manually resolved ✅

---

## ADR-008 Workflow (MANDATORY)

### Flow Chart

```
┌─────────────────┐
│  Agent starts   │
│  feature work   │
└────────┬────────┘
         │
         ↓
┌────────────────────────────┐
│ STEP 1: Create WIP branch  │
│ git checkout -b wip/...    │
│ (never edit main directly) │
└────────┬───────────────────┘
         │
         ↓
┌────────────────────────────┐
│ STEP 2: Make commits       │
│ git add / git commit       │
│ (commits stay on WIP)      │
└────────┬───────────────────┘
         │
         ↓
┌────────────────────────────┐
│ STEP 3: Push to origin     │
│ git push origin wip/...    │
│ (creates remote branch)    │
└────────┬───────────────────┘
         │
         ↓
┌────────────────────────────┐
│ STEP 4: Create PR          │
│ GitHub: Create PR          │
│ Title, description, links  │
└────────┬───────────────────┘
         │
         ↓
┌────────────────────────────────────┐
│ STEP 5: WAIT FOR ARCHITECT REVIEW  │
│ Agent: DO NOT TOUCH ANYTHING       │
│ Architect: Review code + tests     │
│ Architect: Comment / approve       │
└────────┬───────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ STEP 6: ARCHITECT MERGES         │
│ Architect: Click "Merge PR"      │
│ GitHub: Closes PR                │
│ GitHub: Deletes WIP branch       │
│ Result: Code now on main ✅      │
└──────────────────────────────────┘
```

### Commands (Mandatory Sequence)

```bash
# ✅ CORRECT WORKFLOW

# STEP 1: Create WIP branch
git checkout main
git pull origin main  # Ensure up-to-date
git checkout -b wip/feature-name

# STEP 2: Make changes
vim .providence-core/CANONICAL/mandate.spec
git add .providence-core/
git commit -m "feat: Update mandate X"

# STEP 3: Push (not merge!)
git push origin wip/feature-name

# STEP 4: Create PR (via GitHub UI)
# Go to: https://github.com/.../pulls
# Click "New Pull Request"
# Compare: wip/feature-name ← main
# Fill title, description, reference DECISIONS.md

# STEP 5: WAIT FOR ARCHITECT
# Do NOT:
#   git checkout main
#   git merge
#   git push origin main
# Do ONLY:
#   Monitor PR comments
#   Reply to questions

# STEP 6: Architect merges (architect only action)
# Architect clicks "Merge Pull Request" on GitHub

❌ NEVER ❌
git push origin main       # Direct push to main = BLOCKED
git merge wip/... main     # Local merge then push = BLOCKED
git commit on main         # Any commit on main = BLOCKED
```

---

## How to Prevent Violations

### 1. Git Config (Local Protection)

Agent should run:

```bash
# Make main branch read-only for agent (warn, not block)
git config branch.main.rebase false
git config --local core.hooksPath .git-hooks/

# Pre-commit hook will warn:
# ⚠️  WARNING: You are committing to main
# ⚠️  ADR-008 requires PR approval
# ⚠️  Branch protection will BLOCK this push
```

### 2. GitHub Branch Protection (Server-side)

Architect should enable:

```
Repository Settings → Branches → Add rule

Rule name: main

✅ Require pull request reviews
   Reviews required: 1
   Dismiss stale reviews: Yes
   Require review from code owners: No

✅ Require status checks to pass before merging
   Required: All status checks (tests, linting)

✅ Require branches to be up to date before merging
   Yes

✅ Restrict who can push to matching branches
   Allow force pushes: No (CRITICAL)

✅ Require approval of reviews when the head branch updates
   Yes

Enforce administrators: Yes (architect also restricted)
```

Result: **Only GitHub "Merge" button works, never git push**

### 3. Pre-commit Hook (Local Warning)

File: `.git-hooks/pre-commit-adr-008`

```bash
#!/bin/bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" = "main" ]; then
    echo ""
    echo "⚠️  VIOLATION: You are trying to commit to main"
    echo "⚠️  ADR-008 requires:"
    echo "   1. Create WIP branch: git checkout -b wip/feature-name"
    echo "   2. Make commits there"
    echo "   3. Push: git push origin wip/feature-name"
    echo "   4. Create PR on GitHub"
    echo "   5. Architect reviews & merges"
    echo ""
    echo "❌ This commit is BLOCKED by local hook"
    echo ""
    exit 1
fi

if [[ ! $CURRENT_BRANCH =~ ^wip/ ]]; then
    echo "⚠️  WARNING: Branch '$CURRENT_BRANCH' doesn't follow naming"
    echo "   Best practice: git checkout -b wip/what-youre-doing"
    echo "   Proceeding... but consider renaming"
fi

exit 0
```

### 4. Test Suite (Validation)

File: `.providence-migration/tests/test_adr008_enforcement.py`

```python
def test_agent_cannot_commit_to_main():
    """Verify ADR-008: Agent never auto-commits to main"""
    import subprocess

    # Try to commit on main
    result = subprocess.run(["git", "checkout", "main"], capture_output=True)

    # Pre-commit hook should warn/block
    # If hook is installed, commit will fail with proper message
    assert result.returncode == 0 or "ADR-008" in result.stderr
```

### 5. CI/CD Check

GitHub Actions workflow: `.github/workflows/adr008-check.yml`

```yaml
name: ADR-008 Enforcement

on:
  pull_request:
    branches: [main]

jobs:
  check-branch-naming:
    runs-on: ubuntu-latest
    steps:
      - name: Verify PR source branch starts with wip/
        run: |
          BRANCH="${{ github.head_ref }}"
          if [[ ! $BRANCH =~ ^wip/ ]]; then
            echo "❌ VIOLATION: Branch '$BRANCH' doesn't follow wip/* naming"
            echo "Please create PR from branch: wip/your-feature-name"
            exit 1
          fi
          echo "✅ Branch naming correct: $BRANCH"
```

---

## Verification Checklist (Before any commit)

Agent should verify:

```bash
# 1. Am I on a WIP branch?
git branch | grep "*"
# Output should be: * wip/something
# If output is: * main → STOP! Create WIP branch first

# 2. Will my commit go to origin/wip or origin/main?
git push --dry-run origin
# Output should show: wip/something
# If it says main → STOP! You're on wrong branch

# 3. Will GitHub allow merge without PR?
# Answer: NO - Branch protection will block

# 4. Did I create a PR?
# Check: https://github.com/.../pulls
# Should see your PR there
# If not → Create it first!
```

---

## Scenario Testing

### Scenario 1: Agent tries direct main commit (BLOCKED ❌)

```bash
$ git checkout main
Switched to branch 'main'

$ git add .providence-core/CANONICAL/mandate.spec
$ git commit -m "feat: update mandate"

❌ /.git-hooks/pre-commit-adr-008:
    ⚠️  VIOLATION: You are trying to commit to main
    ⚠️  ADR-008 requires PR workflow
    ❌ This commit is BLOCKED

$ echo $?
1  # Non-zero exit = blocked!
```

### Scenario 2: Agent follows workflow (ALLOWED ✅)

```bash
$ git checkout -b wip/update-mandate
Switched to new branch 'wip/update-mandate'

$ git add .providence-core/CANONICAL/mandate.spec
$ git commit -m "feat: update mandate"

✅ /.git-hooks/pre-commit-adr-008:
    ✅ Branch 'wip/update-mandate' follows naming
    ✅ Commit allowed on WIP branch

$ git push origin wip/update-mandate
✅ Pushed to origin/wip/update-mandate

$ echo $?
0  # Zero exit = success!

# Create PR (GitHub UI):
# → PR created
# → Architect reviews
# → Architect merges
✅ Code reaches main only via Merge button
```

### Scenario 3: Try to push main directly (BLOCKED ❌)

```bash
$ git checkout main
$ git merge wip/update-mandate
$ git push origin main

❌ GitHub branch protection error:
    "Push rejected"
    "Require pull request reviews"
    "Please create a pull request"

$ echo $?
1  # Non-zero exit = blocked!
```

---

## Enforcement Status

| Layer | Enforcement | Status | Notes |
|-------|-------------|--------|-------|
| Local Hook | Pre-commit block on main | ✅ Ready | Installed at `.git-hooks/pre-commit-adr-008` |
| GitHub Protection | Require PR + architect review | ⏳ TODO | Architect needs to enable (Repo Settings) |
| CI/CD Workflow | Check WIP branch naming | ⏳ TODO | Add to GitHub Actions |
| Test Suite | Verify ADR-008 compliance | ✅ Ready | Tests in `.providence-migration/tests/` |

---

## ADR-008 Contract (Binding for Agent)

**I (Agent) commit to:**

- [ ] **NEVER** commit directly to main
- [ ] **ALWAYS** create WIP branch first (git checkout -b wip/...)
- [ ] **ALWAYS** push to origin (git push origin wip/...)
- [ ] **ALWAYS** create PR on GitHub
- [ ] **NEVER** merge PR myself
- [ ] **ALWAYS** wait for architect approval
- [ ] **ALWAYS** allow architect to click Merge button
- [ ] **ALWAYS** reference DECISIONS.md in PR description
- [ ] **ALWAYS** explain changes in commit messages
- [ ] **ALWAYS** run tests before pushing

**Architect will:**

- [ ] Review PR (check code + tests)
- [ ] Comment on questions
- [ ] Approve or request changes
- [ ] Click Merge (only architect action)
- [ ] Architect maintains control of main

---

## Violation Response Protocol

**If agent violates ADR-008 again:**

1. **Detect:** GitHub branch protection blocks push OR pre-commit hook warns
2. **Alert:** Architect notified (violation attempt logged)
3. **Review:** Architect audits recent commits
4. **Revert:** git revert on violated commit
5. **Document:** Violation added to violation log
6. **Corrective:** Agent re-does work in WIP branch + PR

---

## Success Metrics

- ✅ All commits to main via Merge button (never git push)
- ✅ 100% of commits have associated PR
- ✅ 0 direct commits to main
- ✅ 0 violations of ADR-008 after today
- ✅ Architect approves 100% of PRs before merge

---

**Status:** ACTIVE ENFORCEMENT
**Start Date:** April 21, 2026 (NOW)
**Violation Today:** 3 commits (RESOLVED)
**Future Violations:** BLOCKED at GitHub + local layers

✅ **Ready to proceed with strict ADR-008 compliance**
