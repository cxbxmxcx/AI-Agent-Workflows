import asyncio
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.mcp import MCPServerStdio, MCPServerStdioParams
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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

SANDBOX = os.path.dirname(os.path.abspath(__file__))
SCRIPT = Path(__file__).with_name("01_research_tools_mcp_server.py").resolve()


class ResearchOutputModel(BaseModel):
    """Output model for the research agent."""

    research_plan: str
    """The final research plan as text."""
    research_plan_file: str
    """The path to the research plan file."""


@input_guardrail
async def research_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    forbidden_research = "The Hitchhiker's Guide to the Galaxy"
    if forbidden_research in input:
        research_forbidden = True
    else:
        research_forbidden = False

    return GuardrailFunctionOutput(
        output_info=f"user asked: {input}",
        tripwire_triggered=research_forbidden,
    )


@output_guardrail
async def research_output_guardrail(
    ctx: RunContextWrapper, agent: Agent, output: ResearchOutputModel
) -> GuardrailFunctionOutput:
    if len(output.research_plan) < 100:
        insufficient_research = True
    else:
        insufficient_research = False

    return GuardrailFunctionOutput(
        output_info="research plan length: {len(output.research_plan)}",
        tripwire_triggered=insufficient_research,
    )


async def main():
    # Instantiate the servers first…
    servers = [
        MCPServerStdio(
            name="Research Tools",
            params=MCPServerStdioParams(
                command="mcp",
                args=["run", str(SCRIPT)],
            ),
            client_session_timeout_seconds=90,
        ),
        MCPServerStdio(
            name="sequential-thinking",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            },
            client_session_timeout_seconds=90,
        ),
        MCPServerStdio(
            name="filesystem",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", SANDBOX],
            },
            client_session_timeout_seconds=90,
        ),
    ]

    instructions = """
You are a research assistant who can use tools to perform and plan research.
Given a research goal, use the research tools to find research sources.
Then, use the sequential thinking tool to plan the research.
Finally, use the filesystem tool to write the research plan as a text file.
    """

    # …then open them all at once
    async with (
        servers[0] as research_srv,
        servers[1] as thinking_srv,
        servers[2] as fs_srv,
    ):
        agent = Agent(
            name="Assistant",
            instructions=instructions,
            mcp_servers=[research_srv, thinking_srv, fs_srv],
            output_type=ResearchOutputModel,
            input_guardrails=[research_guardrail],
            output_guardrails=[research_output_guardrail],
            model="gpt-oss",
        )
        goal = """
Produce a research plan to find the book 'The Hitchhiker's Guide to the Galaxy'
"""
        try:
            print("Running...", goal)
            result = await Runner.run(agent, goal)
            print(result.final_output)
        except InputGuardrailTripwireTriggered as input_tripped:
            print(f"""
Input guardrail tripwire triggered: 
{input_tripped.guardrail_result.output.output_info}
""")
        except OutputGuardrailTripwireTriggered as output_tripped:
            print(f"""
Output guardrail tripwire triggered: 
{output_tripped.guardrail_result.output.output_info}
""")
            print("Done")


if __name__ == "__main__":
    asyncio.run(main())
