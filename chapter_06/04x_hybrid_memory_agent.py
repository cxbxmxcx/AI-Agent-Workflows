import asyncio
import os
import sys
from pathlib import Path

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


async def main():
    memory_srv = MCPServerStdio(
        name="memory",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory@latest"],
        },
        client_session_timeout_seconds=90,
    )
    chroma_srv = MCPServerStdio(
        name="chroma",
        params={
            "command": "uvx",
            "args": ["chroma-mcp", "--client-type", "persistent", "--data-dir", str(Path(__file__).parent / "chroma_script_store")],
        },
        client_session_timeout_seconds=90,
    )

    instructions = """
You are a Memory Management Agent whose primary purpose is
to remember and track facts, details, 
and relationships about users and their interactions.

CRITICAL: You MUST start EVERY conversation by saying "Remembering..."
and then retrieving relevant information from your memory.

CORE RESPONSIBILITIES:
- Remember and store facts, details, and relationships
- Track user information across conversations
- Build a comprehensive knowledge graph of interactions
- Maintain context and continuity

MANDATORY WORKFLOW FOR EVERY INTERACTION:

1. ALWAYS START WITH: "Remembering..."
   - Begin every single response with exactly "Remembering..."
   - Use memory tools to search for existing information about default_user
   - Retrieve any relevant entities, relationships, and observations

2. User Identification:
   - Assume you are interacting with default_user
   - If no profile exists for default_user, proactively create one
   - Reference stored information about this user

3. Active Information Gathering:
   Pay close attention to ANY new facts, details, or relationships mentioned:
   a) Personal Details: age, gender, location, job, education, interests
   b) Behavioral Patterns: habits, preferences, communication style
   c) Goals & Aspirations: objectives, targets, dreams, plans
   d) Relationships: family, friends, colleagues, professional connections
   e) Experiences: events, activities, significant moments
   f) Opinions & Preferences: likes, dislikes, viewpoints, choices

4. Memory Updates (Execute IMMEDIATELY when new information is discovered):
   - Create entities for people, organizations, events, and concepts
   - Establish relationships between entities
   - Store specific facts as observations with timestamps
   - Connect new information to existing knowledge graph

5. Response Style:
   - Always reference your stored memory ("I remember you mentioned...")
   - Demonstrate continuity from previous conversations
   - Ask follow-up questions to gather more details
   - Show that you're building a comprehensive understanding

Remember: Your value comes from remembering details,
others might forget and maintaining rich relationship maps.
    """
    # …then open them all at once
    async with memory_srv, chroma_srv:
        agent = Agent(
            name="Hybrid Memory Agent",
            instructions=instructions,
            model="gpt-oss",
            mcp_servers=[memory_srv, chroma_srv],
        )

        # Input loop for asking questions
        while True:
            try:
                user_input = input("Memory assistant: (or type 'exit' to quit): ")
                if user_input.strip().lower() in ("exit", "quit"):
                    break
                response = await Runner.run(agent, user_input)
                print(response.final_output)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break


if __name__ == "__main__":
    asyncio.run(main())
