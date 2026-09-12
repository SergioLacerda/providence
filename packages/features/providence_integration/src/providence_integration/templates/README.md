# Templates for New Projects

This directory should contain templates that new projects copy.

```
templates/
├── .spec.config                    ← Main config file (spec-architecture location)
├── .github/
│   └── copilot-instructions.md     ← Agent entry point (GitHub Copilot)
├── .vscode/
│   └── ai-rules.md                 ← VS Code AI rules
├── .cursor/
│   └── rules/spec.mdc              ← Cursor IDE rules
└── tests/unit/specs_ia_units/
    ├── __init__.py
    ├── README.md                   ← Explains SDD compliance tests
    └── test_layer_isolation.py     ← Example test (copy & customize)
```

## Usage

When creating a new project:

```bash
# Copy all templates
cp -r /home/sergio/dev/spec-architecture/templates/* your-project/

# Edit only .spec.config
vi your-project/.spec.config  # Set spec_path

# Commit
cd your-project && git add . && git commit -m "🔧 Initialize SPEC"
```

## What Each File Does

| File | Purpose | Edit? |
|------|---------|-------|
| `.spec.config` | Tells agents where spec-architecture is | ✏️ YES (spec_path) |
| `.github/copilot-instructions.md` | GitHub Copilot entry point | ❌ NO (generic) |
| `.vscode/ai-rules.md` | VS Code AI rules | ❌ NO (generic) |
| `.cursor/rules/spec.mdc` | Cursor IDE rules | ❌ NO (generic) |
| `tests/unit/specs_ia_units/README.md` | Explains architecture tests | ❌ NO (generic) |
| `tests/unit/specs_ia_units/test_layer_isolation.py` | Example test | ✏️ YES (project-specific) |
