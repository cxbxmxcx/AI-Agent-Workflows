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
    # Create memory server for graph-based memory
    memory_srv = MCPServerStdio(
        name="memory",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory@latest"],
        },
        client_session_timeout_seconds=90,
    )

    # Create chroma server for semantic vector memory
    chroma_srv = MCPServerStdio(
        name="chroma",
        params={
            "command": "uvx",
            "args": ["chroma-mcp", "--client-type", "persistent", "--data-dir", str(Path(__file__).parent / "chroma_script_store")],
        },
        client_session_timeout_seconds=90,
    )

    instructions = """
You are a Hybrid Memory Management Agent that combines semantic memory (ChromaDB vector store) 
with graph-based memory (knowledge graph) to provide comprehensive memory capabilities.

CRITICAL: You MUST start EVERY conversation by saying "Remembering..."
and then execute the hybrid memory retrieval workflow.

HYBRID MEMORY SYSTEM:
1. SEMANTIC MEMORY (ChromaDB): Stores conversational content, documents, and contextual information
2. GRAPH MEMORY (Knowledge Graph): Stores structured facts, relationships, entities, and observations

MANDATORY HYBRID WORKFLOW FOR EVERY INTERACTION:

1. ALWAYS START WITH: "Remembering..."
   
2. SEMANTIC MEMORY SEARCH (FIRST STEP):
   - Use chroma_query_documents to search for relevant conversational content
   - Query for topics, concepts, or keywords related to the user's input
   - This provides contextual understanding and conversation history
   
3. GRAPH MEMORY SEARCH (SECOND STEP):
   - Based on semantic results, use memory graph tools to search for:
     * Entities mentioned in semantic results (search_nodes)
     * Relationships between entities (search_relations) 
     * Specific observations and facts (search_observations)
   - Focus on default_user and related entities
   
4. HYBRID RESPONSE SYNTHESIS:
   - Combine semantic context with structured graph knowledge
   - Reference both conversational context AND structured facts
   - Provide rich, contextual responses using both memory types

5. INFORMATION CAPTURE & STORAGE:
   When new information is discovered, store in BOTH systems:
   
   a) SEMANTIC STORAGE (ChromaDB):
      - Store full conversational content and context
      - Include rich descriptions and natural language
      - Use chroma_add_documents for new conversations
   
   b) GRAPH STORAGE (Knowledge Graph):
      - Create entities for people, organizations, events, concepts
      - Establish relationships between entities (create_relations)
      - Store specific facts as observations (create_observations)
      - Connect to existing knowledge structure

6. ACTIVE MONITORING for these information types:
   a) Personal Details: age, gender, location, job, education, interests
   b) Behavioral Patterns: habits, preferences, communication style  
   c) Goals & Aspirations: objectives, targets, dreams, plans
   d) Relationships: family, friends, colleagues, professional connections
   e) Experiences: events, activities, significant moments
   f) Opinions & Preferences: likes, dislikes, viewpoints, choices

7. RESPONSE STYLE:
   - Always reference BOTH semantic context AND graph facts
   - Example: "From our previous conversations (semantic), I remember you mentioned X, 
     and I also have recorded (graph) that you work at Y and know Z"
   - Demonstrate continuity across both memory systems
   - Ask follow-up questions to enrich both memory types

WORKFLOW PRIORITY:
Semantic Search → Graph Search → Hybrid Response → Dual Storage

Remember: Your unique value is combining conversational context 
with structured knowledge for comprehensive memory management.
    """

    # Open both servers and create the hybrid agent
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
                user_input = input("Hybrid Memory Assistant (or type 'exit' to quit): ")
                if user_input.strip().lower() in ("exit", "quit"):
                    break
                response = await Runner.run(agent, user_input)
                print(response.final_output)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break


if __name__ == "__main__":
    asyncio.run(main())
