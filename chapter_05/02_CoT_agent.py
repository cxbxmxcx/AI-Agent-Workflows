import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import asyncio

from agents import Agent, Runner

# Define an agent that always explains its reasoning step by step
cot_agent = Agent(
    name="TimeTravelerCoT",
    instructions=(
        "You are a time travel problem solver. "
        "Work out the solution step by step, then give the final answer."
    ),
)

# Example time travel question
question = (
    "Starting in 2025, you travel 10 years to the past, then 5 years to the future. "
    "What year do you end up in?"
)

# Run the agent (using await in an async context, or Runner.run_sync in a script)
result = asyncio.run(Runner.run(cot_agent, input=question))
print(result.final_output)
