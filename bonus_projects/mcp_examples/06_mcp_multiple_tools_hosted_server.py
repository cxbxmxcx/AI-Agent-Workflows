import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import os

from agents.mcp import MCPServerStdio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Sandbox Filesystem")
SANDBOX = os.path.dirname(os.path.abspath(__file__))


@mcp.tool()
async def list_directory() -> str:
    """Return the directory contents as a single string."""
    async with MCPServerStdio(
        name="filesystem",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", SANDBOX],
        },
    ) as fs:
        res = await fs.call_tool("list_directory", {"path": SANDBOX})
        return res.content[0].text  # assume res.content is a list of Text objects


@mcp.tool()
async def read_file(path: str) -> str:
    """Return the directory contents as a single string."""
    async with MCPServerStdio(
        name="filesystem",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", SANDBOX],
        },
    ) as fs:
        result = await fs.call_tool("read_file", {"path": os.path.join(SANDBOX, path)})
        return result.content[0].text  # assume res.content is a list of Text objects


if __name__ == "__main__":
    mcp.run(transport="sse")
