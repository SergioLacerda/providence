# Project Governance

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

## Governance Model

This project uses file-based soft governance. Rules are advisory â€” they guide
your behavior but are not fully enforced at the tool level (see `git-safety.md`
for the one exception: `.claude/settings.json`'s `permissions.deny` list). Your
compliance depends on reading and following the rule files below.

## Active Rule Categories

| Category | File | Scope |
|----------|------|-------|
| Architecture | `.claude/rules/architecture.md` | All files |
| Git Safety | `.claude/rules/git-safety.md` | All files |
| Testing | `.claude/rules/testing.md` | Code files |
| Generated Output | `.claude/rules/generated-artifacts.md` | All files |
| Go Style | `.claude/rules/go.md` | `*.go` |
| Documentation | `.claude/rules/documentation.md` | All files |
| Token Economy | `.claude/rules/token-economy.md` | All files |

## Compliance Priority

When rules conflict, resolve by this priority order:

1. Git safety (never auto-commit)
2. Architecture (boundaries, naming, typing, error handling, security)
3. Testing (test-first evidence)
4. Language-specific rules
5. Documentation
6. Token economy

## Self-Check (before completing any task)

Before considering a task done, verify:

- [ ] No git state-modifying commands were executed autonomously
- [ ] New code follows the architecture rules (size, naming, typing, deps, error handling, security)
- [ ] Changes have test-first evidence (test written/updated alongside code)
- [ ] No generated files were hand-edited
- [ ] Error messages include the offending value and expected shape
- [ ] Output is concise â€” no unnecessary preambles or disclaimers

This is an advisory checklist, not a blocking gate.

Permissions are configured in `.claude/settings.json`.

These files are a generated starting point. Edit them directly to fit this project â€” there is no external source they must stay in sync with.
