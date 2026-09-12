# SDD v3.1 Extension Framework - Phase 8 Workstream 4

Specialized domain extensions for SDD v3.0. Create custom mandates and guidelines for your specific use case.

**Status:**  Phase 8 Workstream 4 (Week 3-4)

## Overview

The Extension Framework allows you to extend SDD with domain-specific mandates and guidelines while maintaining core principles. Perfect for:

- Game development systems (narrative engines, game masters)
- AI systems (reasoning, safety guidelines)
- Financial systems (compliance, risk management)
- Healthcare systems (HIPAA, data protection)
- Custom enterprise architectures

## Quick Start

### 1. Create an Extension

```python
from extensions.framework import (
    BaseExtension,
    CustomMandate,
    CustomGuideline,
    ExtensionMetadata,
    Category,
)


class MyExtension(BaseExtension):
    metadata = ExtensionMetadata(
        name="My Domain Extension",
        version="1.0.0",
        author="Your Name",
        description="Custom SDD for my domain",
        domain="my-domain",
    )

    mandates = [
        CustomMandate(
            id="CUSTOM001",
            type="HARD",
            title="My Custom Mandate",
            description="Domain-specific requirement",
            category=Category.ARCHITECTURE.value,
        )
    ]

    guidelines = [
        CustomGuideline(
            id="CUSTOM001",
            type="SOFT",
            title="My Custom Guideline",
            description="Best practice for my domain",
            category=Category.GENERAL.value,
        )
    ]

    def initialize(self):
        # Setup code
        pass

    def validate(self):
        # Return list of validation errors
        errors = []
        for mandate in self.mandates:
            errors.extend(mandate.validate())
        for guideline in self.guidelines:
            errors.extend(guideline.validate())
        return errors
```

### 2. Create Example Extension

Save your extension in `.providence-core/extensions/examples/my-domain/__init__.py`:

```
.providence-core/extensions/
 examples/
     my-domain/
         __init__.py          # Your Extension class here
         README.md            # Documentation
```

The module MUST export an `Extension` class that inherits from `BaseExtension`.

### 3. Load Extensions

```python
from extensions.framework.plugin_loader import load_all_plugins

# Load all plugins
registry, stats = load_all_plugins()

print(f"Loaded {stats['plugins_loaded']} extensions")
print(f"Errors: {stats['load_errors']}")

# Access extension
ext = registry.get("my-domain")
mandates = ext.get_mandates()
guidelines = ext.get_guidelines()
```

## Built-In Examples

### 1. Game Master API (`game-master-api`)

For narrative-driven game backends with:
- Narrative state persistence (HARD mandate)
- Real-time synchronization (HARD mandate)
- Random outcome generation (SOFT guideline)
- NPC behavior trees (SOFT guideline)
- Event sourcing pattern (SOFT guideline)

**Files:**
- `.providence-core/extensions/examples/game-master-api/__init__.py` (2 mandates, 3 guidelines)

### 2. RPG Narrative Server (`rpg-narrative-server`)

For RPG narrative systems with:
- Dialogue consistency (HARD mandate)
- Quest state machines (HARD mandate)
- Dialogue tree branching (SOFT guideline)
- Character relationship tracking (SOFT guideline)
- Quest reward balancing (SOFT guideline)
- Narrative continuity (SOFT guideline)

**Files:**
- `.providence-core/extensions/examples/rpg-narrative-server/__init__.py` (2 mandates, 4 guidelines)

## Architecture

### Core Components

```
extension_framework.py          # Base classes
 ItemType                    # MANDATE, GUIDELINE enums
 Category                    # Standard categories
 CustomMandate               # Domain mandate class
 CustomGuideline             # Domain guideline class
 ExtensionMetadata           # Extension metadata
 BaseExtension               # Base extension class
 ExtensionRegistry           # Registry for managing extensions

plugin_loader.py                # Plugin discovery & loading
 PluginLoader                # Load plugins from filesystem
 load_all_plugins()          # Convenience function
```

### Data Model

```
Extension
 metadata
    name
    version
    author
    domain
    description
    dependencies

 mandates[]
    id
    type (HARD/SOFT)
    title
    description
    category
    rationale
    validation_commands
    metadata

 guidelines[]
     id
     type (HARD/SOFT)
     title
     description
     category
     examples[]
     related_mandate
     metadata
```

## Key Features

### 1. Pydantic-based Validation

All mandates and guidelines are validated using built-in validators:

```python
errors = mandate.validate()  # Returns list of validation errors
```

### 2. Plugin Auto-Discovery

The loader automatically finds extensions in subdirectories:

```
.providence-core/extensions/examples/
 game-master-api/       Loaded as "game-master-api"
 rpg-narrative-server/  Loaded as "rpg-narrative-server"
 my-domain/             Loaded as "my-domain"
```

### 3. Registry System

Centralized access to all extensions:

```python
registry = ExtensionRegistry()
registry.register("my-domain", extension)

# Query
ext = registry.get("my-domain")
mandates = registry.get_mandates("my-domain")
guidelines = registry.get_guidelines()  # All
```

### 4. Metadata Tracking

Track extension dependencies, versions, and authorship:

```python
metadata = extension.metadata

print(metadata.name)
print(metadata.version)
print(metadata.dependencies)  # List of required packages
```

## Categories

Use standard categories for organization:

- `architecture` - System design principles
- `general` - General practices
- `performance` - Performance optimization
- `security` - Security best practices
- `git` - Version control guidelines
- `documentation` - Documentation standards
- `testing` - Testing strategies
- `naming` - Naming conventions
- `code-style` - Code style guidelines

