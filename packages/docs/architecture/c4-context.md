# C4 Level 1 — System Context

Who uses Providence and what external systems does it interact with.

```mermaid
graph TB
    humanDev["👤 Human Developer\n(defines specs, reviews AI proposals,\napproves governance changes)"]
    aiAgent["🤖 AI Agent\n(Claude / Cursor / VSCode Copilot)\n(executes governed tasks,\nrequests skills, submits proposals)"]

    subgraph sddHarness["Providence"]
        direction TB
        core["Governance Engine\n(compile specs → enforce at runtime)"]
    end

    github["⚙️ GitHub\n(source control, CI/CD,\nCodeQL, Dependabot)"]
    pypi["📦 PyPI\n(dependency source)"]
    ide["🖥️ IDE\n(VSCode / Cursor / JetBrains)\n(reads .providence/seedlings for agent config)"]

    humanDev -->|"writes specs\ndocs/spec/canonical/"| sddHarness
    humanDev -->|"reviews & approves\nAI proposals"| sddHarness
    aiAgent -->|"providence ask / sdd run\nvia CLI or SDK"| sddHarness
    sddHarness -->|"governance verdict\n(allow / block / escalate)"| aiAgent
    sddHarness -->|"compliance events\n(.providence/runtime/compliance-events.jsonl)"| humanDev
    sddHarness <-->|"CI checks\n(lint, test, bandit, CodeQL)"| github
    sddHarness -->|"reads dependencies\nuv.lock"| pypi
    ide -->|"reads agent seeds\n.providence/seedlings/*.seed.json"| sddHarness
```

## Key Points

- **Human Developer** is the sole normative authority — specs in `docs/spec/canonical/` are the source of truth
- **AI Agents** interact exclusively through the `sdd` CLI and governed skill pipeline — they cannot modify specs directly
- **GitHub CI** enforces quality gates (lint, mypy, bandit, coverage, CodeQL) on every push
- **IDE integration** reads `.providence/seedlings/` to configure agent behavior in VSCode, Cursor, etc.
