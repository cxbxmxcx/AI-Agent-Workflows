import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    RunContextWrapper,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
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


def get_reflexion_solver_instructions(
    run_context: RunContextWrapper[str], agent: Agent[str]
) -> str:
    """Generate instructions for the reflexion solver agent."""
    instructions = (
        "You are a time-travel expert. Solve the problem step by step "
        "and be careful to avoid mistakes."
    )
    return instructions + "\nHINT:\n" + run_context.context


# --- Base agents -------------------------------------------------------------
solver = Agent(
    name="TimeTravelerReflexion",
    instructions=get_reflexion_solver_instructions,
    model="gpt-oss",
)
critic = Agent(
    name="TimeTravelCritic",
    instructions=(
        "You are an expert tutor. If the solution is wrong, explain the error "
        "and give a concise hint for improvement."
    ),
    model="gpt-oss",
)

# --- Problem spec ------------------------------------------------------------
problem = (
    "I left the year 2000 in a time machine, went forward 30 years, "
    "then back 40 years. I claim I'm now in 1990. Am I correct?"
)
problem = """
In a sci-fi film, Alex is a time traveler who decides to go back in time
to witness a famous historical event that took place 100 years ago,
which lasted for 10 days. He arrives three days before the event starts.
However, after spending six days in the past, he jumps forward in time
by 50 years and stays there for 20 days. Then, he travels back to
witness the end of the end. 
How many days does Alex spend in the past before he sees the end of the event?
"""
TARGET_DAYS = "26"  # expected final answer
MAX_ATTEMPTS = 5  # fail-safe cap on retries


async def main():
    # --- Reflexion loop ----------------------------------------------------------
    feedback_hint = ""
    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        # Run the solver
        result = await Runner.run(solver, input=problem, context=feedback_hint)
        answer = result.final_output.strip()
        print(f"\nAttempt {attempt_no}:\n{answer}")

        # --- Simple correctness check -------------------------------------------
        has_correct_days = TARGET_DAYS in answer
        says_claim_correct = "yes" in answer.lower() or "correct" in answer.lower()
        solved = has_correct_days and says_claim_correct

        if solved:
            print("✅ Solution accepted.")
            break

        # --- Not solved: generate feedback & retry ------------------------------
        feedback_prompt = (
            f"Solution given:\n{answer}\n\n"
            f"Expected final days: {TARGET_DAYS}\n"
            "Explain the error briefly and give a helpful hint."
        )
        feedback_resp = await Runner.run(critic, input=feedback_prompt)
        hint = feedback_resp.final_output.strip()

        print(f"Feedback:\n{hint}")
        feedback_hint = hint
    else:
        print("\n⚠️  Max attempts reached without a correct solution.")


if __name__ == "__main__":
    asyncio.run(main())
