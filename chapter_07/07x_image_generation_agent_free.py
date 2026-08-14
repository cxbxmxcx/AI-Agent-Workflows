# NOTE: NRP-friendly variant of 07_image_generation_agent.py.
# OpenAI's `ImageGenerationTool` (gpt-image-1) is a hosted tool tied to
# OpenAI's own backend and has no NRP equivalent, so it can't be redirected
# the way plain chat-completions calls can. This version swaps it out for a
# custom @function_tool that calls Pollinations.ai (https://pollinations.ai) —
# a free, no-API-key-required image generation service — so the lesson stays
# fully hands-on without requiring an OpenAI account or any cost.
import asyncio
import os
import subprocess
import sys
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
from openai import AsyncOpenAI

# Load environment variables from .env file
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


def open_file(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", path], check=False)  # macOS
    elif os.name == "nt":  # Windows
        os.startfile(path)  # type: ignore
    elif os.name == "posix":
        subprocess.run(["xdg-open", path], check=False)  # Linux/Unix
    else:
        print(f"Don't know how to open files on this platform: {sys.platform}")


@function_tool
def generate_image(prompt: str, file_name: str) -> str:
    """Generate an image from a text prompt using a free image generation
    service and save it locally.

    Args:
        prompt: A detailed description of the image to generate.
        file_name: A short, filesystem-safe name for the saved image (no extension).
    """
    encoded_prompt = urllib.parse.quote(prompt)
    seed = int(time.time())
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1024&height=1024&seed={seed}&nologo=true"
    )
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    os.makedirs("gen_images", exist_ok=True)
    image_path = os.path.join("gen_images", f"{file_name}.jpg")
    with open(image_path, "wb") as img_file:
        img_file.write(response.content)

    open_file(image_path)
    return f"Image saved to {image_path}"


async def main():
    agent = Agent(
        name="Image generator",
        instructions="""
You are an image-generating assistant. Use the generate_image tool to create
an image based on the user's request, then report where it was saved.

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
""",
        model="gpt-oss",
        tools=[generate_image],
    )

    image_description = "an agent generating an image"

    with trace("Image generation"):
        result = await Runner.run(agent, image_description)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
