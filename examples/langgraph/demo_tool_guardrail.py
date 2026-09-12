#!/usr/bin/env python3
"""
LangGraph Demo — SDD Tool Guardrail

Shows SDD blocking an agent before a LangGraph graph executes when the
governance artifact is missing or the preflight policy check fails.

Run from repo root:
    uv run --extra examples-langgraph python examples/langgraph/demo_tool_guardrail.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import (  # type: ignore[import-not-found]
    HumanMessage,
)
from langchain_core.tools import tool  # type: ignore[import-not-found]
from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]
from langgraph.graph.message import add_messages  # type: ignore[import-not-found]
from providence_runtime import CompiledArtifact, PolicyEngine, SessionState

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / ".providence" / "metadata.json"

SECTION = "\n" + "=" * 60


def load_artifact() -> CompiledArtifact:
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return CompiledArtifact(
        artifact_version=raw["version"],
        schema_version=raw["version"],
        fingerprint=raw["fingerprints"]["combined"],
        generated_at=raw.get("generated_at", ""),
        profile=raw.get("adoption_level", "client"),
    )


@tool  # type: ignore[untyped-decorator]
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. (NOT authorized in governance mandate.)"""
    return f"Email sent to {to}: {body}"


# ─── LangGraph agent node ──────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[list[HumanMessage], add_messages]


def agent_node(state: AgentState) -> AgentState:
    return {"messages": [HumanMessage(content="Calling send_email tool...")]}


# ─── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    print(SECTION)
    print("SDD + LangGraph — Tool Guardrail Demo")
    print(SECTION)

    # 1. Load SDD governance artifact
    print("\n[SDD] Loading governance artifact...")
    if not METADATA_PATH.exists():
        print("[SDD] ERROR: .providence/metadata.json not found. Run from repo root.")
        sys.exit(1)

    artifact = load_artifact()
    print(
        f"[SDD] Artifact loaded  fingerprint={artifact.fingerprint}  schema={artifact.schema_version}"
    )

    # 2. Simulate a session that carries a *tampered* fingerprint (drift scenario)
    tampered_fingerprint = "deadbeef00000000"
    session = SessionState(
        workspace_id="demo-workspace",
        agent_id="demo-agent",
        work_item_id="demo-item",
        artifact_fingerprint=tampered_fingerprint,
        schema_version=artifact.schema_version,
        policy_set_version=artifact.schema_version,
    )
    print(f"\n[SDD] Session fingerprint (tampered) : {tampered_fingerprint}")
    print(f"[SDD] Artifact fingerprint (expected) : {artifact.fingerprint}")

    # 3. Pre-flight policy check — runs BEFORE the graph is built or invoked
    print("\n[SDD] Running preflight policy check for tool 'send_email'...")
    engine = PolicyEngine()
    result = engine.validate_preflight(
        artifact=artifact,
        session=session,
        current_profile="client",
    )

    if not result.allowed:
        print(f"\n[SDD] BLOCKED — severity={result.severity}")
        print(f"[SDD] Reason     : {result.reason}")
        print(f"[SDD] Remediation: {result.remediation}")
        print("\n[SDD] Graph execution prevented. Governance enforced.")
        print("[SDD] The 'send_email' tool was never bound or invoked.")
        print(SECTION)
        sys.exit(0)

    # 4. Only reached if preflight passes (won't happen with tampered session)
    print("\n[SDD] Preflight passed — building graph...")
    builder: StateGraph[AgentState] = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    graph = builder.compile()

    result_state = graph.invoke({"messages": [HumanMessage(content="start")]})
    print(f"[Graph] {result_state['messages'][-1].content}")
    print(SECTION)


if __name__ == "__main__":
    main()
