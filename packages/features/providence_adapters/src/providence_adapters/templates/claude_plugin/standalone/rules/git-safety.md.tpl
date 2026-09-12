# Git Safety

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Never execute git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, branch deletion, etc.) autonomously via any tool or shell. Only suggest git commands in ready-to-run blocks for a human to execute.

Completing a task does not authorize a commit. Only an explicit human request does.

This is enforced, not just advised â€” see `.claude/settings.json`'s `permissions.deny` list, which blocks the same operations at the tool level.
