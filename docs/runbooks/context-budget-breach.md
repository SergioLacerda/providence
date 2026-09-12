# Context Budget Breach

Verification state: documented

## Symptoms

- Context utilization enters RED or BREACH.
- `providence ask --full` exits with a budget breach.
- The agent begins loading broad documentation instead of task-specific leaves.
- Output quality degrades because too much context was loaded.

## Diagnosis

1. Identify the active budget zone.
2. Confirm the task PATH and expected context size.
3. Check whether the agent loaded entire directories instead of targeted files.
4. Prefer path-based context loading through indexes and task classification.

## Resolution Steps

1. Stop loading non-essential context.
2. Reclassify the task using PATH A-F.
3. Load only the relevant leaf docs for that PATH.
4. If in YELLOW or RED, apply compression before loading more context.
5. If in BREACH, stop further context loading and restart with a smaller scope.

## Rollback

1. Discard oversized context bundles.
2. Restart the task from the smallest valid PATH.
3. Keep archived/history directories out of execution context unless the task is
   explicitly research-oriented.

## Post-Incident

- Record the over-load pattern if it recurs.
- Update path routing or search keywords when agents repeatedly load the wrong docs.

## Evidence To Attach

- budget zone/utilization
- list of files loaded
- selected PATH and reason
- compressed context summary if generated

## Sources

- `docs/guides/TECHNICAL_GUIDE.md`
- `docs/cognition/context-loading/CONTEXT_BUDGET.md`
- `docs/cognition/context-loading/COMPRESSION.md`
- `docs/incidents/PLAYBOOKS.md`
