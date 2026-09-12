# C4 Level 3 - Components: providence_cli

Internal structure of the `providence_cli` package, focused on command dispatch and the
canonical JSON envelope.

```mermaid
graph TB
    user["User / Agent"]

    subgraph cli["providence_cli"]
        typerApp["Typer App\nmain.py / app.py\ncommand registration"]

        subgraph commands["Command Modules"]
            askCmd["ask command\ncommands/ask.py"]
            govCmd["governance commands\ncommands/governance.py"]
            runtimeCmd["runtime commands\ncommands/runtime.py"]
            skillCmd["skills commands\ncommands/skills.py"]
            otherCmd["other command groups\ncommands/*.py"]
        end

        subgraph services["Services"]
            askSvc["Ask services\nservices/ask_*.py\ncontext + response fields"]
            govSvc["Governance services\nservices/governance_*.py\ncompile / validate / sign"]
            runtimeSvc["Runtime services\nservices/runtime_*.py\nstatus + preflight"]
            skillSvc["Skill services\nservices/skills_*.py\nregistry + execution"]
        end

        subgraph shared["Shared Contracts"]
            envelope["CommandResult / CommandError\nshared/contracts.py\ncanonical JSON envelope"]
            errors["CliContractError\nshared/errors.py"]
            constants["Shared constants\nshared/constants.py"]
        end

        telemetry["Telemetry helpers\nservices/*telemetry*.py"]
    end

    subgraph core["providence_core / providence_runtime"]
        governance["Governance domain\nmandates, handshake, audit"]
        compiler["CompilerRunner\nnative sdd-compile bridge"]
        runtime["Skill runtime\nSkillEngine + handlers"]
    end

    user -->|"sdd <group> <command>"| typerApp
    typerApp --> askCmd
    typerApp --> govCmd
    typerApp --> runtimeCmd
    typerApp --> skillCmd
    typerApp --> otherCmd

    askCmd --> askSvc
    govCmd --> govSvc
    runtimeCmd --> runtimeSvc
    skillCmd --> skillSvc
    otherCmd --> services

    askSvc --> envelope
    govSvc --> envelope
    runtimeSvc --> envelope
    skillSvc --> envelope
    services --> errors
    services --> constants
    services --> telemetry

    askSvc --> governance
    govSvc --> governance
    govSvc --> compiler
    runtimeSvc --> governance
    skillSvc --> runtime

    classDef entryStyle fill:#fff2cc,stroke:#d6b656,font-weight:bold
    classDef commandStyle fill:#dae8fc,stroke:#6c8ebf
    classDef serviceStyle fill:#d5e8d4,stroke:#82b366
    classDef contractStyle fill:#e1d5e7,stroke:#9673a6
    classDef externalStyle fill:#f8cecc,stroke:#b85450
    classDef telemetryStyle fill:#ffe6cc,stroke:#d79b00

    class typerApp entryStyle
    class askCmd,govCmd,runtimeCmd,skillCmd,otherCmd commandStyle
    class askSvc,govSvc,runtimeSvc,skillSvc serviceStyle
    class envelope,errors,constants contractStyle
    class governance,compiler,runtime externalStyle
    class telemetry telemetryStyle
```

## Key Flows

### Command dispatch

```
user / agent
  -> Typer app
  -> command module
  -> service function
  -> shared CommandResult envelope when JSON output is emitted
```

Command modules own the CLI surface: arguments, options, Typer callbacks, and
console wiring. Service modules own the reusable workflow and should return
plain data structures that command modules can format.

### Canonical JSON envelope

```
command handler
  -> build_ok_result(command, data)
  -> CommandResult.as_dict()
  -> JSON response with status, command, ok, error, data, schema_version
```

Errors use the same envelope:

```
command handler
  -> build_error_result(command, data, code=..., message=...)
  -> CommandError
  -> JSON response with ok=false and structured error
```

The envelope contract is centralized in
`packages/interfaces/providence_cli/src/providence_cli/shared/contracts.py`. Command handlers
must not build alternate JSON shapes when emitting machine-readable output.

## Boundaries

- `providence_cli.commands` maps user intent to service calls and output mode.
- `providence_cli.services` coordinates governance, runtime, compiler, and filesystem
  interactions.
- `providence_cli.shared` owns cross-command contracts and errors.
- `providence_core` and `providence_runtime` remain upstream dependencies; `providence_cli` must not
  reimplement governance or runtime policy.

## Contract Ownership

The CLI JSON envelope follows ADR-006 and the follow-up decision in ADR-016.
The current contract keeps frozen dataclasses as the runtime model and uses a
manually maintained JSON Schema for consumer-facing validation.
