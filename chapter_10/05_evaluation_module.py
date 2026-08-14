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


class EvaluationResult(BaseModel):
    progress_assessment: str        # Narrative of what this step accomplished
    consistency_check: bool         # False if new evidence contradicts existing
    confidence_delta: float         # Positive = more confident, negative = less
    contradictions: list[str] = Field(default_factory=list)
    recommendation: str             # CONTINUE, REPLAN, ESCALATE, TERMINATE


evaluation_agent = Agent(
    name="Evaluator",
    instructions="""You are the evaluation module of a cognitive agent.
    After each execution step, you assess the quality of the results
    and the overall trajectory of the task.

    Assess:
    1. progress_assessment: Did this step advance us toward the goal?
       Be specific about what was gained or not gained.
    2. consistency_check: Are the new results consistent with previous
       findings? If not, flag contradictions.
    3. confidence_delta: Should confidence go up or down based on this
       step? Return a value from -0.3 to +0.3.
    4. contradictions: List any conflicts between new and existing
       evidence.
    5. recommendation: One of CONTINUE, REPLAN, ESCALATE, TERMINATE.
       - CONTINUE: Progress is good, proceed with current plan.
       - REPLAN: Evidence suggests current approach is wrong.
       - ESCALATE: Agent cannot resolve this, surface uncertainty.
       - TERMINATE: Goal is achieved with sufficient confidence.

    Be ruthless about quality. A finding with a low relevance_score
    or a quality_note flagging metadata should NOT increase confidence.
    Two consecutive steps with no new information should trigger
    REPLAN, not CONTINUE.""",
    output_type=EvaluationResult,
    model="gpt-oss",
)
