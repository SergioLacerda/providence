##@ Docs

docs-link-check: ## Check internal relative links in docs
docs-link-fix: ## Apply deterministic internal-link rewrites

DOCS_TASKS := docs-link-check docs-link-fix

.PHONY: $(DOCS_TASKS)
$(DOCS_TASKS):
	$(PYTHON) tools/maintenance/make_tasks.py $@

.PHONY: selector-artifact docs-build docs-serve
selector-artifact: ## Generate the machine-readable Selector artifact only
	$(PYTHON) tools/maintenance/make_tasks.py selector-artifact

docs-build: ## Build composed site (ILUSIONISTA + MkDocs + Selector artifact)
	$(PYTHON) tools/maintenance/make_tasks.py docs-build

docs-serve: docs-build ## Build full site (docs + selector) and serve on http://localhost:8000/providence/
	$(PYTHON) tools/maintenance/make_tasks.py docs-serve

# --- Namespaced aliases (additive, non-breaking; see proposal.md Decision D2) ---
.PHONY: docs.build docs.serve docs.link-check docs.link-fix
docs.build: docs-build
docs.serve: docs-serve
docs.link-check: docs-link-check
docs.link-fix: docs-link-fix
