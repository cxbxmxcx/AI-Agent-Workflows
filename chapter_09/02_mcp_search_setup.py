import asyncio
import os
from agents import Agent, Runner
from agents.mcp import MCPServerStdio


SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "brave").lower()


async def create_search_server() -> MCPServerStdio:
    """Create search server based on SEARCH_PROVIDER env var ('brave' or 'tavily')."""
    if SEARCH_PROVIDER == "tavily":
        return await create_tavily_search_server()
    return await create_brave_search_server()


async def create_brave_search_server() -> MCPServerStdio:
    server = MCPServerStdio(
        name="Brave Search",
        params={
            "command": "npx",
            "args": ["-y", "@anthropic/brave-search-mcp"],
            "env": {"BRAVE_API_KEY": os.environ["BRAVE_API_KEY"]},
        },
    )
    await server.connect()
    return server


async def create_tavily_search_server() -> MCPServerStdio:
    server = MCPServerStdio(
        name="Tavily Search",
        params={
            "command": "npx",
            "args": ["-y", "@tavily-ai/tavily-mcp"],
            "env": {"TAVILY_API_KEY": os.environ["TAVILY_API_KEY"]},
        },
    )
    await server.connect()
    return server
