---
name: Bug Report
about: Report a bug or issue
title: "[BUG] "
labels: bug
assignees: ''

---

## 🐛 Description

**What is the bug?**

[Describe the issue clearly]

## 🔄 Steps to Reproduce

1. [First step]
2. [Second step]
3. [etc.]

## ❌ Expected Behavior

[What should happen]

## 📊 Actual Behavior

[What actually happens]

## 🩺 Diagnosis Information

**Run these commands and share output:**

```bash
# Health status
python3 packages/health_check.py --verbose

# Governance compliance
python3 packages/tools/governance_compliance.py --verify

# Agent handshake
python3 tools/governance/agent_handshake.py --verbose

# Python version
python3 --version

# Git status
git status && git log --oneline -3
```

## 📁 Environment

- **OS**: [Linux/macOS/Windows]
- **Python**: [version from above]
- **Git branch**: [main/develop/feature-X]
- **Project version**: [Phase X]

## 📸 Reproduction

[Include error messages, logs, or screenshots]

## ✅ Troubleshooting Attempted

- [ ] Ran: `python3 packages/health_check.py --force-recheck`
- [ ] Ran: `python3 packages/tools/governance_compliance.py --fix-steps`
- [ ] Cleared cache: `rm -f packages/.providence/agent_state.json`
- [ ] Pulled latest: `git pull origin main`
- [ ] Checked docs: TROUBLESHOOTING.md

## 🔗 Related Issues

[Link to related issues if applicable]

---

**Maintainers**:
- Use labels: `bug`, `priority: high/medium/low`
- Reference related docs
- Verify fix with: `python3 packages/health_check.py --force-recheck`
