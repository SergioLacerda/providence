---
applyTo: "**"
---

# Git Safety

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Never execute git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, branch deletion, etc.) autonomously via any tool or shell. Only suggest git commands in ready-to-run blocks for a human to execute.

Completing a task does not authorize a commit. Only an explicit human request does.

GitHub Copilot has no declarative permissions/config file to enforce this at the tool level (see `.github/copilot-instructions.md` Â§ Known limitations) â€” this rule is advisory only, not mechanically enforced the way an equivalent rule can be on providers with a permissions config file.
