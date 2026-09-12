# SDD Governance Implementation Guide

**Audience**: Developers & AI Agents
**Purpose**: Detailed implementation of governance structure
**Depth**: Intermediate to Advanced

---

## Governance Core Components

### 1. metadata.json Structure

```json
{
  "version": "1.0",
  "domain": "your-domain-name",
  "authority": {
    "architect": ["user@example.com"],
    "governance": ["user@example.com"],
    "operations": ["user@example.com"]
  },
  "seedlings": {
    "active": ["domain-name"],
    "available": ["domain-1", "domain-2"]
  },
  "policies": {
    "enforcement": "strict|standard|permissive",
    "health_check_required": true,
    "manual_bypass_allowed": false
  },
  "phases": {
    "current": 0,
    "completed": [],
    "required": [0, 1, 2, 3, 4, 5, 6, 7]
  }
}
```

### 2. Seedling Structure Template

```
.providence/seedlings/{domain-name}/
 README.md                      # Domain overview
 governance-specialization.json  # Domain-specific rules
 implementation/
    patterns/
       architecture.md
       code-structure.md
       naming-conventions.md
    templates/
       module-template.py
       class-template.py
       config-template.json
    examples/
        basic-example/
        advanced-example/
        testing-example/
 validation/
     rules.json
     checklist.md
```

### 3. Governance-Specialization.json

```json
{
  "domain": "your-domain",
  "authority": {
    "can_modify_policies": ["architect"],
    "can_create_seedlings": ["architect", "governance"],
    "can_deploy": ["operations"]
  },
  "mandatory_patterns": [
    "pattern-1",
    "pattern-2"
  ],
  "optional_patterns": [
    "pattern-3"
  ],
  "validations": [
    "test-coverage-minimum-80%",
    "documentation-required",
    "code-review-required"
  ]
}
```

---

## Implementation Steps (For Agents)

### Step 1: Initialize .providence/ Directory

```bash
mkdir -p .providence/seedlings
mkdir -p .providence/phases
mkdir -p .providence/enforcement
mkdir -p .providence/rules
```

### Step 2: Create metadata.json

Use template above, fill in:
- `domain` - user's primary domain
- `authority` - who has permissions
- `policies` - enforcement level

### Step 3: Define Seedlings

For each domain the user operates in:
1. Create `.providence/seedlings/{domain}/`
2. Add `governance-specialization.json`
3. Document patterns in `implementation/`

### Step 4: Set Enforcement Level

```json
"policies": {
  "enforcement": "strict"  // Prevent any bypass
}
```

This forces AHP validation before operations.

### Step 5: Validate with AHP

```bash
python packages/agent_handshake.py --mode=verbose
```

Expected state: **HEALTHY** 

---

## Extending Agent Handshake for Governance

### Current AHP Layer 4: Governance Health

AHP checks:
-  metadata.json exists
-  JSON is valid
-  Required fields present
-  Authority defined

### New: Governance Compliance Checks

Add to `packages/agent_handshake.py`:

```python
def _check_policy_compliance(self):
    """Verify policies are being followed"""
    governance = self._load_governance_config()
    policies = governance.get('policies', {})

    # Check enforcement level
    enforcement = policies.get('enforcement', 'standard')

    if enforcement == 'strict':
        # Verify all mandatory patterns exist
        # Check authority compliance
        # Verify phase progression

    return {
        'enforcement_level': enforcement,
        'compliance_score': score,
        'violations': violations
    }
```

---

## Forcing Adoption

### Method 1: Health Check Block

```python
if not ahp.validate().passed:
    print(" Governance not adopted")
    print(
        "Run: python packages/interfaces/providence_wizard/src/providence_wizard/SCRIPTS/phase-0-agent-onboarding.py"
    )
    sys.exit(1)
```

### Method 2: Manual Override Disabled

In `policies.json`:
```json
{
  "manual_bypass_allowed": false
}
```

Users CANNOT run:
```bash
python script.py --force --skip-checks
```

### Method 3: Phase Gate

```python
current_phase = governance.get("phases", {}).get("current", 0)
required_phase = 1

if current_phase < required_phase:
    print(" Must complete PHASE 0 first")
    sys.exit(1)
```

---

## AI Agent Workflow

When user asks "How do I implement governance?":

1. **Check if wizard was run**
   ```bash
   [ -f .providence/metadata.json ] && echo " Governance exists"
   ```

2. **Understand their domain**
   - Ask what they're building
   - Recommend seedling templates
   - Explain governance benefits

3. **Guide through implementation**
   - Create .providence/ structure
   - Define authority
   - Set policies
   - Add seedlings

4. **Validate with AHP**
   - Run health check
   - Fix any issues
   - Confirm HEALTHY status

5. **Document decisions**
   - In metadata.json
   - In seedling README
   - In implementation guides

---

## Common Patterns by Domain

### API Services
- Authority: 2 architects, 1 ops lead
- Enforcement: strict
- Required: API documentation, schema validation
- Optional: GraphQL, REST patterns

### Data Pipelines
- Authority: data engineer + architect
- Enforcement: standard
- Required: data quality checks, lineage
- Optional: dbt, Airflow patterns

### ML Systems
- Authority: ML lead + engineer
- Enforcement: standard
- Required: model tracking, metrics
- Optional: MLOps, experiment patterns

---

## Troubleshooting

### "metadata.json" not valid
```bash
python3 -m json.tool .providence/metadata.json
# Fix any JSON errors, retry
```

### Authority not recognized
```bash
# Check metadata.json authority section
# Add user email to appropriate role
# Re-run AHP validation
```

### Phase progression blocked
```bash
# Check current phase in metadata.json
# Complete required phases in sequence
# Update phase.completed array
```

---

**Version**: 1.0 | **Complexity**: Intermediate | **Last Updated**: 2026-04-26
