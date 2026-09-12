# Java SDD Templates

These templates implement Clean Architecture (M001) and Test-Driven Development (M002) for Java projects.

## Files Included

### `project.gradle`
Gradle build configuration with:
- **Clean Architecture**: Dependency Injection setup
- **TDD (M002)**: JUnit + Mockito test framework
- **Code Coverage**: JaCoCo integration with 80% minimum coverage
- **Quality Gates**: Tests must pass before build success

## Getting Started

1. Copy `project.gradle` to your project's `build.gradle` (or rename it)
2. Run `gradle build` to compile and test
3. Run `gradle test` to execute tests with coverage report

## Key Mandates Enforced

- **M001: Clean Architecture** - Dependency Injection via `javax.inject`
- **M002: Test-Driven Development** - JUnit + Mockito, 80% code coverage minimum

## Additional Configuration

- Java 17+ (update `sourceCompatibility` if needed)
- Code coverage report in `build/reports/jacoco/test/html/`
- Failed coverage checks prevent build success

## Extending Templates

To add more dependencies or customize build tasks, edit `project.gradle` following:
- Clean Architecture patterns
- TDD requirements
- SDD governance rules
