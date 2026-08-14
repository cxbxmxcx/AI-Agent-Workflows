import asyncio
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
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


class ResearchPlanModel(BaseModel):
    """Output model for the research plan."""

    research_plan: str
    """The final research plan as text."""
    feedback: str
    """Feedback on the research plan."""
    is_sufficiently_detailed: bool
    """Flag to indicate if the research plan is sufficiently detailed."""


research_plan_guardrail_agent = Agent(
    name="Research Plan Guardrail Agent",
    instructions="""
You are an output guardrail agent.
Confirm the research plan is sufficiently detailed, atleast 1000 characters in length.
If it is not sufficiently detailed, flag it and provide feedback.
""",
    output_type=ResearchPlanModel,
    model="gpt-oss",
)


@output_guardrail
async def research_plan_guardrail(
    ctx: RunContextWrapper, agent: Agent, output: ResearchPlanModel
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        research_plan_guardrail_agent, output.research_plan, context=ctx.context
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_sufficiently_detailed,
    )


async def main():
    # Instantiate the agents first…
    research_agent = Agent(
        name="Research Agent",
        instructions="""
You are a research assistant.
Your role is to find research sources. 
Do not make up or invent any research sources.
Always hand off to the thinking agent.
""",
        model="gpt-oss",
    )
    thinking_agent = Agent(
        name="Thinking Agent",
        instructions="""
You are a research planning assistant.
Your role is to plan the research.
You will receive a list of research sources from the research agent.
Use the sequentialThinking tool to create a research plan based on the sources.
Always hand off to the filesystem agent.
""",
        output_type=ResearchPlanModel,
        output_guardrails=[research_plan_guardrail],
        model="gpt-oss",
    )
    filesystem_agent = Agent(
        name="Filesystem Agent",
        instructions="""
You are a filesystem assistant.
Your role is to write the output as a text file.
Never make up or invent any ouput.
""",
        model="gpt-oss",
    )
    # Instantiate the servers next…
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

    # …then open them all at once
    async with (
        servers[0] as research_srv,
        servers[1] as thinking_srv,
        servers[2] as fs_srv,
    ):
        goal = """
Produce a research plan to find the book 'The Hitchhiker's Guide to the Galaxy'
"""
        print("Running...", goal)
        research_agent.mcp_servers = [research_srv]
        result = await Runner.run(research_agent, goal)
        thinking_agent.mcp_servers = [thinking_srv]
        final_output = result.final_output
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await Runner.run(thinking_agent, final_output)
                final_output = result.final_output.research_plan
                break
            except OutputGuardrailTripwireTriggered as output_tripped:
                final_output = output_tripped.guardrail_result.output.output_info.feedback
            if attempt == max_retries - 1:
                final_output = "A research plan was not generated. Please try again with a different goal."
        filesystem_agent.mcp_servers = [fs_srv]
        result = await Runner.run(filesystem_agent, final_output)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
