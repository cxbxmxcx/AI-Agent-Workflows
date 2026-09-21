import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

from pydantic import BaseModel
from agents import Agent
from agents.mcp import MCPServerStdio


class Finding(BaseModel):
    content: str
    source: str
    relevance_score: float = 0.0
    quality_note: str = ""


# Connect to domain-specific tools via MCP
# Replace with your domain-specific MCP server
# (Brave Search, database, API, etc.)
search_server = MCPServerStdio(
    name="Filesystem",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs"],
    },
)


execution_agent = Agent(
    name="Executor",
    instructions="""You are the execution module of a cognitive agent.
    You receive a specific sub-goal from the current plan and execute
    it using available tools.

    For each result, provide:
    - content: The relevant information you found
    - source: Where it came from
    - relevance_score: 0.0 to 1.0, how relevant to the sub-goal
    - quality_note: Any concerns about the result quality
      (e.g., "source is a table of contents, not actual content",
       "result is partial", "high confidence match")

    Be honest about quality. A retrieval that returns metadata
    instead of content should get a low relevance_score and a
    quality_note explaining why.""",
    mcp_servers=[search_server],
    output_type=Finding,
)
