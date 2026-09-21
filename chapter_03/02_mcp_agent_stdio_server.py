import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import asyncio
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStdio, MCPServerStdioParams

SCRIPT = Path(__file__).with_name("01_claude_mcp_server.py").resolve()


async def main():
    async with MCPServerStdio(
        name="Research Tools",
        params=MCPServerStdioParams(
            command="mcp",
            args=["run", str(SCRIPT)],
        ),
    ) as research_server:
        agent = Agent(
            name="Assistant",
            instructions="Use the research tools to perform research.",
            mcp_servers=[research_server],
        )

        print("Running: Get the available research sources")
        result = await Runner.run(agent, "Get the available research sources")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
