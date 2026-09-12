# JavaScript/TypeScript SDD Templates

These templates implement Clean Architecture (M001) and Test-Driven Development (M002) for TypeScript/JavaScript projects.

## Files Included

### `package.json`
Node.js project configuration with:
- **Clean Architecture**: InversifyJS for dependency injection
- **TDD (M002)**: Jest test framework with coverage enforcement
- **TypeScript**: Full type safety configuration
- **Code Quality**: ESLint, Prettier, TypeScript strict mode

### `tsconfig.json`
TypeScript compiler options with:
- **Strict Mode**: All safety checks enabled
- **Type Checking**: No implicit `any`, full type coverage
- **Decorators**: Support for InversifyJS DI

### `jest.config.js`
Jest test runner configuration with:
- **Coverage Enforcement**: 80% minimum (M002)
- **TypeScript Support**: ts-jest preset
- **Test Discovery**: Finds `*.test.ts` and `*.spec.ts` files

### `eslint.config.js`
ESLint configuration with:
- **TypeScript Support**: `@typescript-eslint` plugin
- **Type-Safe Linting**: Returns type enforcement
- **Code Quality**: Prevents implicit `any`, unused variables

## Getting Started

1. Copy all files to your project root
2. Install dependencies: `npm install`
3. Run tests: `npm test` (will check coverage automatically)
4. Run linting: `npm run lint`
5. Format code: `npm run format`
6. Build: `npm run build`

## Key Mandates Enforced

- **M001: Clean Architecture** - InversifyJS dependency injection framework
- **M002: Test-Driven Development** - Jest, 80% code coverage minimum

## Test Organization

Tests should be in `tests/` directory with:
- Filename: `*.test.ts` or `*.spec.ts`
- Jest will auto-discover and run
- Coverage report: `coverage/index.html`

## Type Safety (M001)

All code must have proper types:
```typescript
interface IUserRepository {
  findById(id: string): Promise<User>;
}

class UserService {
  constructor(@inject('UserRepository') private repo: IUserRepository) {}

  async getUser(id: string): Promise<User> {
    return this.repo.findById(id);
  }
}
```

## Dependency Injection

Use InversifyJS with decorators:
```typescript
import { Container, injectable, inject } from 'inversify';

@injectable()
class MyService {
  constructor(@inject('SomeDependency') private dep: IDependency) {}
}

const container = new Container();
container.bind('SomeDependency').to(Implementation);
```

## Extending Templates

To add more dependencies:
1. Update `package.json`
2. Run `npm install`
3. Update configs if tool behavior needs changes
4. Ensure tests still pass with 80%+ coverage

## CI/CD Integration

GitHub Actions will:
- Run tests and enforce coverage
- Run linting
- Fail if coverage < 80%
- Prevent builds without passing tests
