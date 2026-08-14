import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.mcp import MCPServerStdio
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

# Point the Agents SDK at the NRP (Nautilus) OpenAI-compatible endpoint
client = AsyncOpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=os.getenv("NRP_API_KEY"),
)
set_default_openai_client(client, use_for_tracing=False)
set_default_openai_api("chat_completions")


class ConsoleTracingProcessor(TracingProcessor):
    """Prints trace/span utilization (tokens, duration) to the console."""

    def on_trace_start(self, trace):
        print(f"\n[trace] '{trace.name}' started")

    def on_trace_end(self, trace):
        print(f"[trace] '{trace.name}' finished")

    def on_span_start(self, span):
        pass

    def on_span_end(self, span):
        data = span.span_data.export()
        summary = f"  [span] {data.get('type', 'unknown')}"
        if data.get("name"):
            summary += f" - {data['name']}"
        if data.get("usage"):
            summary += f" | usage={data['usage']}"
        print(summary)

    def shutdown(self):
        pass

    def force_flush(self):
        pass


# Replace the default OpenAI-backend exporter with a local console printer,
# so utilization is visible without needing a real OpenAI API key
set_trace_processors([ConsoleTracingProcessor()])


@function_tool
def travel_back(year: int, years: int) -> str:
    """
    Travel back in time by a given number of years from the start year.
    """
    print(f"Time travel back by {years} years")
    return f"Current year in time: {year - years}"


@function_tool
def travel_forward(year: int, years: int) -> str:
    """Travel forward in time by a given number of years from the start year."""
    print(f"Time travel forward by {years} years")
    return f"Current year in time: {year - years}"


@function_tool
def how_correct_is_answer(days_in_the_past: int) -> str:
    """
    Returns how many days away from the correct answer the provided answer is.
    If the answer is correct, returns a confirmation message.
    """
    correct_days = 26  # The correct answer is 26 days
    diff = days_in_the_past - correct_days
    if diff == 0:
        answer = "Correct answer!"
    else:
        answer = f"{diff:+d} days away from the correct answer."
    print(f"Answer is {answer}")
    return answer


async def main():
    thinking_srv = MCPServerStdio(
        name="sequential-thinking",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        },
        client_session_timeout_seconds=90,
    )

    instructions = """
You are a time travel assistant. 
You have tools 'travel_back' and 'travel_forward' to perform time jumps. 
First, think step-by-step about the problem to devise a plan.
You must use the tools to calculate dates. 
After using a tool, reflect on the result and continue reasoning. 
Consider braching out your reasoning into multiple branches if necessary.
Execute and consider each branch step-by-step.
Check the answer is correct using 'how_correct_is_answer' tool.
If the answer is correct (0 days) provide the final answer and plan.
If the answer is not correct, continue reasoning and try to find the correct answer.
    """
    agent = Agent(
        model="qwen3",
        name="Time Travel Agent",
        instructions=instructions,
        tools=[
            travel_back,
            travel_forward,
            how_correct_is_answer,
        ],
        mcp_servers=[thinking_srv],
    )

    async with thinking_srv:
        time_travel_problem = """
In a sci-fi film, Alex is a time traveler who decides to go back in time
to witness a famous historical event that took place 125 years ago,
which lasted for 10 days. He arrives three days before the event starts.
However, after spending six days in the past, he jumps forward in time
by 50 years and stays there for 20 days. Then, he travels back to
witness the end of the end. Alex current year is 2050.
How many days does Alex spend in the past before he sees the end of the event?
"""
        print("Running...")
        result = await Runner.run(
            agent,
            time_travel_problem,
            max_turns=25,
        )
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
