# SDD Soft Governance Behavior (curated, Soft/Standalone)

Ruleset version: `{{ soft_governance_ruleset_version }}`

This is a small, manually-curated selection of CLI-independent behavioral rules distilled from the source Providence project's `.providence/agent-instructions.md` and `docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`. It is not auto-generated from those files and does not track them byte-for-byte â€” see `metadata/provenance.json` for the ruleset version. It intentionally omits anything that depends on a live `sdd` CLI connection (handshake, execution gate, fingerprint checks, `providence runtime status`/`providence governance validate`/`providence test run`/`providence lint run`) â€” those only apply in Hard/Connected mode, which this plugin does not implement.

## Rule 1 â€” Git safety

Never execute git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, branch deletion, etc.) autonomously via any tool or shell. Only suggest git commands in ready-to-run blocks for a human to execute. Completing a task does not authorize a commit â€” only an explicit human request does.

## Rule 2 â€” Escalate on incomplete or inconsistent governance context

If the governance information available to you is incomplete or internally inconsistent, stop. Do not guess or interpolate. Escalate to a human with the specific problem you found, rather than proceeding on an assumption.

## Rule 3 â€” Mandates outrank guidelines

Mandates (HARD) are non-negotiable and always take precedence. Guidelines and policies (SOFT) must also be applied, but only when they do not conflict with a mandate.

## Rule 4 â€” Follow the 7-phase work flow

Structure non-trivial work as: check context and state, load applicable rules, choose a scope appropriate to the task's size, load only the context that task needs, implement with tests, validate before calling it done, and leave a clear checkpoint of what changed. Skipping straight to implementation without the earlier phases is a common failure mode, not a shortcut.
