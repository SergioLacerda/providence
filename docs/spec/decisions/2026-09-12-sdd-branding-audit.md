# Residual SDD / sdd-* Branding Audit

Mission: `20260912-providence-profile-brand-refinement`, Task 3.

## Method

```bash
rg -n --hidden -g '!.venv' -g '!.git' -g '!.analysis' -g '!*.pyc' -g '!node_modules' \
   '\bSDD\b|sdd-[a-z-]+' packages docs AGENTS.md GEMINI.md .providence
```

2,333 matching lines. Classified below by pattern group (per `design.md` Decision 3),
not line-by-line — most matches are one of a small number of repeating identifiers.

## Important nuance found during classification

**"SDD" is not purely a legacy brand name — it is also the methodology acronym
("Spec-Driven Development"), which this project's own `CLAUDE.md` still uses
correctly today**: *"This Claude workspace is governed by `.providence/` (Spec
Driven Development artifacts)"*. Providence is the **product/brand**; SDD is the
**methodology** it implements. These are two different, legitimately coexisting
terms — blindly replacing every "SDD" with "Providence" would conflate them and
produce wrong sentences like "governed by (Providence artifacts)" losing the
methodology reference entirely.

This means the bare-word `\bSDD\b` matches split into two very different buckets
that must be classified separately, unlike the `sdd-*` id matches which are more
uniform:

