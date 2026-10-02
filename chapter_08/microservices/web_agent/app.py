
# app.py
import os
from typing import Optional, List

from agents import Agent, Runner, WebSearchTool, trace
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

WEB_AGENT_MODEL = os.getenv("WEB_AGENT_MODEL", "gpt-5-mini")

SYSTEM_INSTRUCTIONS = """
You are a careful web research agent.
- Use the WebSearch tool to gather up-to-date facts.
- Prefer recent, reputable sources; avoid speculation.
- Answer concisely (3–6 bullets max) and include a short 'Sources:' section with direct URLs.
- If the question is ambiguous, briefly state assumptions you made.
"""

app = FastAPI(title="Web Search Agent API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["POST","OPTIONS"], allow_headers=["Content-Type"], max_age=600)

class SearchIn(BaseModel):
    query: str = Field(..., description="Search query or question to answer")
    recency_days: Optional[int] = Field(None, ge=1, le=3650, description="Prefer sources within N days")
    max_results: Optional[int] = Field(None, ge=1, le=20, description="Use at most this many results")
    region: Optional[str] = Field(None, description="User region, e.g., 'US', 'EU'")
    include_domains: Optional[List[str]] = Field(None, description="Preferred domains")
    exclude_domains: Optional[List[str]] = Field(None, description="Domains to avoid")

def build_agent(prefs: SearchIn) -> Agent:
    instructions = SYSTEM_INSTRUCTIONS
    if prefs.recency_days:
        instructions += f" Prefer sources published within the last {prefs.recency_days} days."
    if prefs.include_domains:
        instructions += " Prefer these domains if relevant: " + ", ".join(prefs.include_domains[:10]) + "."
    if prefs.exclude_domains:
        instructions += " Avoid these domains unless absolutely necessary: " + ", ".join(prefs.exclude_domains[:10]) + "."
    if prefs.region:
        instructions += f" Assume the user's region is {prefs.region}."

    return Agent(
        name="WebSearch",
        instructions=instructions,
        model=WEB_AGENT_MODEL,
        tools=[WebSearchTool()],
    )

@app.post("/search")
async def search(body: SearchIn):
    agent = build_agent(body)
    prompt = body.query
    try:
        with trace("web_search"):
            result = await Runner.run(agent, prompt)
        # We primarily rely on the LLM to include sources in its own text, but return the text separately
        answer = str(result.final_output)
        return {"answer": answer, "sources": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
