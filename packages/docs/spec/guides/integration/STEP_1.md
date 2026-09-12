# 🔧 STEP 1 — Setup Project Structure

**Goal:** Prepare your project directory for SDD integration
**Duration:** 5 minutes
**Complexity:** Simple (just create directories)

---

## 📍 Where Are You?

You have:

- ✅ A project repository (or about to create one)
- ✅ Git initialized (`git init` already done)
- ❓ Need to add SDD framework

You're about to:

- Create necessary directories
- Verify your project structure
- Move to Step 2

---

## 🚀 Step-by-Step

### 1. Navigate to Your Project

```bash
cd /path/to/your-project

# Verify you're in the right place
pwd
# Should output something like: /home/username/my-project

# Verify git is initialized
git status
# Should show: On branch main (or similar)
# If error: run `git init` first
```

### 2. Create Core Directories

```bash
# Create all needed directories at once
mkdir -p .github .vscode .cursor scripts
```

**What each directory is for:**

| Directory | Purpose |
|-----------|---------|
| `.github/` | GitHub-specific files (Copilot instructions) |
| `.vscode/` | VS Code configuration (AI rules) |
| `.cursor/` | Cursor IDE configuration |
| `scripts/` | Utility scripts (pre-commit setup) |
| `.providence/` | SDD infrastructure (created by PHASE 0 later) |

### 3. Verify Structure

```bash
# Check what you just created
ls -la | grep "^\."

# Expected output:
# drwxr-xr-x  .github
# drwxr-xr-x  .vscode
# drwxr-xr-x  .cursor
# drwxr-xr-x  scripts
```

Or check individual directories:

```bash
ls .github .vscode .cursor scripts
# Should each show: (empty directories)
```

---

## ✅ Success Criteria

After Step 1, your project should have:

```
your-project/
├── .github/        ← empty (will fill in Step 2)
├── .vscode/        ← empty (will fill in Step 2)
├── .cursor/        ← empty (will fill in Step 2)
├── scripts/        ← empty (will fill in Step 2)
├── .providence/            ← empty (will fill in Step 4)
├── src/            ← your existing code
├── tests/          ← your existing tests
├── .gitignore      ← existing
├── README.md       ← existing
└── (other files)
```

Verify:

```bash
test -d .github && test -d .vscode && test -d .cursor && test -d scripts && echo "✅ All directories exist" || echo "❌ Missing directory"
```

---

## 🆘 Troubleshooting

### Issue: Permission Denied

```bash
# If you get permission error:
mkdir -p .github .vscode .cursor scripts

# Try with sudo (only if above fails):
sudo mkdir -p .github .vscode .cursor scripts
```

### Issue: Directory Already Exists

```bash
# If you get "File exists" error, that's OK!
# mkdir -p handles existing directories

# Just verify they exist:
ls -d .github .vscode .cursor scripts
```

### Issue: pwd Shows Wrong Location

```bash
# Make sure you're in the right project
pwd

# If wrong, navigate to correct location
cd /path/to/correct/project
```

---

## 📝 Notes

- **Directories are empty:** Step 2 will populate them with template files
- **No files created yet:** Just directories; all changes reversible
- **Git not involved yet:** We commit all at once in Step 5

---

## ✅ Ready for Step 2?

Once all directories exist, proceed to:

**→ [STEP_2.md](./STEP_2.md)**

Copy template files from SDD framework to your project.

---

**Estimated time:** 5 minutes
**Difficulty:** Easy
**Next step:** Copy templates
