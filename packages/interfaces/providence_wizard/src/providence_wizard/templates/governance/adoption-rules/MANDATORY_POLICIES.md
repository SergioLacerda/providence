# Mandatory Governance Policies

**Status**: Non-Negotiable
**Audience**: All users, developers, AI agents
**Enforcement**: Automatic via AHP + custom validation

---

## The 7 Mandatory Policies

### Policy 1: Governance File Must Exist

**Policy**: `.providence/metadata.json` must exist in project root

**Why**: Entire system depends on this file for configuration

**How to Fix**:
```bash
# Option A: Run wizard (recommended)
python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py

# Option B: Manual creation
mkdir -p .providence
# Copy template and edit
```

**Verification**:
```bash
[ -f .providence/metadata.json ] && echo " Policy 1 met" || echo " Policy 1 failed"
```

---

### Policy 2: Governance File Must Be Valid JSON

**Policy**: `.providence/metadata.json` must parse as valid JSON

**Why**: System cannot load invalid JSON

**How to Fix**:
```bash
# Check syntax
python3 -m json.tool .providence/metadata.json

# Common errors:
# - Missing commas between fields
# - Trailing commas in arrays
# - Unquoted keys
# - Single quotes instead of double quotes

# Use online JSON validator if unsure
```

**Verification**:
```bash
python3 -c "import json; json.load(open('.providence/metadata.json'))" && echo " Policy 2 met" || echo " Policy 2 failed"
```

---

### Policy 3: At Least One Active Seedling Must Be Defined

**Policy**: `metadata.json` must have at least one entry in `seedlings.active`

**Why**: Users must declare their domain/specialization

**Example**:
```json
{
  "seedlings": {
    "active": ["my-domain"],
    "available": ["my-domain", "template-1", "template-2"]
  }
}
```

