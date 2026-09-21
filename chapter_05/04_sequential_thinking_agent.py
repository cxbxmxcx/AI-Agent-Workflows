import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import asyncio

from agents import Agent, Runner
from agents.mcp import MCPServerStdio


async def main():
    # Instantiate the servers first…
    thinking_srv = MCPServerStdio(
        name="sequential-thinking",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        },
    )

    instructions = """
You are helpful planning assistant.
    """
    agent = Agent(
        name="Assistant",
        instructions=instructions,
        mcp_servers=[thinking_srv],
    )

    async with thinking_srv:
        tools = await thinking_srv.list_tools()
        print("Available tools:", tools)
        goal = """
Discover and output the tool and functions you have available.
"""
        print("Running...", goal)
        result = await Runner.run(agent, goal)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
