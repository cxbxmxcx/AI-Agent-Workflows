import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import json

from agents import Agent, ModelSettings, Runner, function_tool


def _failure_error_function(context, e) -> str:
    # Return a JSON-encoded error message
    return json.dumps({"status": "error", "message": str(e)})


@function_tool(failure_error_function=_failure_error_function)
def lookup_order(order_id: str) -> dict:
    """Check order status by ID. Use when user asks about their order."""
    if not order_id.startswith("ORD-"):
        raise ValueError("Invalid order id format")
    return {"status": "shipped", "eta_days": 3}
    return {"status": "shipped", "eta_days": 3}


tooling_agent = Agent(
    name="ToolingAgent",
    instructions="Use tools when needed; respond with JSON.",
    tools=[lookup_order],
    model_settings=ModelSettings(
        tool_choice="auto",
        parallel_tool_calls=True,
    ),
)
print(
    Runner.run_sync(tooling_agent, "What's the status of order ORD-123?").final_output
)
