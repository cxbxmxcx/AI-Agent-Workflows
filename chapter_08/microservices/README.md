# Realtime Voice Agent (v3) — Image + Web Search tools

This version adds a **Web Search Agent** container built with the OpenAI **Agents SDK** and exposes it to the UI as a **tool**.

## Run

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
docker compose up --build
```

- Web UI: http://localhost:8000
- Image Agent: http://localhost:8001
- Web Search Agent: http://localhost:8002

In the UI:
- Click **“🎤 Connect mic”** to start talking.
- Type **`/search your query`** to trigger the search tool directly (or just ask normally; the agent will call the tool when appropriate).
- Type **`/image your prompt`** to generate an image via the image agent.

## How the Web Search Agent works

It uses the Agents SDK **WebSearchTool** (hosted) so the LLM can search the live web and cite sources. See the SDK docs for hosted tools and the web search tool. The agent is kept simple and stateless: we create a fresh agent per request and run it for a single turn.

You can bias behavior with body fields:
- `recency_days`: prefer recent sources (e.g., 30).
- `max_results`: hint the agent to use fewer results.
- `include_domains` / `exclude_domains`: preferences only (the hosted tool may not hard-filter).

## Security & prod notes

- Put the **web** service behind TLS.
- Lock the `/session` route to authenticated origins; rate-limit it.
- If you need **strict domain allow/deny**, front your web agent with your own search API and expose it as a function tool instead of the hosted WebSearchTool.
