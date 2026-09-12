##@ Plugins

.PHONY: plugin-claude
plugin-claude: ## Build the Claude Code standalone governance projection (dist/claude-standalone/)
	$(PYTHON) -m providence_cli claude build

.PHONY: plugin-copilot
plugin-copilot: ## Build the Copilot standalone governance projection (dist/copilot-standalone/)
	$(PYTHON) -m providence_cli copilot build

.PHONY: plugin-devin
plugin-devin: ## Build the Devin standalone governance projection (dist/devin-standalone/)
	$(PYTHON) -m providence_cli devin build --standalone

.PHONY: plugins-standalone
plugins-standalone: plugin-claude plugin-copilot plugin-devin ## Build all standalone governance projections (Claude, Copilot, Devin)

# --- Namespaced aliases (additive, non-breaking — see mk/misc.mk for the same pattern) ---
.PHONY: plugins.claude plugins.copilot plugins.devin plugins.standalone
plugins.claude: plugin-claude
plugins.copilot: plugin-copilot
plugins.devin: plugin-devin
plugins.standalone: plugins-standalone
