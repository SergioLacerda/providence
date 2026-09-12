# Cross-platform note: Make targets should run on Linux and Windows.
# Recipes delegate shell-sensitive logic to tools/maintenance/make_tasks.py.
#
# No implicit suffix rules are used in this Makefile.
MAKEFLAGS += --no-builtin-rules --no-builtin-variables
#
# Use uv run if uv is available; fall back to direct execution (e.g. inside Docker)
VENV_PYTHON := $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe))
DOCKER_BUILD_FLAGS ?=
ifeq ($(OS),Windows_NT)
  UV := $(firstword $(shell powershell -NoProfile -Command '$$cmd = Get-Command uv -ErrorAction SilentlyContinue; if ($$cmd) { $$cmd.Source }'))
else
  UV := $(shell command -v uv 2>/dev/null)
endif

ifeq ($(strip $(VENV_PYTHON)),)
  ifeq ($(strip $(UV)),)
    PYTHON = $(error no .venv found and uv is not installed. Run `make install` first)
  else
    PYTHON := uv run python
  endif
else
  PYTHON := $(VENV_PYTHON)
endif

# Same workspace src dirs as [tool.pytest.ini_options].pythonpath in
# pyproject.toml — needed by any recipe that runs a workspace package via
# `python -m` (relative imports require -m, so a per-script sys.path guard
# like tools/maintenance/lint_all.py's isn't an option there) without relying
# on those packages being uv-sync-installed as editables first.
WORKSPACE_PYTHONPATH := packages/core/providence_core/src:packages/core/providence_runtime/src:packages/core/providence_telemetry/src:packages/features/providence_integration/src:packages/features/providence_adapters/src:packages/features/providence_skills/src:packages/features/providence_pages/src:packages/interfaces/providence_wizard/src:packages/interfaces/providence_cli/src

.DEFAULT_GOAL := help

# Targets are grouped by affinity into mk/*.mk, included below. Each file
# declares its own .PHONY list and documents its targets with a trailing
# `## description` comment, picked up by `help`'s self-documenting scan.
# See .analysis/refined/20260809-makefile-worldclass-refactor/design.md.
include mk/python.mk
include mk/lint.mk
include mk/docs.mk
include mk/web.mk
include mk/go.mk
include mk/release.mk
include mk/docker.mk
include mk/plugins.mk
include mk/misc.mk

.PHONY: help
help: ## Show this help
	$(PYTHON) tools/maintenance/make_tasks.py help
