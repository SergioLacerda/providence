# C4 Level 2 — Containers

The major packages of Providence and their dependency relationships.

```mermaid
graph TB
    subgraph interfaces["interfaces layer"]
        providence_cli["providence_cli\n(Typer CLI)\nEntry point for humans\nand AI agents"]
        providence_wizard["providence_wizard\n(setup wizard)\nBootstraps new workspaces"]
    end

    subgraph features["features layer"]
        providence_skills["providence_skills\n(contract definitions)\nSkillRunResult, validation"]
        providence_adapters["providence_adapters\n(format adapters)\nOpenAI, LangChain, CrewAI"]
        providence_integration["providence_integration\n(external integrations)"]
    end

    subgraph core["core layer"]
        providence_runtime["providence_runtime\n(execution engine)\nSkillEngine, PolicyEngine,\nDriftDetector, Learning"]
        sdd_compiler["sdd_compiler\n(spec compiler)\nMarkdown → signed artifacts"]
        providence_core["providence_core\n(workspace utilities)\nGovernanceOrchestrator,\nDeploymentManager"]
        providence_telemetry["providence_telemetry\n(metrics & events)\nRuntimeEvent, JSONL sink"]
    end

    subgraph artifacts[".providence/ runtime state"]
        compiled["compiled/\nsigned governance artifacts\n(.json + .sig + .msgpack)"]
        skills_dir["skills/\nskill definitions\n(skill.yaml per skill)"]
        trust["trust/\nEd25519 key pair"]
    end

    subgraph specs["docs/spec/canonical/"]
        canonical["mandates + policies\n+ rules (source of truth)"]
    end

    providence_cli --> providence_runtime
    providence_cli --> providence_core
    providence_cli --> providence_skills
    providence_wizard --> providence_core
    providence_runtime --> providence_skills
    providence_runtime --> providence_telemetry
    providence_runtime --> providence_core
    providence_runtime -->|"reads at startup"| compiled
    providence_runtime -->|"reads skill defs"| skills_dir
    sdd_compiler --> providence_core
    sdd_compiler -->|"writes + signs"| compiled
    sdd_compiler -->|"reads"| canonical
    providence_adapters --> providence_skills
    providence_core -->|"verifies with"| trust

    classDef interfaceStyle fill:#dae8fc,stroke:#6c8ebf
    classDef featureStyle fill:#d5e8d4,stroke:#82b366
    classDef coreStyle fill:#fff2cc,stroke:#d6b656
    classDef artifactStyle fill:#f8cecc,stroke:#b85450
    classDef specStyle fill:#e1d5e7,stroke:#9673a6

    class providence_cli,providence_wizard interfaceStyle
    class providence_skills,providence_adapters,providence_integration featureStyle
    class providence_runtime,sdd_compiler,providence_core,providence_telemetry coreStyle
    class compiled,skills_dir,trust artifactStyle
    class canonical specStyle
```

## Layer Rules

Imports are strictly enforced by `pyproject.toml` `[tool.sdd.architecture]`:

- **interfaces** may import **features** and **core**
- **features** may import **core** only
- **core** packages do not import from **interfaces** or **features**

Violating these rules is caught by the architecture contract tests in `tests/contract/`.

## Scope Note — Publication Topology Is Not Shown Here

The diagram above is the **Python package import graph** enforced by the
layer rules — it does not represent runtime deployment or the published
site's URL topology. `apps/landing/` (Astro + React) and the Selector
(static assets compiled by `providence_wizard`'s `selector_compiler.py`) are not
Python packages that participate in this import contract, so they
intentionally aren't nodes in this graph.

The actual publication topology — `/` (Astro landing), `/docs/` (MkDocs),
`/selector/` (Selector), all assembled into one `build/site/` artifact by
`providence_pages` — is recorded in
`.analysis/archived/selector-landing-mkdocs-refinement-20260702-adr.md`,
not here. A dedicated deployment/publication diagram would be a separate
addition, not a change to this import-graph diagram.
