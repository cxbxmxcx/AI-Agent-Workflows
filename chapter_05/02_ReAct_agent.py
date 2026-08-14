import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

# Point the Agents SDK at the NRP (Nautilus) OpenAI-compatible endpoint
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


# Replace the default OpenAI-backend exporter with a local console printer,
# so utilization is visible without needing a real OpenAI API key
set_trace_processors([ConsoleTracingProcessor()])


# Define two tools for time calculations
@function_tool
def travel_back(year: int, years: int) -> int:
    """Travel back in time by a given number of years from the start year."""
    return year - years


@function_tool
def travel_forward(year: int, years: int) -> int:
    """Travel forward in time by a given number of years from the start year."""
    return year + years


# Create an agent equipped with the tools
react_agent = Agent(
    name="TimeTravelerReAct",
    instructions=(
        "You are a time travel assistant. You have tools 'travel_back' and 'travel_forward' to perform time jumps. "
        "First, think step-by-step about the problem. If needed, use the tools to calculate dates. "
        "After using a tool, reflect on the result and continue reasoning. "
        "After gathering information, provide the final answer."
    ),
    tools=[travel_back, travel_forward],
    model="gpt-oss",
)

# A time travel problem that requires using the tools
problem = (
    "I am in the year 2050."
    "I travel 25 years back in time, then travel 10 years forward, "
    "and finally go 5 years back again. What year is it now?"
)

result = asyncio.run(Runner.run(react_agent, input=problem))
print(result.final_output)
