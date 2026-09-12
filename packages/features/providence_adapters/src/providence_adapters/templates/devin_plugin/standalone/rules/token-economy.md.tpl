# Token Economy

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

## Context Window Discipline

- Prefer concise, information-dense output over verbose explanations.
- When suggesting code, emit only the changed lines plus minimal surrounding
  context â€” not the entire file.
- Do not repeat the user's question back before answering.
- Do not emit disclaimers, preambles, or summaries unless explicitly asked.

## Prompt Efficiency

- Inline comments in generated code should be surgical: explain WHY, not WHAT
  (see `documentation.md`).
- Avoid generating boilerplate that a scaffold tool should handle (e.g., license
  headers, empty constructors, trivial getters/setters).
- When multiple approaches exist, present the recommended one first with a brief
  rationale â€” do not enumerate all alternatives unless asked.

## Response Budget

- Aim for the shortest correct answer that preserves context for follow-up
  questions.
- If a task requires more than ~200 lines of generated code, suggest splitting
  it into logical chunks and confirm the approach before generating.
