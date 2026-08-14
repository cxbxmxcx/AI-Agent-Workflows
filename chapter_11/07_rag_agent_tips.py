import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
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
def retrieve(query: str, corpus: str = "product_docs", top_k: int = 5) -> list[dict]:
    """Return top-k passages with metadata from the selected index."""
    # ... ANN + metadata filtering ...
    return [{"text": "...", "source": "KB-123", "section": "Refunds"}]


answerer = Agent(
    name="RAG-Answerer",
    instructions=(
        "Use ONLY the passages provided via `retrieve`. "
        "If none answer the question, reply: "
        "'I don't know based on the available documents.' "
        "Return a short summary and cite sources."
    ),
    tools=[retrieve],
    model="gpt-oss",
)
