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


class StrategyType(str, Enum):
    DIRECT = "direct"
    DECOMPOSE = "decompose"
    EXPLORE = "explore"
    HYPOTHESIS_TEST = "hypothesis_test"


class PlanOutput(BaseModel):
    strategy_type: StrategyType
    sub_goals: list[str] = Field(default_factory=list)
    alternative_strategies: list[str] = Field(default_factory=list)


planning_agent = Agent(
    name="Planner",
    instructions="""You are the planning module of a cognitive agent.
    You receive a task representation from the perception module and
    propose an execution strategy.

    Select a strategy based on the task:
    - DIRECT: For simple lookups with complexity < 0.3. One tool call.
    - DECOMPOSE: For multi-step problems. Break into ordered subtasks.
      Identify which subtasks depend on others.
    - EXPLORE: For ambiguous problems. Propose information-gathering
      steps before committing to an approach.
    - HYPOTHESIS_TEST: For contradictory scenarios. Generate 2-3
      competing hypotheses and propose how to test each one.

    If memory_hits are present in the workspace, use them to inform
    your strategy. Past experience should accelerate planning, not
    replace it.

    Output a plan with: strategy_type, ordered list of sub_goals,
    and any alternative_strategies worth keeping in reserve.""",
    output_type=PlanOutput,
    model="gpt-oss",
)
