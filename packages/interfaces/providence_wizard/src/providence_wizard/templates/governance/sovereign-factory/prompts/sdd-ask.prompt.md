---
description: Query SDD governance context
mode: agent
---

Query the SDD governance context with the user's question.

Execute in the terminal:
```bash
providence runtime status
providence governance validate
providence ask --full "$QUERY"
```

Replace `$QUERY` with the user's question.

HARD contract for this command:
- Run preflight in order (`providence runtime status` then `providence governance validate`).
- If preflight fails, do not continue; return governance-blocked status.
- Only continue to `providence ask --full` when preflight is healthy.

Response contract:
- Show `fingerprint`, `context_source`, and `mandates_loaded` from runtime output.
- Treat `.providence` runtime artifacts as source of truth for these fields.

PROVIDENCE GOVERNANCE CHECK
- Always end responses with this compact footer:
  `PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`

Audit JSON policy:
- `.providence/compiled/audit/*.json` is human/audit oriented.
- Agents should prefer `.providence/source/*` for human-readable governance context and
  runtime checks (`providence runtime status`, `providence ask --full`) for operational state.
