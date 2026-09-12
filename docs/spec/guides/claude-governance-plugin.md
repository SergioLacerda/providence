# Providence Governance Projection for Claude Code

Generates a self-contained, zero-Providence-mention Claude Code governance configuration
from curated, static content, in **Soft/Standalone** profile. This is the Claude
Code analogue of `providence devin build --standalone` and `providence copilot build` — same
criteria, same curated/generic (not repo-specific) content approach, adapted to
Claude Code's own real file conventions.

This is a different mechanism from two pre-existing, unrelated Claude-specific
integrations: the per-skill `AdapterGenerator` (writing `.claude/commands/*.md`
from `.providence/skills/`, wizard-integrated, Providence-branded), and the `providence governance
generate` wizard subsystem that produces this repository's own root `CLAUDE.md`.
This projection is additive and does not touch either.

## What Soft/Standalone means

- Works without Providence, without network, without any runtime dependency in
  the consuming project.
- Content is curated and generic — not parsed from this repository's own `.providence/`
  governance sources — so it is reusable in any project, the same design choice
  `DevinPluginGenerator.generate_standalone()` and
  `CopilotStandaloneGenerator.generate_standalone()` already make. It never
  mentions "sdd" (verified by test).
- Is never represented as equivalent to a connected, governed Providence session.

## Two scope decisions (see the mission ADR for full rationale)

- **Decision D-1:** "standalone" here means a plain project-config bundle
  (`CLAUDE.md` + `.claude/rules/*.md` + `.claude/settings.json`), not an
  installable `.claude-plugin/plugin.json` marketplace plugin. Claude Code
  supports both systems; this generator only targets the former, by symmetry with
  every other "standalone" generator in this package.
- **Decision D-2:** the generated `.claude/settings.json` ships a `permissions`
  block only — no `hooks` block — by symmetry with Devin's own standalone-vs-plugin
  split, where hooks exist only in Devin's *plugin* bundle, never in its
  standalone mode.

## Build

```bash
providence claude build
# optional: providence claude build --dest ./some/other/path
```

Or from Python:

```python
from providence_adapters.claude import ClaudeStandaloneGenerator

ClaudeStandaloneGenerator().generate_standalone(output_dir=repo_root)
```

Output: `dist/claude-standalone/` (a build artifact — same convention as
`dist/devin-standalone/` and `dist/copilot-standalone/`, never written into the
project's real root `CLAUDE.md`/`.claude/` directly).

## Install

Copy the generated files into your project's real root:

```bash
cp -r dist/claude-standalone/CLAUDE.md dist/claude-standalone/.claude .
```

Claude Code picks up `CLAUDE.md` (read as persistent context at session start) and
`.claude/rules/*.md` / `.claude/settings.json` automatically — no separate install
command exists for Claude Code the way `devin plugins install` exists for Devin.

## Bundle contents

| Path | Role |
|---|---|
| `CLAUDE.md` | Always-on persistent context, read at session start — index of the rule files below |
| `.claude/rules/architecture.md` | Function/file size, naming, typing, dependency direction |
| `.claude/rules/git-safety.md` | What the agent may and may not do with git |
| `.claude/rules/testing.md` | Write the test first |
| `.claude/rules/generated-artifacts.md` | Never hand-edit generated output |
| `.claude/rules/go.md` | Go-specific style, anti-patterns, dependency version hygiene |
| `.claude/rules/documentation.md` | What a comment is for |
| `.claude/rules/token-economy.md` | Context window discipline, prompt efficiency, response budget |
| `.claude/settings.json` | `permissions.allow`/`permissions.deny` — the same operations `git-safety.md` describes, enforced at the tool level |

## Known limitations

Verified against Claude Code's own documentation (see
`docs/spec/guides/claude-plugin-provider-surface-evidence.md`):

- Unlike Copilot's standalone projection, no structural-gap disclosure is needed
  here — Claude Code's real surface has a confirmed equivalent for every element
  of Devin's standalone bundle.
- Whether `.claude/rules/*.md` supports any form of per-file, path-scoped loading
  (the way Copilot's `.github/instructions/*.instructions.md` uses an `applyTo`
  glob) was not confirmed. Treat each rule file as loading in full for the
  session until a targeted follow-up check confirms otherwise.
- This bundle has been verified structurally and by automated test only — it has
  not yet been tested inside a real Claude Code session. Copy it into a real
  project and confirm Claude Code picks up `CLAUDE.md` / `.claude/rules/*.md` /
  `.claude/settings.json` before treating this as production-ready.
