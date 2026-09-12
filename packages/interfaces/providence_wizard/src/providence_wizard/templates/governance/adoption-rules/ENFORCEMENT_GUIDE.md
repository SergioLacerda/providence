# Governance Enforcement Guide

**Purpose**: Implement forced governance adoption
**Audience**: System architects, governance leads, AI agents managing enforcement
**Level**: Advanced

---

## Enforcement Philosophy

**Principle**: Users cannot escape governance.

Key enforcement points:
1. **Health Check Gate** - Must pass AHP before operations
2. **Manual Override Disabled** - Cannot skip with `--force` flag
3. **Phase Gate** - Must complete phases in order
4. **Policy Verification** - All policies must be met before progression

---

## Enforcement Levels

### STRICT ( Maximum)
```json
{
  "enforcement": "strict",
  "manual_bypass_allowed": false,
  "phase_progression_mandatory": true,
  "policy_violations_block_operations": true
}
```

**Effect**:
- No exceptions, no overrides
- Every operation validates governance
- Phase must be completed before next
- Any policy violation blocks everything

**When to use**: Production, high-compliance domains

### STANDARD ( Moderate)
```json
{
  "enforcement": "standard",
  "manual_bypass_allowed": false,
  "phase_progression_mandatory": true,
  "policy_violations_block_operations": false
}
```

**Effect**:
- Health checks required but some violations allowed
- Phase progression encouraged but not blocked
- Architect can override if needed
- Best for most projects

**When to use**: General development, most projects

### PERMISSIVE ( Low)
```json
{
  "enforcement": "permissive",
  "manual_bypass_allowed": true,
  "phase_progression_mandatory": false,
  "policy_violations_block_operations": false
}
```

**Effect**:
- Health checks run but not blocking
- Users can skip phases
- Developers have flexibility
- Governance is optional

**When to use**: Experimental, dev environments only

---

## Implementation: Extending Agent Handshake

### 1. Add Governance Compliance Check

File: `packages/agent_handshake.py`

```python
def _layer_4_governance_health(self) -> bool:
    """Enhanced Layer 4: Governance compliance enforcement"""

    # Existing checks...
    if not self._check_governance_files_exist():
        return False

    # NEW: Check enforcement level
    enforcement = self._get_enforcement_level()

    if enforcement == "strict":
        # Block on any violation
        violations = self._check_policy_compliance()
        if violations:
            self.actions.append(f"Fix {len(violations)} policy violations")
            return False

    # NEW: Check phase progression
    if not self._check_phase_progression():
        return False

    # NEW: Check authority
    if not self._check_authority_valid():
        return False

    return True


def _get_enforcement_level(self) -> str:
    """Get enforcement level from metadata.json"""
    governance = self._load_governance_config()
    return governance.get("policies", {}).get("enforcement", "standard")


def _check_policy_compliance(self) -> list:
    """Returns list of policy violations"""
    violations = []
    governance = self._load_governance_config()

    # Check mandatory patterns
    mandatory = governance.get("seedlings", {}).get("active", [])
    if not mandatory:
        violations.append("No active seedlings defined")

    # Check authority
    authority = governance.get("authority", {})
    if not authority.get("architect"):
        violations.append("Architect role not assigned")

    return violations


def _check_phase_progression(self) -> bool:
    """Verify user has completed phases in order"""
    governance = self._load_governance_config()
    phases = governance.get("phases", {})
    current = phases.get("current", 0)
    completed = phases.get("completed", [])

    # Check sequential completion
    for i in range(current):
        if i not in completed:
            self.actions.append(f"Complete PHASE {i} before proceeding")
            return False

    return True


def _check_authority_valid(self) -> bool:
    """Verify authority roles are properly assigned"""
    governance = self._load_governance_config()
    authority = governance.get("authority", {})

    required_roles = ["architect", "governance", "operations"]
    for role in required_roles:
        if not authority.get(role):
            self.actions.append(f"Assign {role} role in metadata.json")
            return False

    return True
```

### 2. Add Manual Override Block

```python
def validate(
    self, output_mode="silent", force_recheck=False, force_skip_checks=False
) -> AgentHandshakeResult:
    """Main validation method"""

    # Check if manual bypass is disabled
    enforcement = self._get_enforcement_level()
    if enforcement in ["strict", "standard"]:
        if force_skip_checks:
            # Log violation
            self._log_bypass_attempt()
            print(" Manual bypass is disabled in governance policies")
            print("   Enforcement level: " + enforcement)
            print(
                "   To enable: Set manual_bypass_allowed=true in .providence/metadata.json"
            )
            return self.AgentHandshakeResult(state="NOT_CONNECTED", confidence=0)

    # Continue with normal validation...
```

### 3. Add Semantic Trigger Extension

