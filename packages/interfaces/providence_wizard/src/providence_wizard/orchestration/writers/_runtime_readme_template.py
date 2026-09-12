"""Template builder for .providence/runtime/README.md."""

from __future__ import annotations

from ._runtime_readme_integration_sections import _integration_section
from ._runtime_readme_maintenance_sections import (
    _best_practices_and_footer_section,
    _cache_invalidation_section,
    _optimization_tips_section,
    _troubleshooting_section,
)


def _overview_and_workflow_section(
    generated_at: str,
    language_context_lines: str,
    runtime_guideline_load_snippet: str,
) -> str:
    return f"""# .providence/runtime - Agent Pre-Cache Strategy

 **For AI Agents: Instructions on using .providence/source as pre-cache**

## Overview

This directory provides guidance on how to use `.providence/source/` as a **pre-cache**
mechanism for AI agents to reduce context token usage and improve performance.

**Generated**: {generated_at}

## Language Context

The wizard may capture language preference context for interaction surfaces.

{language_context_lines}Mandatory language rules still override preference context for:
- technical documentation
- governance artifacts
- CLI help and examples

## What is Pre-Caching?

Pre-caching is a strategy where:

1. Governance files are loaded **once** at the start of an agent session
2. Content is cached **in memory** (not re-read from disk)
3. Subsequent tasks **reference** the cached content instead of re-reading files

**Result**: Lower token usage, faster execution, consistent governance adherence.

## Pre-Cache Workflow

### Session Start (Agent Initialization)

```python
# When agent starts, load governance once
def init_agent():
    mandates = read_file('.providence/source/mandates/mandates.md')
{runtime_guideline_load_snippet}
    # Cache in agent memory/context
    agent.context['mandates'] = mandates
    agent.context['guidelines'] = guidelines
```

### Task Execution (Reference, Don't Re-Read)

```python
# During task execution, reference cached content
def execute_task(task):
    relevant_category = determine_category(task)
    guideline = agent.context['guidelines'][relevant_category]

    # Use guideline in task execution
    # DO NOT re-read from .providence/source
```

### Session End

- Cached content is available for entire agent session
- No disk reads for governance after initial load
- Only refresh if files are explicitly updated

"""


def build_runtime_readme(
    generated_at: str,
    language_context_lines: str,
    runtime_guideline_load_snippet: str,
) -> str:
    """Return the full .providence/runtime/README.md content."""
    return (
        _overview_and_workflow_section(
            generated_at, language_context_lines, runtime_guideline_load_snippet
        )
        + _integration_section()
        + _cache_invalidation_section()
        + _optimization_tips_section()
        + _troubleshooting_section()
        + _best_practices_and_footer_section()
    )
