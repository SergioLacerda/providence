# 🎯 STEP 6 — Detect Your Intention (Choose LITE or FULL)

**Goal:** Understand your project's context and governance needs
**Duration:** 10 minutes
**Complexity:** Simple (answer questions)
**Prerequisites:** STEP 1-5 complete (technical setup done)

---

## 📅 Where Are You?

You have:

- ✅ Project directories created (Step 1)
- ✅ Template files copied (Step 2)
- ✅ `.spec.config` configured (Step 3)
- ✅ Validation script passed (Step 4)
- ✅ Changes committed to git (Step 5)
- ❓ Now: Understand your project's governance needs

You're about to:

- Answer 5 simple questions about your project
- Determine if you need LITE or FULL governance
- Update `.spec.config` with your adoption level
- Move to EXECUTION with appropriate rules

---

## 🤔 The 5 Questions

Answer these questions about your project. **Be honest.** These aren't trick questions—they help you pick the right level.

### Question 1: Team Size & Composition

**"How many people will be developing with Providence?"**

- A: 1-5 people
- B: 5-20 people
- C: 20+ people, multiple teams

**→ Move to Q2**

---

### Question 2: Project Type & Risk

**"What is this project's primary use?"**

- A: Learning, experimentation, side project, hobby
- B: Internal tool, MVP, prototyping
- C: Production service, business-critical, customer-facing

**→ Move to Q3**

---

### Question 3: Regulatory / Compliance

**"Does your project have regulatory or compliance requirements?"**

- A: No requirements, no audits
- B: Internal standards, team agreements
- C: Regulatory (SOC2, HIPAA, etc.), formal audits, compliance documentation

**→ Move to Q4**

---

### Question 4: Autonomous Agents

**"Will you use AI agents (GitHub Copilot, Claude, etc.) in your workflow?"**

- A: No, manual coding only
- B: Maybe, experimental use
- C: Yes, agents are core to our workflow

**→ Move to Q5**

---

### Question 5: Error Cost

**"What's the cost of a deployed bug?"**

- A: Low cost, rollback easy, affects just this project
- B: Medium cost, rollback takes 1-2 hours, affects a few users
- C: High cost, rollback complex, affects many users, reputation impact, $$$

**→ Determine your level**

---

## 📊 Scoring

Count your answers:

- **Mostly A's → 🟢 LITE**
  - 1-5 people
  - Learning/experimentation
  - Low compliance needs
  - Manual coding
  - Low error cost

- **Mostly B's → Consider LITE or FULL** (see LITE-TO-FULL migration)
  - You're on the edge
  - Start LITE, upgrade when needed
  - Upgrade is 30 min, reversible

- **Mostly C's → 🔵 FULL**
  - 20+ people
  - Production critical
  - Regulatory requirements
  - Autonomous agents
  - High error cost

---

## 🎯 What Each Level Means

### 🟢 LITE (15 min to start)

- **Principles:** 10 core
- **Rules:** 5 essential (imports, async, layers, errors, tests)
- **DoD Criteria:** 10 items (basic quality)
- **Workflow Phases:** 3 simplified (Spec, Implement, Validate)
- **Pre-commit Hooks:** 5 basic checks
- **Best for:** Learning, small teams, low-risk projects
- **Upgrade path:** → FULL (30 min migration)

### 🔵 FULL (40 min to start)

- **Principles:** 15 complete
- **Rules:** 16 mandatory (comprehensive governance)
- **DoD Criteria:** 45 items (production-grade)
- **Workflow Phases:** 7 complete (full AGENT_HARNESS)
- **Pre-commit Hooks:** 12 comprehensive checks
- **AI Agent Integration:** Full support
- **Best for:** Production teams, regulatory, high-risk projects
- **Auditable:** Complete decision trail (ADRs)

---

## ✏️ Update `.spec.config`

Now that you know your adoption level, update `.spec.config`:

### Current State

