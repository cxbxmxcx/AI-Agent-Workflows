import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

from typing import List

from agents import Agent, Runner
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Create an MCP server
mcp = FastMCP("Research Tools")

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

class ResearchPlanModel(BaseModel):
    tasks: List[str]
    """A list of tasks to perform for research."""

@mcp.tool()
async def get_research_plan(subject: str) -> ResearchPlanModel:
    try:
        agent = Agent(
            name="Research Planner",
            instructions=instructions,
            output_type=ResearchPlanModel,
        )       

        result = await Runner.run(
            agent,
            input=subject,
        )

        return result.final_output
    except Exception as e:
        return ResearchPlanModel(tasks=[str(e)])


if __name__ == "__main__":
    mcp.run(transport="sse")
