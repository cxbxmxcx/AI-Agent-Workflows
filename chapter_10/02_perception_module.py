import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field
from enum import Enum
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


class TaskType(str, Enum):
    SIMPLE_LOOKUP = "simple_lookup"
    MULTI_STEP = "multi_step"
    CONTRADICTORY = "contradictory"
    AMBIGUOUS = "ambiguous"
    COMPOSITIONAL = "compositional"
    UNKNOWN = "unknown"


class TaskRepresentation(BaseModel):
    task_type: TaskType
    extracted_entities: list[str] = Field(default_factory=list)
    complexity_estimate: float = 0.0
    ambiguities: list[str] = Field(default_factory=list)


perception_agent = Agent(
    name="Perception",
    instructions="""You are the perception module of a cognitive agent.
    Your job is to analyze a user query and produce a structured
    understanding of the task BEFORE any action is taken.

    For each query, determine:

    1. task_type: Is this a simple_lookup, multi_step, contradictory,
       ambiguous, or compositional problem?
    2. extracted_entities: What are the key nouns, concepts, or
       identifiers in the query?
    3. complexity_estimate: From 0.0 (trivial) to 1.0 (highly complex).
       Consider: number of steps needed, whether information must be
       combined from multiple sources, whether the query contains
       contradictions or ambiguity.
    4. ambiguities: List anything in the query that could be
       interpreted multiple ways.

    Be honest about complexity. A question that looks simple but
    requires cross-referencing is at least 0.5. A question containing
    "but" or "however" or "already tried" is likely contradictory
    and should be at least 0.6.

    You do NOT answer the user's question. You only analyze it.""",
    output_type=TaskRepresentation,
    model="gpt-oss",
)
