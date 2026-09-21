import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import asyncio

from agents import Agent, Runner
from agents.mcp import MCPServerSse


async def main():
    async with MCPServerSse(
        name="SSE Python Server",
        params={
            "url": "http://localhost:8000/sse",
        },
    ) as research_server:
        agent = Agent(
            name="Assistant",
            instructions="""
Use the research tools to perform and plan research.""",
            mcp_servers=[research_server],
        )

        input = """
Get the research plan for the book 
'The Hitchhiker's Guide to the Galaxy'"""
        print("Running: Get the research plan")
        result = await Runner.run(agent, input)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
