#  SDD Architecture Governance Seedlings

**Quick Start for AI Agents** - Optimized for Wizard Integration

## For AI Assistants: Navigation Guide

If you're an AI agent helping a user adopt SDD Architecture governance:

1. **First Time Setup?**
    Go to [WIZARD_ADOPTION.md](./base-seedling/WIZARD_ADOPTION.md)

2. **Implementing Governance?**
    Go to [GOVERNANCE_IMPLEMENTATION.md](./base-seedling/GOVERNANCE_IMPLEMENTATION.md)

3. **Enforcing Rules?**
    Go to [ENFORCEMENT_GUIDE.md](./adoption-rules/ENFORCEMENT_GUIDE.md)

4. **Need Quick Reference?**
    Go to [QUICK_REFERENCE.md](./base-seedling/QUICK_REFERENCE.md)

---

## What This Directory Contains

### `base-seedling/`
Core governance templates and implementation guides optimized for AI understanding.
- **WIZARD_ADOPTION.md** - Step-by-step wizard integration
- **GOVERNANCE_IMPLEMENTATION.md** - Detailed implementation patterns
- **QUICK_REFERENCE.md** - Quick lookup for common scenarios

### `adoption-rules/`
Enforcement mechanisms and mandatory policies.
- **ENFORCEMENT_GUIDE.md** - How to enforce governance
- **MANDATORY_POLICIES.md** - Non-negotiable rules
- **ADOPTION_CHECKLIST.md** - Verification steps

---

## Key Concepts for AI Agents

### Health Check Integration
The governance system is tightly integrated with AHP (Agent Handshake Protocol):
- Health checks now validate governance compliance
- Adoption is verified before allowing operations
- Non-compliance blocks progression until fixed

### Semantic Triggering
AI agents should trigger governance validation when:
- User mentions "governance", "policy", "compliance"
- Creating new seedlings or specializations
- Deploying to production
- Running phases 3+

### Forced Adoption
Users cannot bypass governance:
- Manual mode disables health checks
- All operations require compliance verification
- Clear error messages guide remediation

---

## For Developers: Integration Points

### Extending Agent Handshake
See: `packages/agent_handshake.py` - `_layer_4_governance_health()`

### Adding Custom Rules
See: `adoption-rules/ENFORCEMENT_GUIDE.md` - Custom Rule Pattern

### Wizard Integration
See: `base-seedling/WIZARD_ADOPTION.md` - Phase 0 Integration

---

**Version**: 1.0 | **Status**:  Production Ready
**Last Updated**: 2026-04-26 | **Target**: AI Agent Optimization
