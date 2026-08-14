import asyncio
import os
import sys
from pathlib import Path
from typing import List

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.mcp import MCPServerStdio, MCPServerStdioParams
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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

SANDBOX = os.path.dirname(os.path.abspath(__file__))
SCRIPT = Path(__file__).with_name("04_research_tools_mcp_server.py").resolve()

research_srv = MCPServerStdio(
    name="Research Tools",
    params=MCPServerStdioParams(
        command="mcp",
        args=["run", str(SCRIPT)],
    ),
    client_session_timeout_seconds=90,
)
thinking_srv = MCPServerStdio(
    name="sequential-thinking",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
    },
    client_session_timeout_seconds=90,
)
fs_srv = MCPServerStdio(
    name="filesystem",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", SANDBOX],
    },
    client_session_timeout_seconds=90,
)


class ResearchSourcesModel(BaseModel):
    research_sources: List[str]
    """A list of research sources to use for research."""


@function_tool
async def research_agent(instructions: str) -> ResearchSourcesModel:
    """
    Use the research agent to find research sources.
    """
    agent = Agent(
        name="Research Agent",
        instructions="""
You are a research assistant.
Your role is to find research sources.
Never make up or invent any research sources.
""",
        output_type=ResearchSourcesModel,
        mcp_servers=[research_srv],
        model="gpt-oss",
    )
    async with research_srv:
        result = await Runner.run(agent, instructions)
        return result.final_output


@function_tool
async def filesystem_agent(instructions: str) -> str:
    """
    Use the filesystem agent to read or write files.
    """
    agent = Agent(
        name="Filesystem Agent",
        instructions="""
You are a filesystem assistant.
Your role is to read and write files.
Never make up or invent any ouput.
""",
        mcp_servers=[fs_srv],
        model="gpt-oss",
    )
    async with fs_srv:
        result = await Runner.run(agent, instructions)
        return result.final_output


orchestration_agent = Agent(
    name="Orchestration Agent",
    instructions="""
You are a research planning and orchestration assistant.
Your role is to plan the research, find existing research already done and update it.
Use the research agent to find research sources.
Use the sequentialThinking tool to create a research plan based on the sources.
Use the filesystem agent to help find existing research and update it.
Use the filesystem agent to write the output as a text file.
""",
    tools=[research_agent, filesystem_agent],
    model="gpt-oss",
)


async def main():
    async with thinking_srv:
        goal = """
Produce a research plan to find the book 'The Hitchhiker's Guide to the Galaxy'
"""
        orchestration_agent.mcp_servers = [thinking_srv]
        print("Running...", goal)
        result = await Runner.run(
            orchestration_agent,
            goal,
            max_turns=25,
        )
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