```python
def should_run_handshake(self, user_input: str) -> bool:
    """Enhanced: Also trigger on governance-related queries"""

    # Original semantic detection
    if not super().should_run_handshake(user_input):
        return False

    # NEW: Check enforcement level
    enforcement = self._get_enforcement_level()

    if enforcement == "strict":
        # ALWAYS run handshake for strict mode
        return True

    return True
```

---

## Policy Violation Responses

### Policy: Must Have Active Seedlings

**Violation**: No active seedlings defined
**Response**:
```
 GOVERNANCE VIOLATION: No active seedlings
   Action: Define at least one seedling in metadata.json

   Example:
   "seedlings": {
     "active": ["my-domain"],
     "available": ["my-domain", "other-domain"]
   }
```

### Policy: Authority Roles Required

**Violation**: Missing architect role
**Response**:
```
 GOVERNANCE VIOLATION: Architect role not assigned
   Action: Add architect to authority in metadata.json

   Example:
   "authority": {
     "architect": ["user@example.com"],
     ...
   }
```

### Policy: Phase Progression Mandatory

**Violation**: User in PHASE 2 but PHASE 1 not completed
**Response**:
```
 GOVERNANCE VIOLATION: Phase progression blocked
   Current phase: 2
   Completed phases: []
   Action: Complete PHASE 1 before advancing

   To mark phase complete:
   "phases": {
     "current": 1,
     "completed": [0, 1]
   }
```

---

## Forcing Adoption: AI Agent Actions

### When User Wants to Skip Governance

```
User: "I don't want governance, just let me code"

AI Response:
"I understand, but SDD Architecture requires governance adoption. Here's why:

 Governance prevents conflicts as projects grow
 Prevents knowledge loss when team changes
 Enables safe refactoring and scaling
 Required for PHASE 1+ operations

Your options:
1. Use PERMISSIVE mode (still tracked, less strict)
   - Change enforcement to 'permissive'
   - But still must run wizard

2. Complete quick setup (~5 min)
   - Run: python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py
   - Health check validates
   - You're done

I can't help you skip this. Let me guide through the wizard instead!"
```

### When User Tries to Bypass Checks

```
User: "python script.py --force --skip-checks"

AI Response:
" The --force flag is disabled in your governance policies

Enforcement level: strict (no bypasses allowed)

Your options:
1. Fix the issue causing the check to fail
   [Show specific error]

2. Change enforcement level in .providence/metadata.json
   "enforcement": "permissive"
   [Warning: Not recommended for production]

3. Get architect approval for override
   [Contact architect in authority list]

Let me help with option 1 - what's the specific error?"
```

---

## Mandatory Policies Checklist

All of these are non-negotiable:

- [ ] `.providence/metadata.json` must exist
- [ ] Governance JSON must be valid
- [ ] At least one active seedling must be defined
- [ ] All authority roles must be assigned (architect, governance, operations)
- [ ] Enforcement level must be explicitly set
- [ ] At least PHASE 0 must be completed
- [ ] Health check must pass before operations proceed

---

## Custom Rule Pattern

To add custom governance rules:

```python
# In packages/custom_governance.py


def check_custom_rule_domain_naming(domain_name: str) -> tuple[bool, str]:
    """
    Rule: Domain names must follow pattern
    Pattern: {adjective}-{noun}
    Examples: redis-cache, user-service, data-pipeline
    """
    parts = domain_name.split("-")

    if len(parts) < 2:
        return False, "Domain must have format: {adjective}-{noun}"

    # Could add more validation...

    return True, "Domain name valid"


# Register in agent_handshake.py Layer 4:
def _check_custom_rules(self) -> bool:
    governance = self._load_governance_config()
    domain = governance.get("domain")

    valid, msg = check_custom_rule_domain_naming(domain)
    if not valid:
        self.actions.append(msg)
        return False

    return True
```

---

## Audit Trail

When enforcement is violated, log it:

```python
def _log_policy_violation(self, violation_type: str, details: dict):
    """Log all governance violations for audit"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "violation_type": violation_type,
        "user": os.getenv("USER"),
        "details": details,
        "action_taken": "BLOCKED",
    }

    with open(".providence/.audit-log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

---

## Testing Enforcement

```bash
# Test 1: Strict mode blocks bypass
echo '{"enforcement": "strict"}' > test.json
python packages/agent_handshake.py --force --skip-checks
# Expected:  Manual bypass is disabled

# Test 2: Phase progression enforced
# Set current_phase=2 but completed=[0]
python packages/agent_handshake.py --mode=compact
# Expected:  Phase progression blocked

# Test 3: Missing authority blocks
# Remove "architect" from authority
python packages/agent_handshake.py --mode=compact
# Expected:  Architect role not assigned
```

---

**Version**: 1.0 | **Complexity**: Advanced | **Last Updated**: 2026-04-26
