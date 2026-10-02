import asyncio
import os
from agents import Agent, Runner
from agents.mcp import MCPServerStdio


async def create_search_server() -> MCPServerStdio:
    server = MCPServerStdio(
        name="Brave Search",
        params={
            "command": "npx",
            "args": ["-y", "@brave/brave-search-mcp-server@2.1.4"],
            "env": {"BRAVE_API_KEY": os.environ["BRAVE_API_KEY"]},
        },
        client_session_timeout_seconds=60,
    )
    await server.connect()
    return server
