##@ Misc

.PHONY: hooks-install
hooks-install: ## Install local git hooks (Providence shell hooks + pre-commit)
	$(PYTHON) tools/maintenance/make_tasks.py hooks-install

governance-bootstrap: ## Generate full governance artifacts for local workspace

.PHONY: governance-bootstrap
governance-bootstrap:
	$(PYTHON) tools/maintenance/make_tasks.py $@

# P004 Pre-Delivery Quality Gate. Run this before every agent handoff.
# See: docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md
.PHONY: pre-delivery
pre-delivery: lint test ## [P004] Pre-Delivery Quality Gate: lint + test (run before handoff)
	@echo [PDQG] Pre-Delivery Quality Gate PASSED - ready for human review

# --- Namespaced aliases (additive, non-breaking; see proposal.md Decision D2) ---
.PHONY: misc.hooks-install misc.governance-bootstrap misc.pre-delivery
misc.hooks-install: hooks-install
misc.governance-bootstrap: governance-bootstrap
misc.pre-delivery: pre-delivery
