##@ Lint

lint: ## Run linters (ruff check + format, mypy, bandit)
lint-fix: ## Auto-fix Python linting issues with ruff (local development)

LINT_TASKS := lint lint-fix

.PHONY: $(LINT_TASKS)
$(LINT_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

.PHONY: lint-go lint-fix-go
lint-go: ## Run golangci-lint on tools/sdd-compile
	$(PYTHON) tools/maintenance/make_tasks.py lint-go

lint-fix-go: ## Auto-fix Go lint issues (golangci-lint --fix)
	$(PYTHON) tools/maintenance/make_tasks.py lint-fix-go

.PHONY: lint-web lint-fix-web
lint-web: install-web ## Run npm audit fix, then landing app diagnostics (astro check)
	$(PYTHON) tools/maintenance/make_tasks.py lint-web

lint-fix-web: install-web ## Auto-fix landing app lint issues (no-op: astro check has no --fix)
	$(PYTHON) tools/maintenance/make_tasks.py lint-fix-web

# --- Namespaced aliases (additive, non-breaking; see proposal.md Decision D2) ---
.PHONY: lint.py lint.py-fix lint.go lint.go-fix lint.web lint.web-fix
lint.py: lint
lint.py-fix: lint-fix
lint.go: lint-go
lint.go-fix: lint-fix-go
lint.web: lint-web
lint.web-fix: lint-fix-web
