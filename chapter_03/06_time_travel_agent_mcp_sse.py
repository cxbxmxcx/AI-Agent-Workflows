# agent.py
import asyncio
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.mcp import MCPServerSse
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

SCRIPT = Path(__file__).with_name("06_mcp_time_travel_tracker").resolve()

# Simulate a series of historical travel events
travel_events = [
    "Traveled to Ancient Rome and watched a gladiator fight",
    "Visited the signing of the Declaration of Independence in 1776",
    "Witnessed the moon landing in 1969",
]


async def main():
    async with MCPServerSse(
        name="Time Tracker Server",
        params={
            "url": "http://localhost:8000/sse",
        },
    ) as time_tracker_server:
        agent = Agent(
            name="Assistant",
            instructions="""
You are a time-travel journaling agent.
Always use the 'load_journal' tool at the start to get past entries.
For a new event, call 'record_event' to save it.
If asked for a summary or to show the journal, output all recorded events.
            """,
            mcp_servers=[time_tracker_server],
            model="gpt-oss",
        )
        print("Recording travels:")
        for event in travel_events:
            await Runner.run(agent, event)
        # Ask the agent to summarize the adventures
        result = await Runner.run(agent, "Show my travel history")
        print("\nFinal Journal:")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
