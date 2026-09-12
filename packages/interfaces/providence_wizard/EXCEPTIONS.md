# Line-Count Exceptions

Files in `src/providence_wizard/` currently over the repo's 200-line-per-file
convention (see `tools/architecture/validate_class_size.py`), tracked here per
the validation step of `wizard-structure-refactor-20260708`.

The 7 files originally scoped by that mission are now all ≤200 lines (see
`.analysis/pending/wizard-structure-refactor-20260708/tasks.md` for the pass
history). The files below were **not** part of that mission's scope — they
were already over 200 lines before this refactor started and are called out
here rather than split silently, since splitting them was not analyzed or
requested.

| File | Lines | Status |
|---|---|---|
| `orchestration/seedlings/governance_seeds.py` | 257 | Pre-existing, out of scope |
| `orchestration/phase6_output_validator.py` | 257 | Pre-existing, out of scope |
| `orchestration/deployer/template_deployer.py` | 242 | Pre-existing, out of scope |
| `application/workspace_runtime.py` | 220 | Pre-existing, out of scope |
| `orchestration/wizard/phase1_generator.py` | 208 | Pre-existing, out of scope |

If these need splitting, scope and analyze that as its own pending item
rather than folding it into this exceptions list without review.
