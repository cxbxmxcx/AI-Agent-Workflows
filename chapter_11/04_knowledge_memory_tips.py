import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from agents import (
    Agent,
    Runner,
    SQLiteSession,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)
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

kb = load_vector_kb(  # your FAISS/Weaviate/Chroma wrapper
    embedding_model="qwen3-embedding",  # choose embeddings deliberately
    index="HNSW",  # ANN (HNSW/IVF)
    shards=["product", "policy", "engineering"],  # shard by domain
)


@function_tool
def retrieve(
    query: str,
    product: str | None = None,
    version: str | None = None,
    date: str | None = None,
    role: str | None = None,
    tenant: str | None = None,
) -> str:
    """Return grounded snippets using metadata filters."""
    return kb.query(
        query=query,
        k=5,
        filters={
            "product": product,
            "version": version,
            "date": date,
            "role": role,
            "tenant": tenant,
        },
    )


@function_tool
def remember(user_id: str, fact: str) -> str:
    """Persist long‑term user fact in vector memory; prune aggressively."""
    kb.upsert(
        text=fact, metadata={"user_id": user_id, "kind": "preference"}, ttl_days=90
    )
    return "ok"


agent = Agent(
    name="Support",
    instructions=(
        "Use ONLY retrieved context; cite chunk ids; if absent say 'I don't know'."
    ),
    tools=[retrieve, remember],
    model="gpt-oss",
)
session = SQLiteSession("u42-chat")  # short‑term session memory per thread

kb.ingest(
    "docs/*.md",
    chunking="semantic",
    partition_by=["role", "tenant", "product", "version"],
)  # refresh nightly

print(
    Runner.run_sync(
        agent, "Can I use the beta API on v3.2? (tenant=acme)", session=session
    )
)
