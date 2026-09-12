# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x     | :white_check_mark: |
| < 3.0   | :x:                |

## Threat Model

`providence` processes user-supplied specs (YAML/TOML), executes wizard scripts, and
compiles governance artifacts. The primary attack surface is **input parsing**:

- Path traversal in spec source roots and compiled output paths
- Arbitrary code execution via malformed wizard templates
- Injection via governance spec values rendered into generated files

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities via GitHub's private [Security Advisories](https://github.com/SergioLacerda/providence/security/advisories/new).

Please include:

1. Description of the vulnerability and affected component
2. Steps to reproduce
3. Potential impact assessment
4. Suggested fix (optional)

### Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | 48 hours |
| Initial assessment | 5 business days |
| Patch / mitigation | 30 days (critical), 90 days (moderate) |
| Public disclosure | After patch is released |

## Security Practices

- SAST: `bandit -r packages/ -ll` runs in `make lint` and CI
- Dependencies: Dependabot monitors `pyproject.toml` weekly (`.github/dependabot.yml`)
- No credentials or secrets are stored in this repository
- Generated artifacts (`generated/`) contain only compiled governance specs — no executable code
