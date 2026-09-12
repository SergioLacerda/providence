# 📋 STEP 2 — Copy Template Files

**Goal:** Copy SDD template files to your project
**Duration:** 5 minutes
**Complexity:** Simple (copy files)
**Prerequisites:** Step 1 complete (directories created)

---

## 📍 Where Are You?

You have:

- ✅ Project directories created (Step 1)
- ✅ Git initialized
- ❓ Need to copy SDD template files

You're about to:

- Copy files from providence/INTEGRATION/templates/
- Populate your project with SDD configuration
- Move to Step 3

---

## 🚀 How to Copy Templates

### Option A: From Command Line (Recommended)

**If providence is in a sibling directory** (recommended setup):

```bash
# From your project directory
cd /path/to/your-project

# Copy templates (note trailing /)
cp -r ../providence/INTEGRATION/templates/* .
```

**If providence is elsewhere:**

```bash
# Adjust the path to providence
cp -r /path/to/providence/INTEGRATION/templates/* /path/to/your-project/
```

### Option B: Manual Copy (If CLI doesn't work)

1. Open file browser to `providence/INTEGRATION/templates/`
2. Select all files: `Ctrl+A`
3. Copy: `Ctrl+C`
4. Navigate to your project root
5. Paste: `Ctrl+V`

---

## ✅ Verify Files Were Copied

After copying, verify these files exist:

```bash
cd /path/to/your-project

# Check root-level files
ls -la | grep -E "^-.*\.spec\.config|pre-commit"

# Check subdirectories
ls -la .github/
ls -la .vscode/
ls -la .cursor/
ls -la scripts/
ls -la .providence/
```

**Expected files:**

| File | Should Be | Size |
|------|-----------|------|
| `.spec.config` | project root | ~40 lines |
| `.github/copilot-instructions.md` | `.github/` | ~400 lines |
| `.vscode/ai-rules.md` | `.vscode/` | ~300 lines |
| `.vscode/settings.json` | `.vscode/` | ~50 lines |
| `.cursor/rules/spec.mdc` | `.cursor/` | ~250 lines |
| `.pre-commit-config.yaml` | project root | ~30 lines |
| `.github/setup-precommit-hook.sh` | `scripts/` | ~50 lines |
| `.providence/README.md` | `.providence/` | ~100 lines |

### Quick Verification Script

```bash
# Run this to verify all files
for file in .spec.config .github/copilot-instructions.md .vscode/ai-rules.md .cursor/rules/spec.mdc .pre-commit-config.yaml .github/setup-precommit-hook.sh .providence/README.md; do
  if [ -f "$file" ]; then
    echo "✅ $file"
  else
    echo "❌ $file (missing!)"
  fi
done
```

---

## 📝 What Each File Does

### `.spec.config`

- **Purpose:** Tells your project where SDD framework is located
- **Edit in:** Step 3
- **Used by:** PHASE 0 setup script

### `.github/copilot-instructions.md`

- **Purpose:** Copilot/Claude instructions for your project
- **Used by:** GitHub Copilot Chat, AI agents
- **Don't edit yet:** References will be updated after PHASE 0

### `.vscode/ai-rules.md`

- **Purpose:** VS Code AI governance rules
- **Used by:** VS Code settings
- **Can edit:** After understanding PHASE 0 output

### `.cursor/rules/spec.mdc`

- **Purpose:** Cursor IDE rules
- **Used by:** Cursor IDE
- **Don't edit yet:** Will be consistent with GitHub Copilot

### `.pre-commit-config.yaml`

- **Purpose:** Git pre-commit hooks (auto-checks before commit)
- **Used by:** Git hook system
- **Install in:** Step 4 or Step 5

### `.github/setup-precommit-hook.sh`

- **Purpose:** Installs pre-commit hooks
- **Run:** After copying (optional) or during Step 4
- **Usage:** `bash .github/setup-precommit-hook.sh`

### `.providence/README.md`

- **Purpose:** Explains .providence/ directory structure
- **Used by:** Developers during PHASE 0
- **Don't edit yet:** PHASE 0 will create infrastructure

---

## 🆘 Troubleshooting

### Issue: "No such file or directory"

```bash
# Wrong: cp -r INTEGRATION/templates/* .
# The path providence is not found

# Solution: Check where providence actually is
find ~ -type d -name "providence" 2>/dev/null

# Then use the full path
cp -r /home/username/providence/INTEGRATION/templates/* .
```

### Issue: "Permission denied"

```bash
# You don't have permission to copy

# Solution: Use sudo (if needed)
sudo cp -r ../providence/INTEGRATION/templates/* .

# Or change to your user
sudo chown -R $USER:$USER .
```

### Issue: Files copied but some are missing

```bash
# Verify templates directory has all files
ls -la ../providence/INTEGRATION/templates/

# If templates/ is empty, something is wrong with providence
# Check providence/INTEGRATION/templates/ exists
```

### Issue: Hidden files not showing

```bash
# Hidden files (starting with .) might not copy with *
# Solution: Use this instead

cp -r ../providence/INTEGRATION/templates/. .
# Note: dot at end of "templates/."
```

---

## ✅ Ready for Step 3?

Once all files are copied, proceed to:

**→ [STEP_3.md](./STEP_3.md)**

Configure `.spec.config` to point to providence.

---

## 📊 File Count Check

After copying, you should have approximately:

```bash
# Count files in each directory
find . -type f ! -path './.git/*' ! -path './.github/*' -o -path './.github/*' | wc -l
# Should show: ~8 files across .github/, .vscode/, .cursor/, scripts/, .providence/
```

---

**Estimated time:** 5 minutes
**Difficulty:** Easy
**Next step:** Configure .spec.config