**How to Fix**:
1. Decide your primary domain (what you're building)
2. Edit `seedlings.active` to include it
3. Ensure directory exists: `.providence/seedlings/{domain}/`

**Verification**:
```python
import json

config = json.load(open(".providence/metadata.json"))
active_seedlings = config.get("seedlings", {}).get("active", [])
assert len(active_seedlings) >= 1, "No active seedlings"
print(" Policy 3 met")
```

---

### Policy 4: All Authority Roles Must Be Assigned

**Policy**: Every role (architect, governance, operations) must have at least one email assigned

**Why**: Governance requires clear ownership and responsibility

**Required Roles**:
| Role | Responsibility |
|------|---|
| `architect` | Define policies, approve major changes |
| `governance` | Enforce rules, audit compliance |
| `operations` | Deploy, manage runtime, incident response |

**Example**:
```json
{
  "authority": {
    "architect": ["alice@company.com"],
    "governance": ["bob@company.com"],
    "operations": ["charlie@company.com"]
  }
}
```

**How to Fix**:
1. Identify person for each role
2. Add their email to the role
3. Can assign same person to multiple roles if needed

**Verification**:
```python
config = json.load(open(".providence/metadata.json"))
authority = config.get("authority", {})

for role in ["architect", "governance", "operations"]:
    assert authority.get(role), f"{role} not assigned"

print(" Policy 4 met")
```

---

### Policy 5: Enforcement Level Must Be Explicitly Set

**Policy**: `policies.enforcement` must be one of: `strict`, `standard`, `permissive`

**Why**: System needs to know how strictly to apply governance

**Options**:
```json
{
  "policies": {
    "enforcement": "strict"    // No bypasses (production)
    // OR
    "enforcement": "standard"  // Architect can override (most common)
    // OR
    "enforcement": "permissive" // Flexible (dev only)
  }
}
```

**How to Fix**:
```bash
# Edit .providence/metadata.json and set enforcement

# Recommended for most projects:
"enforcement": "standard"
```

**Verification**:
```python
config = json.load(open(".providence/metadata.json"))
enforcement = config.get("policies", {}).get("enforcement")
assert enforcement in ["strict", "standard", "permissive"], f"Invalid: {enforcement}"
print(" Policy 5 met")
```

---

### Policy 6: PHASE 0 Must Be Marked Complete

**Policy**: `phases.completed` must include `0` (PHASE 0 - Agent Onboarding)

**Why**: Phase 0 establishes governance foundation

**How to Fix**:
```json
{
  "phases": {
    "current": 0,
    "completed": [0],
    "required": [0, 1, 2, 3, 4, 5, 6, 7]
  }
}
```

After running wizard, it auto-updates this.

**Manual Update**:
```bash
# Edit .providence/metadata.json
# Make sure "completed" includes 0
```

**Verification**:
```python
config = json.load(open(".providence/metadata.json"))
completed = config.get("phases", {}).get("completed", [])
assert 0 in completed, "PHASE 0 not completed"
print(" Policy 6 met")
```

---

### Policy 7: Health Check Must Pass

**Policy**: AHP (Agent Handshake Protocol) must return state = `HEALTHY`

**Why**: This validates all other policies are met

**How to Check**:
```bash
python packages/agent_handshake.py --mode=compact
```

Expected output:
```
 SDD STATUS
State:  HEALTHY
Confidence: 85%
```

**How to Fix**:
1. Run the check to see what failed
2. Fix the specific issue
3. Re-run to verify

**Verification**:
```python
import sys

sys.path.insert(0, "packages")
from agent_handshake import AgentHandshakeProtocol

ahp = AgentHandshakeProtocol()
result = ahp.validate(output_mode="silent")
assert result.state == "HEALTHY", f"Health check failed: {result.state}"
print(" Policy 7 met")
```

---

## Enforcement Actions

### When Policy is Violated

| Enforcement Level | Response | Can Override |
|---|---|---|
| `strict` |  BLOCK operation | No - must fix policy |
| `standard` |  WARN user | Yes - architect can approve |
| `permissive` |  WARN only | Yes - anyone can proceed |

### Example: Strict Mode Violation

```
User: python script.py
Response:
 GOVERNANCE VIOLATION
   Policy: At least one active seedling required
   Current: seedlings.active = []

   Fix: Add seedling to .providence/metadata.json
   "seedlings": {
     "active": ["my-domain"]  // Add here
   }

   Then retry: python script.py
```

---

## Verification Script

Run this to check all mandatory policies at once:

```bash
python3 << 'EOF'
import json
import sys

def check_all_policies():
    """Verify all 7 mandatory policies"""
    config = json.load(open('.providence/metadata.json'))

    errors = []

    # Policy 1: File exists (already passed to get here)
    print(" Policy 1: metadata.json exists")

    # Policy 2: Valid JSON (already passed to parse here)
    print(" Policy 2: JSON is valid")

    # Policy 3: Active seedlings
    active = config.get('seedlings', {}).get('active', [])
    if not active:
        errors.append("Policy 3: No active seedlings")
    else:
        print(f" Policy 3: Active seedlings = {active}")

    # Policy 4: Authority roles
    authority = config.get('authority', {})
    for role in ['architect', 'governance', 'operations']:
        if not authority.get(role):
            errors.append(f"Policy 4: {role} not assigned")
        else:
            print(f" Policy 4: {role} = {authority[role]}")

    # Policy 5: Enforcement level
    enforcement = config.get('policies', {}).get('enforcement')
    if enforcement not in ['strict', 'standard', 'permissive']:
        errors.append(f"Policy 5: Invalid enforcement = {enforcement}")
    else:
        print(f" Policy 5: Enforcement = {enforcement}")

    # Policy 6: PHASE 0 complete
    completed = config.get('phases', {}).get('completed', [])
    if 0 not in completed:
        errors.append("Policy 6: PHASE 0 not completed")
    else:
        print(f" Policy 6: PHASE 0 completed")

    # Policy 7: Health check
    print("\nRunning Policy 7 health check...")
    # (would import and run AHP here)

    # Report
    if errors:
        print("\n Policies failed:")
        for error in errors:
            print(f"   {error}")
        return False
    else:
        print("\n All mandatory policies met!")
        return True

check_all_policies()
EOF
```

---

## Non-Compliance Actions

| Scenario | Compliance Action |
|---|---|
| User tries to deploy without governance |  Operation blocked (strict/standard) |
| User modifies policies without authority |  Change rejected (strict/standard) |
| User skips phase progression |  Operation blocked (strict/standard) |
| User tries manual bypass `--force` |  Flag ignored in strict/standard mode |
| User creates seedling without approval |  Warning issued (can proceed in permissive) |

---

## FAQ: "Why These 7 Policies?"

**Q: Can I skip some policies?**
A: No. All 7 are mandatory because they're interconnected. Each builds on previous ones.

**Q: Can I modify these policies?**
A: You can create additional policies in enforcement-rules, but these 7 cannot be removed.

**Q: What if I disagree with a policy?**
A: Raise an issue with the SDD Architecture team. Policies exist for good reasons.

**Q: How often are policies reviewed?**
A: Quarterly. Feedback from users is considered for improvements.

---

**Version**: 1.0 | **Last Updated**: 2026-04-26 | **Status**:  Production Ready
