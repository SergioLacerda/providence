---
applyTo: "**/*.go"
---

# Go

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

## Code Style

**Tools:**

```bash
gofmt -l .
go vet ./...
golangci-lint run
```

**Rules:**

- All errors must be checked â€” never discard an error without a documented reason.
- Errors must be wrapped with context using `fmt.Errorf("...: %w", err)`.
- No `panic` for expected application errors â€” return errors explicitly.
- Every goroutine must have a cancellation path via `context.Context`.
- Package names must be lowercase, single words reflecting cohesive behavior.

## Architecture & Dependency Direction

Domain and application packages must not import adapter packages. Enforce the boundary in CI with a dependency-direction linter. Dependencies are injected via constructor or parameter, never global state â€” see `architecture.instructions.md` for the general principle.

## Dependency Versions

- Pin direct dependencies to exact versions (`go.sum` is canonical).
- Review changelogs before upgrading â€” never blindly bump.
- Run `govulncheck ./...` as part of CI.
- Minimize the dependency tree â€” every dependency is attack surface and maintenance burden.

## Anti-Patterns

**Ignored error:**

```go
// VIOLATION
_ = json.Unmarshal(data, &value)

// OK
if err := json.Unmarshal(data, &value); err != nil {
    return fmt.Errorf("decode payload: %w", err)
}
```

**Panic as control flow:**

```go
// VIOLATION
func GetUser(id string) *User {
    if id == "" {
        panic("id cannot be empty")
    }
    // ...
}

// OK
func GetUser(id string) (*User, error) {
    if id == "" {
        return nil, fmt.Errorf("GetUser: id cannot be empty")
    }
    // ...
}
```

**Goroutine leak:**

```go
// VIOLATION â€” no cancellation path
go func() { for { process() } }()

// OK â€” checks ctx before each iteration
go func(ctx context.Context) {
    for ctx.Err() == nil { process() }
}(ctx)
```

## Performance

- Profile with `pprof` before optimizing any hot path.
- Use `sync.Pool` for frequently allocated short-lived objects.
- Avoid spawning a goroutine per request without a worker pool.
- Use buffered channels intentionally â€” document the buffer size rationale.
- Prefer value types over pointers for small structs in hot paths.

## Project Structure

```
cmd/
  server/
    main.go           # entry point
internal/
  domain/             # business rules; no external imports
  application/        # use cases; imports domain only
  adapters/           # implements domain ports
  infrastructure/     # wiring, config, startup
pkg/                  # public library code (if any)
go.mod
go.sum
```

Avoid `internal/common`, `internal/utils` â€” name packages by behavior. No circular imports.

## CI Checklist

```bash
go build ./...
go test ./...
go test -race ./...
go vet ./...
golangci-lint run
go mod verify
govulncheck ./...
```
