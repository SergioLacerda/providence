# C4 Level 3 — Components: providence_runtime

Internal structure of the `providence_runtime` execution engine.

```mermaid
graph TB
    cli["providence_cli\n(caller)"]

    subgraph runtime["providence_runtime"]
        engine["SkillEngine\n(thin facade)\nskills.py"]

        subgraph registry["Registry"]
            skillReg["SkillRegistry\n_skill_registry.py\nload / list / get / export"]
        end

        subgraph executor["Executor"]
            skillExec["SkillExecutor\n_skill_executor.py\nrun_skill template"]

            subgraph handlers["Skill Handlers"]
                askH["AskHandler\npre_run: execution contract"]
                diagH["DiagnoseHandler\npre_run: diagnosis report"]
                corrH["CorrectHandler\npre_run: correction gate\npost_run: learning + candidates"]
                convH["ConvergeHandler\npost_run: delta report\n+ rule decisions"]
            end

            policy["PolicyEngine\npolicy.py\nhandshake + risk enforcement"]
            cmdExec["_execute_commands\nSafeProcessRunner\ncli_fallback commands"]
        end

        subgraph governance["Governance"]
            injector["GovernanceInjector\nloads compiled artifacts\ninto agent context"]
            drift["DriftDetector\ncompares fingerprints\ndetects governance drift"]
        end

        subgraph learning["Supervised Learning"]
            store["SupervisedLearningStore\nledger → candidates → rules\nrule impact recording"]
        end

        telemetry["TelemetrySink\nRuntimeEvent → JSONL\n.providence/runtime/telemetry.jsonl"]
    end

    cli -->|"run_skill(name, context)"| engine
    engine --> skillReg
    engine --> skillExec
    skillExec -->|"get_skill(name)"| skillReg
    skillExec --> policy
    skillExec --> handlers
    skillExec --> cmdExec
    skillExec -->|"emit telemetry"| telemetry
    corrH --> store
    convH --> store
    skillExec --> store

    classDef facadeStyle fill:#fff2cc,stroke:#d6b656,font-weight:bold
    classDef registryStyle fill:#dae8fc,stroke:#6c8ebf
    classDef executorStyle fill:#d5e8d4,stroke:#82b366
    classDef handlerStyle fill:#d5e8d4,stroke:#82b366
    classDef governanceStyle fill:#e1d5e7,stroke:#9673a6
    classDef learningStyle fill:#f8cecc,stroke:#b85450
    classDef telemetryStyle fill:#ffe6cc,stroke:#d79b00

    class engine facadeStyle
    class skillReg registryStyle
    class skillExec,policy,cmdExec executorStyle
    class askH,diagH,corrH,convH handlerStyle
    class injector,drift governanceStyle
    class store learningStyle
    class telemetry telemetryStyle
```

## Key Flows

### Skill execution (`providence ask "..."`)

```
providence_cli → SkillEngine.run_skill("sdd-ask", context)
  → SkillRegistry.get_skill("sdd-ask")
  → PolicyEngine.evaluate_skill_policy()
  → AskHandler.pre_run()  # builds execution contract
  → SkillExecutor._execute_commands()  # runs cli_fallback
  → TelemetrySink.emit(RuntimeEvent)
```

### Correction with gate (`sdd correct`)

```
providence_cli → SkillEngine.run_skill("sdd-correct", context)
  → CorrectHandler.pre_run()
      → _evaluate_correction_gate()  # evidence / confidence / scope checks
      → if deny: SupervisedLearningStore.append_failure() → early exit
  → SkillExecutor._execute_commands()
  → CorrectHandler.post_run()
      → SupervisedLearningStore.append_failure()
      → SupervisedLearningStore.generate_candidates_from_ledger()
```

### Handler discovery (`_get_skill_handler`)

```
name = "sdd-correct"
suffix = "correct"
class_name = "CorrectHandler"
cls = globals()["CorrectHandler"]  # in _skill_executor.py
return cls()
```
