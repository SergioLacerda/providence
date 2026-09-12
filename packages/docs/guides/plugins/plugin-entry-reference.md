# Plugin Entry Reference

**Status:** Active
**Schema:** `.providence/plugins/plugin-entry.schema.yaml`
**Mandate:** M019 (Governance Federation)

---

## Required Fields

### `id`

- **Type:** string (kebab-case)

- **Description:** Unique plugin identifier. Must match the skill's declared id.

- **Example:** `brainstorming`

### `name`

- **Type:** string

- **Description:** Human-readable plugin name.

- **Example:** `Brainstorming Skill`

### `version`

- **Type:** string (semver)

- **Description:** Plugin version at time of registration.

- **Example:** `1.0.0`

### `risk`

- **Type:** enum — `read_only`|`read_write`|`controlled`

- **Description:**

  - `read_only`: plugin only reads context and produces analysis artifacts

  - `read_write`: plugin may write artifacts within declared scope

  - `controlled`: plugin requires explicit user approval before any write

### `skill_path`

- **Type:** string (absolute or home-relative path)

- **Description:** Path to the installed skill directory. The skill is not moved; this is the governance binding only.

- **Example:** `~/.claude/skills/brainstorming`

### `capabilities`

- **Type:** list of strings

- **Description:** What this plugin can do — declared capability identifiers.

- **Example:** `["exploratory_analysis", "option_discovery", "tradeoff_mapping"]`

### `governance`

- **Type:** object

- **Fields:**

  - `mode`(enum:`governed`|`compatible`|`standalone`) — determined at registration time

  - `respects_hard_mandates`(bool) — must be`true`for`governed` mode

  - `must_follow` (list of mandate IDs) — mandates the plugin commits to

---

## Optional Fields

### `handles`

- **Type:** list of strings

- **Description:** Task type classifications this plugin accepts. Used for routing.

- **Example:** `["exploratory_analysis", "design_session"]`

### `source_policy`

- **Type:** enum — `always`|`when_relevant`|`never`

- **Default:** `when_relevant`

- **Description:** When the plugin consults Providence governance sources (mandates, guidelines, ADRs).

### `output_schema`

- **Type:** string (file path)

- **Description:** Path to the artifact output schema, if the plugin produces structured output.

- **Example:** `.providence/contracts/analysis-result.schema.yaml`

### `registered_at`

- **Type:** string (ISO 8601)

- **Description:** Timestamp written by the agent at registration time.

### `registered_by`

- **Type:** string

- **Description:** Agent session or user identifier that performed registration.

---

## Complete Example Entry

```yaml
- id: brainstorming
  name: Brainstorming Skill
  version: "1.0.0"
  risk: read_only
  skill_path: ~/.claude/skills/brainstorming
  capabilities:
    - exploratory_analysis
    - option_discovery
    - tradeoff_mapping
    - design_session
  governance:
    mode: governed
    respects_hard_mandates: true
    must_follow:
      - M019
  handles:
    - exploratory_analysis
    - design_session
  source_policy: when_relevant
  registered_at: "2026-06-05T00:00:00Z"
  registered_by: "claude-sonnet-4-6"
```

---

## What Does NOT Go Here

- Internal Providence skills (`.providence/skills/`) — governed via `governance_adherence:`in`skill.yaml`

- Plugin-instance documentation (requirements-strategist, openspec, etc.) — created when the plugin is implemented

- Governance rules — these live in mandates, not in registry entries
