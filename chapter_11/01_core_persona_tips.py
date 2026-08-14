from datetime import date

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

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


class Answer(BaseModel):  # A
    """Machine-readable answer format."""

    answer: str = Field(..., description="Concise, user-facing answer")
    citations: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


def core_instructions(ctx, agent) -> str:  # B
    today = date.today().isoformat()  # C
    return (
        f"You are SupportMentor, a helpful domain assistant. Today is {today}.\n"  # D
        "Always:\n"
        "1) Answer concisely; 2) Prefer retrieved context; 3) If context is missing, say you don't know.\n"
        "Output must be valid JSON matching the Answer schema.\n"
        "Never: make policy exceptions or invent facts."
    )


core_agent = Agent(
    name="SupportMentor",
    instructions=core_instructions,
    output_type=Answer,
    model="gpt-oss",
)

input = "What's our refund window for accessories?"
result = Runner.run_sync(core_agent, input)
print(result.final_output)
