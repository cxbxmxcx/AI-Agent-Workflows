from typing import Literal

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
from agents.mcp import MCPServerStdio
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

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


set_trace_processors([ConsoleTracingProcessor()])

MAX_TURNS = 3  # iteration cap

thinking_srv = MCPServerStdio(
    name="sequential-thinking",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
    },
    client_session_timeout_seconds=90,
)


class Answer(BaseModel):
    status: Literal["ok", "needs_followup"] = "ok"
    checklist: list[str] = []
    summary: str
    sources: list[str]


instructions = f"""
You are a planner-executor.
If the message starts with 'PLAN ONLY', 
return only the checklist (no actions).
1) Plan→Execute: draft a concise 3–5 item checklist, then execute.
2) ReAct: Thought→Action(tool)→Observation; 
inspect each observation before continuing.
3) Limit: stop after at most {MAX_TURNS} tool calls; 
if reached, set status='needs_followup' and return best effort.
4) Self-review: before final, catch obvious mistakes, 
ensure the question is answered, and cite sources.
Use seq_think between actions to decide the next step. 
Return Answer JSON only.
"""


async def main():
    agent = Agent(
        name="Planner",
        instructions=instructions,
        mcp_servers=[thinking_srv],
        output_type=Answer,
        model="gpt-oss",
    )

    async with thinking_srv:
        question = "Summarize our refund policy and cite relevant internal docs."
        plan = await Runner.run(agent, f"PLAN ONLY. Question: {question}")
        print(plan.final_output.checklist)

        result = await Runner.run(agent, question)
        print(result.final_output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
