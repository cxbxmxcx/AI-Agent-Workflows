import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    ModelSettings,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=os.getenv("NRP_API_KEY"),
)
set_default_openai_client(client, use_for_tracing=False)
set_default_openai_api("chat_completions")


class ConsoleTracingProcessor(TracingProcessor):
    """Prints trace/span utilization (tokens, duration) to the console."""

    def on_trace_start(self, trace):
        print(f"\n[trace] '{trace.name}' started")

    def on_trace_end(self, trace):
        print(f"[trace] '{trace.name}' finished")

    def on_span_start(self, span):
        pass

    def on_span_end(self, span):
        data = span.span_data.export()
        summary = f"  [span] {data.get('type', 'unknown')}"
        if data.get("name"):
            summary += f" - {data['name']}"
        if data.get("usage"):
            summary += f" | usage={data['usage']}"
        print(summary)

    def shutdown(self):
        pass

    def force_flush(self):
        pass


set_trace_processors([ConsoleTracingProcessor()])


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
    model="gpt-oss",
)
