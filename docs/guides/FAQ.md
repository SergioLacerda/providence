# FAQ

## Quick Answers

**What is SDD?**
Spec-Driven Development — executable governance for AI agents. Rules are compiled into artifacts that are validated at runtime and in CI.

**Does SDD replace my framework?**
No. SDD sits between your team's decisions and the agent's actions. It doesn't replace LangChain, AutoGen, or any orchestration tool.

**What does `providence doctor run` check?**
Workspace profile, compiled governance artifacts, compliance trail, CLI health, and environment consistency.

**How do I update governance rules?**
Edit files under `docs/spec/canonical/`, then run `providence governance compile` + `providence governance validate`.

**Full FAQ →** [docs/spec/guides/faq.md](../spec/guides/faq.md)
