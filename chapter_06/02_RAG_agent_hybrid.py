import os
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import chromadb
import tiktoken
from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
)  # OpenAI Agents SDK
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
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

# ------------------------------------------------------------------
# 1. Load + chunk the script
# ------------------------------------------------------------------
script_text = (Path(__file__).parent / "sample_documents" / "back_to_the_future.txt").read_text(
    encoding="utf-8"
)


def simple_chunk(text, max_tokens=200):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    words, chunk, chunks = text.split(), [], []
    for w in words:
        if len(tokenizer.encode(" ".join(chunk + [w]))) > max_tokens:
            chunks.append(" ".join(chunk))
            chunk = [w]
        else:
            chunk.append(w)
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks


docs = simple_chunk(script_text, max_tokens=200)

# ------------------------------------------------------------------
# 2. Create (or connect to) a Chroma collection (uses Chroma's bundled
#    local embedding function, not an external embeddings API)
# ------------------------------------------------------------------
client = chromadb.PersistentClient(
    path=str(Path(__file__).parent / "chroma_script_store")  # on-disk so we reuse later
)
collection_name = "bttf_script"

# Try to get existing collection first
try:
    collection = client.get_collection(collection_name)
except Exception:
    # Collection doesn't exist, create it without embedding function
    collection = client.create_collection(name=collection_name)

# Populate once (skip if already populated)
if collection.count() == 0:
    collection.add(ids=[str(uuid.uuid4()) for _ in docs], documents=docs)


# ------------------------------------------------------------------
# 3. Define search tools for hybrid approach
# ------------------------------------------------------------------
@function_tool
def search_script_with_vector_similarity(query: str, top_k: int = 3) -> str:
    """Search the script using vector similarity (semantic search)."""
    res = collection.query(query_texts=[query], n_results=top_k)
    if res and "documents" in res and res["documents"] and res["documents"][0]:
        # Format results with clear separation and reference markers
        formatted_results = []
        for i, doc in enumerate(res["documents"][0]):
            formatted_results.append(f"[Reference {i + 1}]\n{doc}")
        return "\n\n".join(formatted_results)
    return "No relevant documents found."


@function_tool
def search_script_with_keyword(query: str, top_k: int = 3) -> str:
    """Search the script using basic keyword matching."""
    # Convert query to lowercase for case-insensitive search
    query_lower = query.lower()

    # Split query into individual words (remove short words)
    query_words = [
        word.strip() for word in query_lower.split() if len(word.strip()) > 2
    ]

    if not query_words:
        return "No relevant documents found."

    # Score each document based on keyword matches
    scored_docs = []
    for i, doc in enumerate(docs):
        doc_lower = doc.lower()
        score = 0

        # Count exact phrase matches (highest weight)
        if query_lower in doc_lower:
            score += 10

        # Count individual word matches
        for word in query_words:
            # Count occurrences of each word
            word_count = doc_lower.count(word)
            score += word_count * 2

        # Boost score for documents with multiple query words
        words_found = sum(1 for word in query_words if word in doc_lower)
        if len(query_words) > 1 and words_found > 1:
            score += words_found

        if score > 0:
            scored_docs.append((score, doc))

    # Sort by score (descending) and return top_k
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    # Format results with clear reference markers
    if scored_docs:
        formatted_results = []
        for i, (score, doc) in enumerate(scored_docs[:top_k]):
            formatted_results.append(f"[Reference {i + 1}]\n{doc}")
        return "\n\n".join(formatted_results)
    return "No relevant documents found."


# ------------------------------------------------------------------
# 4. Build the agent with hybrid search capabilities
# ------------------------------------------------------------------
agent = Agent(
    name="Script Agent",
    model="gpt-oss",
    instructions="""
You answer questions about the movie *Back to the Future*.
You have access to two search tools:
1. `search_script_with_vector_similarity` - Use for
   semantic/conceptual searches
2. `search_script_with_keyword` - Use for exact
   word/phrase searches
Use both tools when appropriate to get comprehensive
results.

IMPORTANT: You must always provide exact references
from the script.
- Quote relevant passages directly from the search
  results
- Use the [Reference X] markers to cite specific
  passages
- Do not make up information that isn't in the script
- If the script doesn't contain the requested
  information, say so clearly
- Always ground your answers in the actual script text
  provided by the search tools

Format your answers like this:
Based on the script:
[Quote from Reference 1]: "exact text from script"
[Quote from Reference 2]: "exact text from script"

Your interpretation: [your analysis based on the
quotes]
""",
    tools=[search_script_with_vector_similarity, search_script_with_keyword],
)


# ------------------------------------------------------------------
# 5. Test hybrid search with various queries
# ------------------------------------------------------------------
queries = [
    "Where does Doc tell Marty to meet him, and at what time?",
    "What happens at 1:15 AM",
    "one minute fifteen seconds",
    "Who is Doc Brown?",
    "time machine",
    "DeLorean",
]

for query in queries:
    print(f"\n{'=' * 60}")
    print(f"QUERY: {query}")
    print("=" * 60)
    result = Runner.run_sync(agent, query)
    print("\n--- ANSWER ---\n", result.final_output)
