---
name: Feature Request
about: Suggest a new feature or enhancement
title: "[FEATURE] "
labels: enhancement
assignees: ''

---

## 📋 Description

**What feature or enhancement are you proposing?**

[Describe the feature clearly]

## 🎯 Motivation

**Why is this needed?**

[Explain the business or technical need]

## ✅ Acceptance Criteria

- [ ] Feature is implemented
- [ ] Health checks pass (`python3 packages/health_check.py`)
- [ ] Governance compliant (`python3 packages/tools/governance_compliance.py --verify`)
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] Performance benchmarked (if applicable)

## 🔍 Governance Checklist

- [ ] Does not violate mandatory policies
- [ ] Follows code quality standards (type hints, docstrings, etc.)
- [ ] Aligns with enforcement level (STRICT/STANDARD/PERMISSIVE)
- [ ] Includes error handling and recovery

## 📚 Related Documentation

Link to relevant docs:
- [Health Check Guide](../../docs/HEALTH_CHECK_GUIDE.md)
- [Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)
- [Governance Implementation](../../packages/.providence-wizard/templates/governance/base-seedling/GOVERNANCE_IMPLEMENTATION.md)

## 🚀 Implementation Notes

[Any additional context for implementation]

---

**Contributor**: Please ensure your changes:
1. Maintain health (10/10 checks passing)
2. Maintain compliance (100% governance compliance)
3. Follow code patterns in `docs/ARCHITECTURE.md`
4. Include tests in `tests/`
5. Pass: `python scripts/git_hooks.py install` (local validation)
