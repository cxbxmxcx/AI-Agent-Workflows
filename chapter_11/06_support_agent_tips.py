import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

from agents import Agent, ModelSettings, function_tool


@function_tool
def escalate_to_human(ticket_id: str, reason: str) -> str:
    """Escalate this conversation to a human. Use for angry users, large refunds, or unclear policy."""
    # Create/route ticket in your system...
    return f"Escalated ticket {ticket_id}: {reason}"


retrieval_agent = Agent(...)  # add retrieval agent here

support = Agent(
    name="Triage Support Agent",
    instructions=(
        "Verify identity before account actions. Cite policies. "
        "If unsure or user is upset, call escalate_to_human."
        "Pass on complex queries to retrieval_agent."
    ),
    tools=[
        escalate_to_human,
        retrieval_agent.as_tool(),
    ],  # add order lookup, refund APIs, and RAG tool here
    model_settings=ModelSettings(tool_choice="auto"),
)
