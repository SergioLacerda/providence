"""ACTIVATION_GUIDE.md sections: checklist, governance config, enforcement mode,
and the per-seedling description block. Split out of
_activation_guide_template.py to keep files under the 200-line convention.
"""

from __future__ import annotations


def _checklist_section() -> str:
    return """##  Activation Checklist

### Before Activation
- [ ] `.providence/source/mandates/mandates.md` exists
- [ ] `.providence/source/guidelines/` exists
- [ ] `.providence/metadata.json` exists
- [ ] `.providence/seedlings/` has 5 files (3 seeds + guide + verify)

### During Activation
- [ ] Close all IDE windows
- [ ] Reopen project in IDE
- [ ] Wait 5 seconds for seedlings to load

### After Activation
- [ ] Run `python3 .providence/seedlings/verify.py`
- [ ] Check SeedlingLoader output
- [ ] Test agent knowledge of mandates
- [ ] Confirm every governed response ends with:
  `PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`

---

"""


def _governance_config_section(
    mandates_list: str, guidelines_list: str, fingerprint: str
) -> str:
    return f"""##  Your Governance Configuration

### Mandates
Your project enforces these mandatory principles:
```
{mandates_list}
```

### Guidelines
Your project follows guidelines in these categories:
```
{guidelines_list}
```

### Fingerprint
Governance fingerprint for validation:
```
{fingerprint}
```

This fingerprint will be used to detect if governance rules have changed.

---

"""


def _enforcement_mode_section(
    enforcement_label: str, enforcement_explanation: str, enforcement_behavior: str
) -> str:
    return f"""##  Enforcement Mode

### Your Configuration: **{enforcement_label}**

{enforcement_explanation}

**How violations are handled:**

{enforcement_behavior}

**What this affects:**
- SeedlingLoader activation behavior
- Pre-commit hook response to violations
- CI/CD pipeline behavior on non-compliance

**To change this after setup:**
1. Edit `.providence/seedlings/compliance.seed.json`
2. Change `action_on_drift` value
3. Restart IDE

---

"""


def _seedling_descriptions_section() -> str:
    return """##  What Each Seedling Does

### 1. governance.seed.json (GAP v1.0)
**Purpose:** Auto-activates governance on project load
- Loads mandates into memory
- Sets up agent context
- Enables fingerprint validation
- Auto-triggers on `on_project_load`

**You'll know it works when:** Agent chat knows your mandates

### 2. agent-prep.seed.json (IDE Integration)
**Purpose:** Configures AI agents in your IDE
- Supports: Copilot, Claude, Gemini, Local LLM
- Auto-injects `.providence/source/` context
- Configures IDE hooks (VS Code, Cursor, Windsurf)
- Triggers on project load and editor focus

**You'll know it works when:** Agent gives governance-aware suggestions

### 3. compliance.seed.json (CI/CD Validation)
**Purpose:** Sets up compliance checking
- Validates fingerprint hasn't drifted
- Enforces mandates in CI/CD
- Supports selected runtime and CI checks

**You'll know it works when:** selected governance checks flag non-compliant changes

### 4. ACTIVATION_GUIDE.md (This File)
**Purpose:** Instructions for using seedlings

### 5. verify.py (Verification Script)
**Purpose:** Checks if activation succeeded

---

"""
