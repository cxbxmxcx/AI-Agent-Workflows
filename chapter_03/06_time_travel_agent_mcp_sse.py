import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

# agent.py
import asyncio
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerSse

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