## Testing

Run extension tests:

```bash
# All tests
pytest .providence-core/extensions/tests/

# With coverage
pytest .providence-core/extensions/tests/ --cov=.providence-core/extensions.framework

# Specific test
pytest .providence-core/extensions/tests/test_extensions.py::TestCustomMandate
```

**Test Coverage:** >85% (target)

**Test Categories:**
- `TestCustomMandate` (5 tests)
- `TestCustomGuideline` (3 tests)
- `TestExtensionMetadata` (2 tests)
- `TestExtensionRegistry` (4 tests)
- `TestPluginLoader` (1 test)
- `TestGlobalRegistry` (2 tests)

## Best Practices

### 1. Clear Mandate IDs

Use domain prefix for mandates:
```
GAME001, GAME002, ...       # Game Master API
RPG001, RPG002, ...         # RPG Narrative Server
HEALTH001, HEALTH002, ...   # Healthcare extension
```

### 2. Validate Early

Always implement comprehensive `validate()` method:

```python
def validate(self):
    errors = []
    for mandate in self.mandates:
        errors.extend(mandate.validate())
    for guideline in self.guidelines:
        errors.extend(guideline.validate())
    # Add custom validation
    if len(self.mandates) == 0:
        errors.append("No mandates defined")
    return errors
```

### 3. Document Rationale

Always include rationale for mandates:

```python
CustomMandate(
    id="GAME001",
    type="HARD",
    title="Narrative State Persistence",
    description="...",
    rationale="Allows pausing/resuming games",  # <- Explain why
)
```

### 4. Provide Examples

Guidelines should include practical examples:

```python
CustomGuideline(
    id="GAME001",
    type="SOFT",
    title="Event Sourcing",
    examples=[
        "PlayerMoved event with coordinates",
        "NPCSpawned event with properties",
    ],
)
```

## Integration with SDD API

Load extensions in FastAPI application:

```python
from fastapi import FastAPI
from extensions.framework.plugin_loader import load_all_plugins

app = FastAPI()
registry, stats = load_all_plugins()


@app.get("/api/extensions")
async def list_extensions():
    return registry.get_stats()


@app.get("/api/extensions/{domain}")
async def get_extension(domain: str):
    ext = registry.get(domain)
    if ext is None:
        return {"error": f"Extension {domain} not found"}
    return ext.to_dict()
```

## File Structure

```
.providence-core/extensions/
 __init__.py                              # Module init
 README.md                                # This file

 framework/
    __init__.py
    extension_framework.py              # Core classes (700+ lines)
    plugin_loader.py                    # Plugin loading (300+ lines)
    security.py                         # (Planned: sandboxing)

 examples/
    __init__.py
    game-master-api/
       __init__.py                    # 2 mandates, 3 guidelines
    rpg-narrative-server/
        __init__.py                    # 2 mandates, 4 guidelines

 tests/
     __init__.py
     test_extensions.py                 # Test suite (500+ lines)
```

## Success Criteria

- [x] Base extension classes (CustomMandate, CustomGuideline)
- [x] Registry system for managing extensions
- [x] Plugin loader with auto-discovery
- [x] 2 example extensions working
- [x] Test suite (18+ tests)
- [x] Comprehensive documentation
- [ ] Security sandbox (Week 4)
- [ ] API endpoint integration (Week 4)
- [ ] Dependency resolution (Future)

## Next Steps

**Week 4:**
1. Sandbox security implementation
2. API endpoint integration
3. Load testing with multiple domains
4. Performance optimization

**Future Features:**
- Dependency resolution (plugin A requires plugin B)
- Extension versioning & compatibility
- Plugin marketplace
- Hot-loading (reload without restart)
- Extension signing (verify authenticity)

## Examples: Creating a Custom Domain

### Example: Healthcare System

```python
class HealthcareExtension(BaseExtension):
    metadata = ExtensionMetadata(
        name="Healthcare Compliance",
        version="1.0.0",
        author="Health Team",
        domain="healthcare",
        dependencies=["hipaa-toolkit>=1.0"],
    )

    mandates = [
        CustomMandate(
            id="HEALTH001",
            type="HARD",
            title="HIPAA Compliance",
            description="All patient data MUST be encrypted at rest and in transit",
            category=Category.SECURITY.value,
            rationale="Legal requirement for healthcare",
        ),
        CustomMandate(
            id="HEALTH002",
            type="HARD",
            title="Data Retention Limits",
            description="Patient records MUST be deleted after 7 years",
            category=Category.GENERAL.value,
            rationale="Minimize risk exposure",
        ),
    ]

    guidelines = [
        CustomGuideline(
            id="HEALTHG01",
            type="SOFT",
            title="PII De-identification",
            description="Remove personally identifiable information before data analysis",
            category=Category.SECURITY.value,
            examples=[
                "Hash email addresses",
                "Mask phone numbers",
                "Remove names from records",
            ],
        ),
    ]

    def initialize(self):
        # Load HIPAA templates
        pass

    def validate(self):
        # Validate HIPAA compliance
        pass
```

## References

- **SDD v3.0:** [Migration Guide](../.providence-migration/MIGRATION_v2_to_v3.md)
- **Phase 8 Planning:** [../.providence-migration/PHASE_8_PLANNING.md](../.providence-migration/PHASE_8_PLANNING.md)
- **API Integration:** [../.providence-api/README.md](../.providence-api/README.md)

## Author

SDD Development Team - Phase 8 Workstream 4 (Custom Extensions)

**Timeline:** Week 3-4 of Phase 8 (April 22 - May 6, 2026)