- **Methodology reference** ("Spec-Driven Development (SDD)", "the SDD
  methodology") → `unrelated` / keep. ~22 explicit "Spec-Driven Development"
  expansions found; likely more implicit ones.
- **Product/tool name used as if "SDD" were the product** ("the SDD CLI",
  "SDD Governance:", "SDD skill catalog", "reinstall the SDD CLI from...",
  "SDD wizard already generates...") → `branding_drift`, should say "Providence
  CLI" / "Providence governance" / "Providence wizard". ~143 lines matched this
  pattern (undercount — many product-name uses don't fit that exact regex,
  e.g. "No. SDD sits between your team's decisions...", "Does SDD replace my
  framework?").

## Classification by pattern group

| Pattern | Count (approx.) | Bucket | Notes |
| --- | --- | --- | --- |
| `sdd-ask`, `sdd-diagnose`, `sdd-correct`, `sdd-converge`, `sdd-organize`, `sdd-pipeline`, `sdd-validate-governance`, `sdd-review-architecture`, `sdd-compress-context`, `sdd-harness` | ~830 | `compatibility_alias` | Real skill/command registry ids. Already display-branded via Task 1/2's `resolve_profile_label`. Keep verbatim per `proposal.md` compatibility policy — no removal date set. |
| `sdd-compile`, `sdd-compile-{linux,darwin,windows}-{amd,arm}...` | ~250 | `internal_legacy_path` | Go compiler binary and its per-platform release artifact names (`tools/sdd-compile/`, CI release assets). Renaming these breaks release automation and published binary names — separate, higher-risk change requiring its own approval; out of scope here. |
| `sdd-runtime`, `sdd-validation`, `sdd-governance`, `sdd-commands`, `sdd-api` | ~100 | `internal_legacy_path` | Internal Go package/module paths under `tools/sdd-compile/`. Same rationale as above. |
| `sdd-ink-`, `sdd-indigo-`, `sdd-green-`, `sdd-blue-` | ~90 | `internal_legacy_path` — **confirmed** (`20260912-providence-brand-migration-residual`, Task 2) | Real CSS custom-property names in `docs/app/site-header.css` (and its two sibling copies at `packages/interfaces/providence_wizard/src/providence_wizard/templates/selector/site-header.css` and `apps/landing/public/shared/site-header.css`) — e.g. `--sdd-indigo-500`, `--sdd-blue-400`. Never rendered as visible text; already paired with Providence-branded `.providence-site-header-*` class names in the same file. Renaming would touch three synced copies for zero user-visible benefit — left as-is. |
| `sdd-theme` | ~2 | `internal_legacy_path` — **confirmed** | The literal filename `docs/app/sdd-theme.css` (self-referenced in its own header comment and in `mkdocs.yml`'s `extra_css:`), and the `localStorage.getItem("sdd-theme")` persistence key in `providence_wizard`'s `templates/selector/selector.js`. A file/storage-key rename, not a text-content rename — out of scope here. |
| `sdd-zeta`, `sdd-one`, `sdd-legacy`, `sdd-custom` | ~30 | `unrelated` — **confirmed** | Synthetic placeholder skill/command ids used only inside test fixtures (`test_governance_reconcile_registries.py`, `test_skills_resolver_seeds.py`, `test_prompt_commands_builders.py`) to test registry-reconciliation and stale-seed-cleanup logic — equivalent to `foo`/`bar`, not real product identifiers. |
| `sdd-coding-practices`, `sdd-test-project` | ~10 | `internal_legacy_path` | `rules/sdd-coding-practices.md` is a real generated Devin-plugin filename (same category as `rules/sdd-soft-governance-behavior.md`, already reviewed and left as-is). `/tmp/sdd-test-project` is a cosmetic example temp-directory name in `docs/spec/guides/operational/DEPLOYMENT.md`'s deployment-test instructions — trivially renameable, zero functional impact, low priority. |
| `sdd-rust`, `sdd-nodejs`, `sdd-go` | ~18 | **new finding**, `unrelated` (speculative/unbuilt) | Not adapter template files — these are *planned, not-yet-built* package names in `docs/spec/guides/adoption/MULTI-LANGUAGE-EXPLORATION.md` and `INDEX.md`'s roadmap ("⏳ Node.js support (sdd-nodejs)", "sdd-go/ — Go Implementation (v3.0)", checklist items still unchecked). Nothing exists to rename yet; if/when this roadmap work actually starts, whether the new packages should be named `sdd-*` or `providence-*` is an open naming question worth deciding *then*, not retrofitted onto a doc describing work that hasn't started. |
| Bare `SDD` as methodology ("Spec-Driven Development (SDD)") | ~22+ | `unrelated` — keep | Legitimate methodology acronym, distinct from the Providence product brand. |
| Bare `SDD` as product name ("the SDD CLI", "SDD Governance:", "SDD wizard", "SDD skill catalog", "Does SDD replace...") | ~150-300 (undercounted by regex) | `branding_drift` | Concentrated in `docs/guides/*.md` (FAQ, CLIENT_ONBOARDING, RUNTIME_API_INTEGRATION, plugin docs), `docs/spec/reference/commands/cli.md`, `docs/incidents/PLAYBOOKS.md`, `docs/runbooks/*.md`, `GEMINI.md`, `docs/QUICKSTART_AGENT.md`. Real user-facing rename candidates, mirrored 1:1 into `packages/docs/**`. |
| `docs/adr/**`, `docs/plans/**`, historical ADR text | ~90 | `historical_reference` | Never edit — records what was true when written. |

## Recommendation for Task 4

This is a substantially larger effort than the original `proposal.md` scoped
(it assumed only the footer profile label needed attention). Two sub-efforts,
independent and separately reviewable:

1. **Small, mechanical**: fix the ~150-300 "SDD" used as a product-name
   stand-in for "Providence" in `docs/**` (+ mirror to `packages/docs/**`).
   Each fix is a sentence-level edit, not a token substitution — "the SDD CLI"
   → "the Providence CLI", "SDD wizard" → "Providence wizard", etc. Requires
   reading each sentence, not a blind `sed`.
2. **Explicitly out of scope for this mission** (needs separate approval):
   renaming `tools/sdd-compile` itself, its release binary naming
   (`sdd-compile-linux-amd64`, ...), and CI/release workflow references to
   those names — this is the Go compiler product, its own component with its
   own release process, not covered by `tasks.md`'s allowed scope list.

Given the size, recommend doing (1) as its own reviewed batch rather than
folding it into Task 1/2's commit — already merged and tested independently.

## Task 4 outcome (2026-09-12)

Fixed, sentence-by-sentence, with the full test suite re-run green after every
batch:

- **Real functional bugs** (not cosmetic — the named command doesn't exist
  under that name): `.claude/sdd-bootstrap.sh` → renamed
  `.claude/providence-bootstrap.sh`, fixed `command -v sdd` → `command -v
  providence` (source template + generator + test + the live root file +
  `.providence/runtime/direct-root-manifest.json` key). `docs/incidents/PLAYBOOKS.md`
  (10 occurrences of `sdd bootstrap`/`sdd metrics summary`),
  `docs/runbooks/client-bootstrap-path-shadowing.md` (rewritten — every command
  in it used the dead `sdd` binary), `docs/guides/RUNTIME_API_INTEGRATION.md`
  (2×), `docs/spec/guides/devin-governance-plugin.md` /
  `claude-governance-plugin.md` / `copilot-governance-plugin.md` (`sdd devin
  build` / `sdd claude build` / `sdd copilot build` examples).
- **Live CLI `--help` text** (more visible than docs): `providence init`,
  `install`, `wizard`, `scaffold`, `ask`, `devin build` all said "SDD
  governance/workspace/skills/CLI" in their Typer help strings — fixed in
  `providence_cli/commands/*.py` and `_command_specs.py`, tests updated where
  they asserted the old strings.
- **A live runtime string**: `providence_cli/commands/_ask_backend/_budget.py`
  emitted `[SDD] BUDGET BREACH: ...` to real users on context-budget breach —
  now `[Providence] BUDGET BREACH: ...`.
- **A generated artifact template** (not just the doc describing it): the Devin
  plugin's `AGENTS.md.tpl` — the file real Devin sessions read — had the same
  branding drift as its documentation (title, "Connected SDD hard policy",
  "Embedded SDD snapshot", "SDD skill catalog", `sdd` CLI assumption). Fixed
  alongside its doc and the one test asserting its generated text.
- **Docs prose** (with mirrors synced to `packages/docs/`): `GEMINI.md`
  bootstrap title (via its template, `providence_wizard/orchestration/seedlings/_renderer.py`),
  `docs/spec/reference/commands/cli.md`, `docs/guides/CLIENT_ONBOARDING.md`,
  `docs/QUICKSTART_AGENT.md`, `docs/runbooks/windows-standalone-compiler-skew.md`,
  `docs/spec/guides/integration/STEP_5.md` and `STEP_6.md`, the
  `docs/spec/guides/adoption/*ADOPTION*.md` family ("SDD LITE/FULL" →
  "Providence LITE/FULL", kept consistent across all four files that use the
  term), `docs/guides/plugins/plugin-governance-overview.md` /
  `plugin-entry-reference.md` / `registration-protocol.md`,
  `docs/cognition/decision-models/CONFIDENCE_THRESHOLD.md`,
  `docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md` (a
  compiled governance source — triggered a `providence governance compile`
  re-run, verified clean), `docs/guides/TECHNICAL_GUIDE.md`.

**Deliberately left alone** (methodology usage, matching the nuance above, not
re-litigated per file): `docs/guides/FAQ.md`, `docs/spec/guides/operational/CORE__START_HERE.md`,
`docs/indices/search-keywords.md` (a search-keyword index — removing "SDD" as a
keyword would reduce findability for that legacy search term), `docs/.ai-index.md`,
`docs/guides/plugins/registration-protocol.md`'s one remaining ambiguous
mention, and the "learning SDD" / "SDD is collaborative" phrasing left in the
adoption docs after the LITE/FULL tier-name fix.

**Found but explicitly not fixed — needs a decision, not a rename**:
`docs/spec/guides/operational/OPERATIONS.md` describes an entirely different,
long-obsolete architecture (`.providence-wizard/`, `.providence-core/`,
`compile_artifacts.py`, `python -m cli`, `sdd new --project-name`, `sdd project
validate` — none of these exist in the current codebase; `providence` has no
`new` or `project` subcommand at all). Renaming its "SDD" mentions to
"Providence" would make a stale document look freshly maintained without
fixing the actual problem. This needs either a full rewrite against the
current architecture or archival, not a branding pass — flagging for a
separate task.
