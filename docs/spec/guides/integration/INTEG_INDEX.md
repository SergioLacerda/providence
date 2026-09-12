# 📑 INTEGRATION — Local Index

**Complete navigation for the INTEGRATION flow (add new projects to SDD framework)**

---

## 📍 Entry Point

- [CHECKLIST.md](./CHECKLIST.md) — Start here (5 min overview)
- [CHECKLIST.md](./CHECKLIST.md) — 5-step process with commands

---

## 📋 Step-by-Step Guides

Follow in order (20-30 minutes total):

1. **[STEP_1.md](./STEP_1.md)**
   - Create project structure
   - Verify directory layout
   - ~5 minutes

2. **[STEP_2.md](./STEP_2.md)**
   - Copy template files from `INTEGRATION/templates/`
   - Understand what each file does
   - ~5 minutes

3. **[STEP_3.md](./STEP_3.md)**
   - Edit `.spec.config` (2 lines!)
   - Verify path to providence
   - ~2 minutes

4. **[STEP_4.md](./STEP_4.md)**
   - Run validation script
   - Check .providence/ infrastructure created
   - ~5 minutes

5. **[STEP_5.md](./STEP_5.md)**
   - Git add + commit
   - Verify files tracked
   - ~3 minutes

---

## 🗂️ Templates (Inside INTEGRATION/templates/)

| File | Purpose | Copies To |
|------|---------|-----------|
| `.spec.config` | Framework discovery | `your-project/.spec.config` |
| `.github/copilot-instructions.md` | AI governance | `your-project/.github/` |
| `.vscode/ai-rules.md` | VS Code rules | `your-project/.vscode/` |
| `.vscode/settings.json` | VS Code settings | `your-project/.vscode/` |
| `.cursor/rules/spec.mdc` | Cursor IDE rules | `your-project/.cursor/` |
| `.pre-commit-config.yaml` | Git hooks | `your-project/` |
| `.github/setup-precommit-hook.sh` | Hook setup | `your-project/scripts/` |
| `ai/README.md` | AI infrastructure guide | `your-project/.providence/` |

---

## ✅ Success Criteria

After completing all 5 steps, verify:

```
✅ .spec.config exists and points to ../providence
✅ .github/copilot-instructions.md copied
✅ .vscode/ai-rules.md copied
✅ .cursor/rules/spec.mdc copied
✅ .pre-commit-config.yaml in place
✅ .github/setup-precommit-hook.sh executable
✅ .providence/context-aware/ created (empty, ready)
✅ .providence/runtime/ created (with search indices)
✅ All changes git-staged
✅ Ready to commit
```

---

## 🚀 Quick Commands

**Get all templates:**

```bash
cp -r INTEGRATION/templates/* /path/to/your-project/
```

**Edit .spec.config:**

```bash
# Edit: spec_path = ../providence
```

**Run validation:**

```bash
python ../providencedocs/spec/SCRIPTS/phase-0-agent-onboarding.py
```

**Commit:**

```bash
git add .spec.config .github/ .vscode/ .cursor/ .pre-commit-config.yaml scripts/ .providence/
git commit -m "feat: Integrate SDD framework governance"
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| `.spec.config` not found | Copy from `INTEGRATION/templates/.spec.config` |
| Python path error | Check `.spec.config` spec_path = correct relative path |
| Templates not copying | Use: `cp -r INTEGRATION/templates/` (with trailing /) |
| Validation script fails | Check STEP_4_VALIDATE.md troubleshooting |
| Pre-commit hook error | See [Setup Pre-commit](./STEP_5.md) |

---

## 📊 Status

- [ ] Step 1: Project setup
- [ ] Step 2: Templates copied
- [ ] Step 3: .spec.config edited
- [ ] Step 4: Validation passed
- [ ] Step 5: Committed to git

---

**Purpose:** Integration flow index
**Target:** Teams adding new projects
**Duration:** 30 minutes
**Success:** Project ready for development
