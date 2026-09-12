## Pull Request: SDD Architecture

**Describe your changes**

[Clear description of what this PR does]

---

## 🔏 Human Review Sign-off

Human Review: [Signed-off]

## ✅ Checklist

### TDD (M002 — mandatory, not customizable)

`.providence/source/mandates/mandates.md` requires writing tests before implementation
(Red-Green-Refactor). CI's "Validate Test Coverage (M002)" step runs
`tools/ci/check_tdd_diff_coverage.py`, which flags production changes with no
test file touched in the same diff.

- [ ] Every changed production file (`packages/*/src/**`) has a corresponding
      test change in this diff
- [ ] Tests were written/updated before (or alongside) the implementation, not
      as an afterthought
- [ ] `make test` passes locally
- [ ] `make coverage-strict` passes locally (core ≥ 90%, features/interfaces ≥ 70%)

### Health & Compliance

- [ ] `uv run python -m providence_cli governance validate --skip-handshake` passes
- [ ] No governance violations or mandate breaks

### Code Quality

- [ ] Type hints on all new functions
- [ ] Docstrings on classes and public methods where behavior isn't obvious
- [ ] No hardcoded values that should be config/env-driven
- [ ] `make lint` passes

### Documentation

- [ ] Updated relevant docs (READMEs, ADRs) if behavior or contracts changed
- [ ] Docstrings are clear and complete

### Git Workflow

- [ ] Branch name is descriptive: `feature/name` or `fix/description`
- [ ] Commits are atomic (one change per commit)
- [ ] Commit messages are clear and reference issues
- [ ] No merge conflicts
- [ ] All required CI workflows passing

---

## 🔍 Review Focus

**Key areas for reviewers to check:**

1. **TDD** — Does every production change carry a test in this diff?
2. **Governance** — Does this respect the active mandates (`.providence/source/mandates/mandates.md`)?
3. **Testing** — Are tests comprehensive and maintainable?
4. **Documentation** — Is the change clearly documented?

---

## 🚀 Deployment Notes

**Breaking changes?** [Yes/No]

**Database migrations?** [N/A/Yes - describe]

**New environment variables?** [N/A/List them]

**Related issues:** Closes #[number] or Relates to #[number]

---

## 💬 Questions for Reviewers

[Optional: Ask specific questions about the implementation]
