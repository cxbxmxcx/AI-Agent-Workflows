import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field
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


# --- Collaboration types ---

class Contribution(BaseModel):
    """A single agent's contribution to the shared state."""
    agent_name: str = ""
    content: str = ""
    critique: str = ""
    suggestions: list[str] = []
    agrees_goal_met: bool = False
    confidence: float = 0.0


class CollaborationState(BaseModel):
    """Shared state for a collaborative agent loop."""
    goal: str
    contributions: list[Contribution] = Field(
        default_factory=list
    )
    round_number: int = 0
    max_rounds: int = 5
    consensus_threshold: float = 0.8

    @property
    def has_consensus(self) -> bool:
        if len(self.contributions) < 2:
            return False
        recent = self.contributions[-3:]
        if not recent:
            return False
        agreeing = sum(1 for c in recent if c.agrees_goal_met)
        return agreeing / len(recent) >= self.consensus_threshold

    def recent_context(self, n: int = 6) -> str:
        recent = self.contributions[-n:]
        return str([
            dict(agent=c.agent_name, content=c.content[:500],
                 critique=c.critique, agrees=c.agrees_goal_met)
            for c in recent
        ])


# --- Collaborative agents ---

researcher_agent = Agent(
    name="Collaborative Researcher",
    instructions="""
You are a researcher in a collaborative team.
Review the shared state and previous contributions. Search for
new information that fills gaps identified by the critic or
extends existing findings.
Return your findings as content, note any concerns as critique,
and suggest next steps for the team.
Set agrees_goal_met to true only if you believe the research
goal is comprehensively answered.
""",
    model="gpt-oss",
    output_type=Contribution,
)

critic_agent = Agent(
    name="Collaborative Critic",
    instructions="""
You are a critic in a collaborative team.
Review the shared state and all contributions so far.
Your job is to:
1. Identify weaknesses, gaps, or unsupported claims in findings
2. Challenge assumptions and flag contradictions
3. Suggest specific areas that need more research
Be constructive but rigorous. Set agrees_goal_met to true only
if you believe the collective findings are strong, well-sourced,
and comprehensive enough to answer the goal.
""",
    model="gpt-oss",
    output_type=Contribution,
)

synthesizer_agent = Agent(
    name="Collaborative Synthesizer",
    instructions="""
You are a synthesizer in a collaborative team.
Review all contributions and weave them into a coherent
narrative. Resolve contradictions flagged by the critic,
integrate the researcher's findings, and produce a unified
summary.
Set agrees_goal_met to true if the synthesized output
comprehensively answers the research goal.
Your confidence score should reflect how complete and
well-supported the synthesis is.
""",
    model="gpt-oss",
    output_type=Contribution,
)


# --- Collaboration loop ---

async def run_collaboration_loop(
    goal: str, max_rounds: int = 5
) -> CollaborationState:
    agents = [researcher_agent, critic_agent,
              synthesizer_agent]
    search_server = MCPServerStdio(
        name="Brave Search",
        params={
            "command": "npx",
            "args": ["-y", "@anthropic/brave-search-mcp"],
            "env": {"BRAVE_API_KEY": os.environ["BRAVE_API_KEY"]},
        },
        client_session_timeout_seconds=90,
    )
    async with search_server:
        agents[0] = researcher_agent.clone(
            mcp_servers=[search_server]
        )
        state = CollaborationState(
            goal=goal, max_rounds=max_rounds
        )

        agent_index = 0
        while (state.round_number < state.max_rounds
               and not state.has_consensus):
            current_agent = agents[agent_index % len(agents)]
            collab_input = dict(
                goal=state.goal,
                your_role=current_agent.name,
                round=state.round_number + 1,
                recent_contributions=state.recent_context(),
            )

            print(f"\nRound {state.round_number + 1}, "
                  f"Agent: {current_agent.name}")

            result = await Runner.run(
                current_agent, input=str(collab_input)
            )
            contribution = result.final_output
            contribution.agent_name = current_agent.name
            state.contributions.append(contribution)

            print(f"  Content: {contribution.content[:100]}...")
            if contribution.critique:
                print(f"  Critique: {contribution.critique[:80]}...")
            if contribution.suggestions:
                print(f"  Suggestions: {len(contribution.suggestions)}")
            print(f"  Agrees goal met: "
                  f"{contribution.agrees_goal_met} "
                  f"(confidence: {contribution.confidence:.0%})")

            agent_index += 1
            if agent_index % len(agents) == 0:
                state.round_number += 1
                print(f"\n--- Round {state.round_number} complete ---")
                if state.has_consensus:
                    print("  Consensus reached!")

        return state


async def main():
    state = await run_collaboration_loop(
        goal="What are the latest advances in solid-state batteries "
             "and which companies are leading commercialization?",
        max_rounds=4,
    )
    print(f"\n{'='*50}")
    print(f"Collaboration complete after "
          f"{state.round_number} rounds")
    print(f"Total contributions: {len(state.contributions)}")
    print(f"Consensus reached: {state.has_consensus}")

    print(f"\nContributions by agent:")
    for agent_name in ["Collaborative Researcher",
                       "Collaborative Critic",
                       "Collaborative Synthesizer"]:
        count = sum(1 for c in state.contributions
                    if c.agent_name == agent_name)
        print(f"  {agent_name}: {count}")

    if state.contributions:
        final = state.contributions[-1]
        print(f"\nFinal contribution ({final.agent_name}):")
        print(f"  {final.content[:300]}...")


asyncio.run(main())