```ini
[spec]
spec_path = ../providence
```

### New State (Add Your Level)

#### If you chose LITE

```ini
[spec]
spec_path = ../providence
adoption_level = lite
```

#### If you chose FULL

```ini
[spec]
spec_path = ../providence
adoption_level = full
```

### How to Update

```bash
cd /path/to/your-project

# Option 1: With nano
nano .spec.config
# Edit and save (Ctrl+O, Enter, Ctrl+X)

# Option 2: With command line
echo "adoption_level = lite" >> .spec.config
# OR
echo "adoption_level = full" >> .spec.config
```

### Verify

```bash
cat .spec.config
# Should show both lines:
# [spec]
# spec_path = ../providence
# adoption_level = lite  (or full)
```

---

## 🔄 Document Your Intention

### Option 1: In `.providence/README.md` (Recommended)

Add a section:

```markdown
## Project Governance

**Adoption Level:** LITE (or FULL)
**Reason:** [Your reason from the 5 questions]
**Team Size:** [Number of people]
**Risk Level:** [Low / Medium / High]
**Reviewed by:** [Your name]
**Date:** [Today's date]
```

### Option 2: In Your Project README

```markdown
## Providence Governance

This project uses **Providence LITE** (or FULL) governance.
- Setup time: 15 minutes (or 40)
- Rules: 5 essential (or 16 mandatory)
- DoD Criteria: 10 items (or 45 items)

See [Providence Adoption Guide](../adoption/LITE-ADOPTION.md)
```

---

## ✅ Success Criteria

After this step:

- ✅ You answered the 5 questions honestly
- ✅ You know whether you need LITE or FULL
- ✅ `.spec.config` includes `adoption_level`
- ✅ Your intention is documented (in `.providence/README.md` or project README)
- ✅ Team is aligned on the choice
- ✅ Ready to move to EXECUTION

---

## 🚀 Next Steps

### For Everyone

1. Commit your changes

   ```bash
   git add .spec.config .providence/README.md
   git commit -m "docs: set adoption level to LITE (or FULL)"
   ```

2. Read your adoption guide:
   - **LITE:** [LITE-ADOPTION.md](../adoption/LITE-ADOPTION.md)
   - **FULL:** [FULL-ADOPTION.md](../adoption/FULL-ADOPTION.md)

### For Developers

1. Go to [EXECUTION/_START_HERE.md](spec/guides/operational/CORE__START_HERE.md)
2. Follow AGENT_HARNESS workflow with your adoption level

### For Team Leads

1. Communicate the choice to your team
2. Reference [adoption/INDEX.md](../adoption/INDEX.md) for FAQs
3. Plan LITE→FULL migration if needed (see [LITE-TO-FULL-MIGRATION.md](../adoption/LITE-TO-FULL-MIGRATION.md))

---

## 🤔 Questions?

**"Can we change from LITE to FULL later?"**
→ Yes! See [LITE-TO-FULL-MIGRATION.md](../adoption/LITE-TO-FULL-MIGRATION.md) (30 min)

**"What if our project changes (scales up)?"**
→ Re-answer the 5 questions. If mostly C's now → upgrade to FULL

**"Can different projects use different levels?"**
→ Yes! Each project's `.spec.config` can have its own adoption_level

**"What if I'm unsure?"**
→ Start with LITE. It's easier, and upgrading is simple and reversible.

---

## 📊 Real-World Examples

**LITE Projects:**

- Team learning Providence for the first time
- Side project, hobby, personal tools
- Internal utilities, < 5 people
- Proof of concepts, MVPs
- Experimental features

**FULL Projects:**

- Production API serving customers
- Mission-critical backend
- Regulatory compliance required
- Large team (20+)
- Autonomous agents handling complex workflows

---

**Integration complete! 🎉**

**Next:** Start implementing features → [EXECUTION/_START_HERE.md](spec/guides/operational/CORE__START_HERE.md)

*Go team!*
