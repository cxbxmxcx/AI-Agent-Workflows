# app.py
# NOTE: NRP-friendly variant of 02_app.py.
# The original uses OpenAI's hosted `ImageGenerationTool` (gpt-image-1), which
# has no NRP equivalent. This version swaps it for a custom @function_tool
# that calls Pollinations.ai (https://pollinations.ai) -- a free, no-API-key
# image generation service -- same approach used in
# chapter_07/07x_image_generation_agent_free.py and
# chapter_07/08x_image_vision_critic_agents_free.py.
import os
import tempfile
import time
import urllib.parse

import requests
from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_trace_processors,
    trace,
)
from agents.tracing import TracingProcessor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

# Load environment variables from .env file (NRP_API_KEY / NRP_BASE_URL)
load_dotenv()

# Point the Agents SDK at the NRP (Nautilus) OpenAI-compatible endpoint
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


# Replace the default OpenAI-backend exporter with a local console printer,
# so utilization is visible without needing a real OpenAI API key
set_trace_processors([ConsoleTracingProcessor()])

# ----- Fixed configuration -----
CONTROLLER_MODEL = "gpt-oss"  # the LLM running the agent

STYLE_GUIDELINES = """
## Style Guidelines for All Images:

- **Consistency**: Each image should maintain the same photographic quality with 3D-rendered elements seamlessly integrated
- **Color Palette**: Use a consistent scheme of blues, purples, warm golds, and greens with pops of bright accent colors
- **Lighting**: Professional photography lighting with dramatic but warm tones
- **Infographics**: Semi-transparent holographic projections that don't overwhelm the main subjects
- **Characters**: AI robots should be cute, approachable, and distinctly different from each other while maintaining a family resemblance
- **Icons**: Use universally recognizable symbols (lightbulbs for ideas, gears for processing, hearts for alignment, etc.)
- **Mood**: Optimistic, educational, and slightly futuristic without being cold or intimidating

When calling generate_image, translate these style guidelines into a single
detailed prompt string describing the specific image requested.
"""

# ----- FastAPI -----
app = FastAPI(title="Fixed-Config Image Generator API (NRP/free)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to e.g. ["http://localhost:5173"]
    allow_credentials=False,  # keep False if you use "*"
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],  # browser preflight asks for this
    max_age=600,  # cache the preflight for 10 minutes
)


class GenerateIn(BaseModel):
    # The ONLY thing callers can change
    input: str = Field(
        ..., description="Plain-language request (the agent crafts the prompt)."
    )


@function_tool
def generate_image(prompt: str) -> str:
    """Generate an image from a text prompt using a free image generation
    service and save it to a temporary file.

    Args:
        prompt: A detailed description of the image to generate.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    seed = int(time.time())
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1536&height=1024&seed={seed}&nologo=true"
    )
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(response.content)
    tmp.close()
    return tmp.name


def build_agent() -> Agent:
    """
    Build a fresh agent per request to avoid cross-request memory/state.
    Tool configuration is FIXED here and not user-overridable.
    """
    return Agent(
        name="Image generator",
        instructions=STYLE_GUIDELINES,
        model=CONTROLLER_MODEL,
        tools=[generate_image],
    )


def extract_image_path(result) -> str | None:
    """
    Find the generate_image tool call's returned file path in the run result.
    """
    for item in getattr(result, "new_items", []) or []:
        if getattr(item, "type", None) == "tool_call_output_item" and isinstance(
            getattr(item, "output", None), str
        ):
            path = item.output
            if os.path.exists(path):
                return path
    return None


@app.post("/generate", response_class=Response)
async def generate(body: GenerateIn):
    # The only variable is the input text. Everything else is fixed in code.
    agent = build_agent()
    print(f"Generating image for input: {body.input}")
    with trace("Image generation"):
        result = await Runner.run(agent, body.input)

    image_path = extract_image_path(result)
    if not image_path:
        raise HTTPException(
            status_code=500, detail="Image generation tool produced no output."
        )

    print("Image generation successful, returning JPEG bytes.")
    with open(image_path, "rb") as f:
        jpeg_bytes = f.read()
    os.remove(image_path)
    # Return the JPEG bytes directly. No filenames, no JSON--just the image.
    return Response(content=jpeg_bytes, media_type="image/jpeg")
