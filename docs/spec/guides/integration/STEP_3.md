# ⚙️ STEP 3 — Configure .spec.config

**Goal:** Point `.spec.config` to providence (just 2 lines!)
**Duration:** 2 minutes
**Complexity:** Simple (edit 1 file)
**Prerequisites:** Step 2 complete (templates copied)
**Note:** You'll add `adoption_level` in STEP 6 after answering intention questions

---

## 📅 Where Are You?

You have:

- ✅ Project directories created (Step 1)
- ✅ Template files copied (Step 2)
- ❓ Need to edit `.spec.config` to point to providence

You're about to:

- Edit 1 file (`.spec.config`)
- Configure 2 variables (`spec_path` now, `adoption_level` in STEP 6)
- Move to Step 4 (validation)

---

## 🔍 Understanding .spec.config

`.spec.config` is a simple configuration file that tells your project where the SDD framework lives.

**Format:** INI (simple key=value)

**Now (STEP 3):**

```ini
[spec]
spec_path = ../providence
```

**Later (STEP 6):** You'll add:

```ini
[spec]
spec_path = ../providence
adoption_level = lite
```

(or `adoption_level = full`)

---

## ✏️ How to Edit (STEP 3 Only)

### Option A: From Command Line

```bash
cd /path/to/your-project

# Open with nano (easy text editor)
nano .spec.config
```

Then edit:

```ini
[spec]
spec_path = ../providence
```

Save: `Ctrl+O`, then `Enter`, then `Ctrl+X`

### Option B: From VS Code

```bash
# Open in VS Code
code .spec.config
```

Edit the file to:

```ini
[spec]
spec_path = ../providence
```

Save: `Ctrl+S` or `Cmd+S`

### Option C: From Any Editor

Open `.spec.config` in your favorite editor and edit to:

```ini
[spec]
spec_path = ../providence
```

---

## ⚙️ Choosing the Right spec_path

### Case 1: providence is a Sibling Directory (Recommended)

Your directory structure:

```
home/
├── providence/     ← SDD framework
└── your-project/        ← Your project
    └── .spec.config
```

**Use:** `spec_path = ../providence`

### Case 2: providence is Elsewhere

Your directory structure:

```
/home/username/
├── dev/
│   ├── providence/
│   └── your-project/
│       └── .spec.config
```

**Use:** `spec_path = ../providence` (still works!)

### Case 3: providence is Far Away

Your directory structure:

```
/home/username/work/projects/myapp/
└── .spec.config

/opt/frameworks/providence/
└── (SDD framework here)
```

**Use:** `spec_path = /opt/frameworks/providence` (absolute path)

### Case 4: providence is in a Different Location

```bash
# Find where providence actually is
find ~ -type d -name "providence" 2>/dev/null
# Shows: /home/username/frameworks/providence

# Then use relative path from your project
# If your project is /home/username/my-project
# and providence is /home/username/frameworks/providence
# Use: spec_path = ../frameworks/providence
```

---

## ✅ Verify Configuration

After editing, verify it's correct:

```bash
cat .spec.config
```

Should show:

```ini
[spec]
spec_path = ../providence
```

Or if you used absolute path:

```ini
[spec]
spec_path = /path/to/providence
```

### Test the Path

```bash
# This shows what the script will see
cat .spec.config | grep spec_path | cut -d' ' -f3

# Should output:
# ../providence
# (or your absolute path)

# Then verify the path actually exists
cd $(cat .spec.config | grep spec_path | cut -d' ' -f3)
ls
# Should show: INTEGRATION/, EXECUTION/, docs/, templates/, etc.
```

---

## 🆘 Troubleshooting

### Issue: "No such file or directory"

```bash
# The spec_path you entered doesn't exist

# Solution 1: Find where providence really is
find ~ -type d -name "providence" 2>/dev/null

# Solution 2: Update .spec.config with correct path
nano .spec.config
# Edit spec_path to correct location
```

### Issue: ".spec.config not found"

```bash
# Did Step 2 copy work?

# Check if file exists
ls -la .spec.config

# If not, copy it manually
cp ../providence/INTEGRATION/templates/.spec.config .

# Then edit it
nano .spec.config
```

### Issue: Can't Edit File (Permission Denied)

```bash
# You don't have permission

# Solution: Change permissions
chmod +w .spec.config

# Then try editing again
nano .spec.config
```

---

## 📝 Example .spec.config Files

### Example 1: Sibling Directories

```ini
[spec]
# Points to ../providence (one level up, then providence folder)
spec_path = ../providence

# Alternative: absolute path
# spec_path = /home/sergio/dev/providence
```

### Example 2: With Comments

```ini
[spec]
# Framework source: https://github.com/user/providence
# This tells your project where to find PHASE 0, AGENT_HARNESS, etc.
spec_path = ../providence

# You can also use absolute path:
# spec_path = /opt/providence
```

---

## ✅ Ready for Step 4?

Once `.spec.config` is configured, proceed to:

**→ [STEP_4.md](./STEP_4.md)**

Run validation script to verify everything works.

---

## 🚀 What Happens Next

In Step 4, the validation script will:

1. Read `.spec.config`
2. Find providence at the specified `spec_path`
3. Create `.providence/` infrastructure
4. Run VALIDATION_QUIZ to verify knowledge

---

**Estimated time:** 2 minutes
**Difficulty:** Very easy
**Next step:** Validate setup
