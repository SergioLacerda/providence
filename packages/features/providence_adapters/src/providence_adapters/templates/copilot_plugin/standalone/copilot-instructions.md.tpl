# Project Governance

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

## Governance Model

This project uses file-based soft governance. Rules are advisory â€” they guide
your behavior but are not mechanically enforced at the tool level (see
"Known limitations" below). Your compliance depends on reading and following
the instruction files below.

## Active Rule Categories

| Category | File | Scope |
|----------|------|-------|
| Architecture | `architecture.instructions.md` | All files |
| Git Safety | `git-safety.instructions.md` | All files |
| Testing | `testing.instructions.md` | `*.go` |
| Generated Output | `generated-artifacts.instructions.md` | All files |
| Go Style | `go.instructions.md` | `*.go` |
| Documentation | `documentation.instructions.md` | All files |
| Token Economy | `token-economy.instructions.md` | All files |

GitHub Copilot applies each file automatically to matching files, based on its
own `applyTo` frontmatter â€” no action is required to activate them beyond
their presence in this repository.

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

## Known limitations (verified, not an oversight)

GitHub Copilot's real customization surface (verified against `docs.github.com` and
`github.blog`; see the provider-surface evidence note this bundle was generated
against) has no documented equivalent for two governance mechanisms other providers
support:

- **No lifecycle hook mechanism.** There is no Copilot equivalent of a
  session-start or pre/post-action hook that can inject additional context or block
  an operation at runtime. Anything that would need that capability cannot be
  expressed in this bundle.
- **No single declarative config/permissions file.** There is no Copilot equivalent
  of a project-level file that declares tool permissions or a deny-list of
  operations. `.github/workflows/copilot-setup-steps.yml`, if present in this
  repository, configures the coding agent's *build environment* only (tools,
  runtimes, dependencies) â€” it is not a governance or permissions surface, and this
  bundle does not treat it as one.

Because there is no permissions file to enforce it mechanically,
`git-safety.instructions.md` is advisory only â€” it cannot be mechanically enforced
the way an equivalent rule can be via a provider with a declarative permissions
file.

These are documented gaps, not files this generator failed to produce.

These files are a generated starting point. Edit them directly to fit this project
â€” there is no external source they must stay in sync with.
