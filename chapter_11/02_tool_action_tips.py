import json

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    ModelSettings,
    Runner,
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


def _failure_error_function(context, e) -> str:
    # Return a JSON-encoded error message
    return json.dumps({"status": "error", "message": str(e)})


@function_tool(failure_error_function=_failure_error_function)
def lookup_order(order_id: str) -> dict:
    """Check order status by ID. Use when user asks about their order."""
    if not order_id.startswith("ORD-"):
        raise ValueError("Invalid order id format")
    return {"status": "shipped", "eta_days": 3}
    return {"status": "shipped", "eta_days": 3}


tooling_agent = Agent(
    name="ToolingAgent",
    instructions="Use tools when needed; respond with JSON.",
    tools=[lookup_order],
    model_settings=ModelSettings(
        tool_choice="auto",
        parallel_tool_calls=True,
    ),
    model="gpt-oss",
)
print(
    Runner.run_sync(tooling_agent, "What's the status of order ORD-123?").final_output
)
