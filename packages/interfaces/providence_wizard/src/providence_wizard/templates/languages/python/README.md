# Python SDD Templates

These templates implement Clean Architecture (M001) and Test-Driven Development (M002) for Python projects.

## Files Included

### `pyproject.toml`
Modern Python project configuration with:
- **Clean Architecture**: Dependency Injector framework
- **TDD (M002)**: Pytest with 80% code coverage minimum
- **Type Safety**: MyPy strict mode for type checking
- **Code Quality**: Black formatter, isort, pylint, flake8
- **Coverage Enforcement**: Build fails if coverage < 80%

## Getting Started

1. Copy `pyproject.toml` to your project root
2. Install dependencies: `pip install -e ".[test,dev]"`
3. Run tests: `pytest` (will check coverage automatically)
4. Run linting: `pylint src` or `flake8 src`
5. Format code: `black . && isort .`

## Key Mandates Enforced

- **M001: Clean Architecture** - Dependency-injector framework for DI
- **M002: Test-Driven Development** - Pytest, 80% code coverage minimum

## Test Organization

Tests are located in the `tests/` directory and follow:
- Filename: `test_*.py`
- Class naming: `Test*`
- Function naming: `test_*`

Coverage report available in: `htmlcov/index.html`

## Type Hints (M001)

All Python code should include type hints:
```python
def process_data(items: list[str]) -> dict[str, int]:
    """Process items and return count."""
    return {item: len(item) for item in items}
```

## Extending Templates

To add more dependencies:
1. Add to appropriate section in `[project.optional-dependencies]`
2. Update tool configurations if needed
3. Ensure coverage and type checking still pass

## Continuous Integration

GitHub Actions workflow will automatically:
- Run tests with coverage
- Check type hints with mypy
- Enforce code formatting
- Fail if coverage < 80%
