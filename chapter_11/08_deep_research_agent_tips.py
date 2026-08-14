import asyncio

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
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

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

web_search_tool = ...  # WebSearchTool() or your own @function_tool
extract_tool = ...  # e.g., page extractor / cleaner
analyze_tool = ...  # e.g., code interpreter for stats

critic = Agent(
    name="Critic",
    instructions="Check completeness, bias, contradictions.",
    model="gpt-oss",
)
writer = Agent(
    name="Writer",
    instructions="Synthesize into a concise brief with citations.",
    model="gpt-oss",
)

researcher = Agent(
    name="ResearchPlanner",
    instructions=(
        "Break down the research goal. Always use web/doc tools for facts. "
        "Track sources and avoid unsupported claims."
    ),
    tools=[
        web_search_tool,
        extract_tool,
        analyze_tool,
        critic.as_tool(),
        writer.as_tool(),
    ],
    model="gpt-oss",
)

# Stream results to your UI
stream = Runner.run_streamed(
    researcher, "Map the 3 best open RAG rerankers and compare."
)


async def main():
    result = Runner.run_streamed(
        researcher, input="Map the 3 best open RAG rerankers and compare."
    )
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
