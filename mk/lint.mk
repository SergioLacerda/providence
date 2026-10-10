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

# --- Namespaced aliases ---
.PHONY: lint.py lint.py-fix lint.go lint.go-fix
lint.py: lint
lint.py-fix: lint-fix
lint.go: lint-go
lint.go-fix: lint-fix-go
