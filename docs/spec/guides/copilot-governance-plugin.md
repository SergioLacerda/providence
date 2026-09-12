# Providence Governance Projection for GitHub Copilot

Generates a self-contained, zero-Providence-mention GitHub Copilot governance
configuration from curated, static content, in **Soft/Standalone** profile. This is
the Copilot analogue of `providence devin build --standalone` — same criteria, same
curated/generic (not repo-specific) content approach, adapted to Copilot's own real
file conventions.

This is a different mechanism from the existing per-skill Copilot adapter
(`AdapterGenerator`, writing `.github/prompts/*.prompt.md` from `.providence/skills/`,
wizard-integrated, Providence-branded) — see
`docs/spec/decisions/2026-05-16-multi-agent-adapters-design.md`. This projection is
additive and does not touch that integration.

## What Soft/Standalone means

- Works without Providence, without network, without any runtime dependency in
  the consuming project.
- Go-only for now (2026-08-18 scope decision) — see
  `.analysis/refined/20260818-plugin-language-scope-and-canonical-review/`.
- Content is curated and generic — not parsed from this repository's own `.providence/`
  governance sources — so it is reusable in any project, the same design choice
  `DevinPluginGenerator.generate_standalone()` already makes. It never mentions
  "sdd" (verified by test).
- Is never represented as equivalent to a connected, governed Providence session.

## Build

```bash
providence copilot build
# optional: providence copilot build --dest ./some/other/path
```

Or from Python:

```python
from providence_adapters.copilot import CopilotStandaloneGenerator

CopilotStandaloneGenerator().generate_standalone(output_dir=repo_root)
```

Output: `dist/copilot-standalone/` (a build artifact — same convention as
`dist/devin-standalone/`, never written into the project's real `.github/`
directly).

## Install

Copy the generated `.github/` contents into your project's real `.github/`
directory:

```bash
cp -r dist/copilot-standalone/.github/. .github/
```

GitHub Copilot picks up `.github/copilot-instructions.md` and
`.github/instructions/*.instructions.md` automatically — no separate install
command exists for Copilot the way `devin plugins install` exists for Devin.

## Bundle contents

| Path | Role |
|---|---|
| `.github/copilot-instructions.md` | Always-on repository custom instructions (completions + Chat + PR review) — index of the topic files below, plus the known-limitations disclosure |
| `.github/instructions/architecture.instructions.md` | `applyTo: "**"` — function/file size, naming, typing, dependency direction |
| `.github/instructions/git-safety.instructions.md` | `applyTo: "**"` — what the agent may and may not do with git |
| `.github/instructions/testing.instructions.md` | `applyTo: "**/*.go"` — write the test first |
| `.github/instructions/generated-artifacts.instructions.md` | `applyTo: "**"` — never hand-edit generated output |
| `.github/instructions/go.instructions.md` | `applyTo: "**/*.go"` — Go-specific style, anti-patterns, dependency version hygiene |
| `.github/instructions/documentation.instructions.md` | `applyTo: "**"` — what a comment is for |
| `.github/instructions/token-economy.instructions.md` | `applyTo: "**"` — context window discipline, prompt efficiency, response budget |

## Known limitations

Verified against GitHub's own documentation (see
`docs/spec/guides/copilot-plugin-provider-surface-evidence.md`) — these are
disclosed in the generated `.github/copilot-instructions.md` itself, not silently
dropped:

- **No lifecycle hook mechanism.** Unlike Devin's `.devin/hooks.v1.json`
  (`SessionStart` hook injecting context), Copilot has no documented runtime hook
  API. Nothing in this bundle depends on one.
- **No declarative config/permissions file.** Unlike Devin's `.devin/config.json`
  (`permissions.allow`/`permissions.deny`), Copilot has no single file that
  declares tool permissions. `git-safety.instructions.md` is therefore advisory
  only — it cannot be mechanically enforced the way an equivalent Devin rule can be
  via `config.json`'s `deny` list. `.github/workflows/copilot-setup-steps.yml`, if
  present in a project, is a build-environment provisioning file, not a governance
  surface, and is not part of this bundle.
- **`.github/copilot-instructions.md` vs. root `AGENTS.md` precedence is
  undocumented.** GitHub Copilot coding agent also reads a root (or nested)
  `AGENTS.md` file, but public documentation does not state precedence when both
  `.github/copilot-instructions.md` and `AGENTS.md` are present. This generator
  deliberately emits only `.github/copilot-instructions.md` to avoid
  duplicate/conflicting always-on content. Revisit if GitHub documents precedence
  in the future.
- This bundle has been verified structurally only — it has not yet been tested
  inside a real Copilot Chat or coding-agent session. Copy it into a real
  repository's `.github/` and confirm Copilot picks up the instructions before
  treating this as production-ready.
