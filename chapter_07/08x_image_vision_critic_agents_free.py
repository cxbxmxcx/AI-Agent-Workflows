# NOTE: NRP-friendly variant of 08_image_vision_critic_agents.py.
# The original uses two OpenAI-only capabilities: `ImageGenerationTool`
# (gpt-image-1, a hosted tool with no NRP equivalent) and vision/image-input
# via the Responses API. This version replaces image generation with a
# custom @function_tool calling Pollinations.ai (free, no API key), and
# replaces the vision call with NRP's `gemma-small` model, which was
# confirmed to support multimodal (image_url) chat-completions input —
# unlike NRP's other hosted models (gpt-oss, qwen3, kimi don't return usable
# output for image input; minimax-m2 and glm-5 explicitly reject it as
# "not a multimodal model").
import asyncio
import base64
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
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
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Point the Agents SDK at the NRP (Nautilus) OpenAI-compatible endpoint
client = AsyncOpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=os.getenv("NRP_API_KEY"),
)
set_default_openai_client(client, use_for_tracing=False)
set_default_openai_api("chat_completions")

# A plain sync client for the vision call inside describe_image, mirroring
# how the original file makes its own direct client call from within a tool.
vision_client = OpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=os.getenv("NRP_API_KEY"),
)


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


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


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
        f"?width=1536&height=1024&seed={seed}&nologo=true"
    )
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    os.makedirs("gen_images", exist_ok=True)
    image_path = os.path.join("gen_images", f"{file_name}.jpg")
    with open(image_path, "wb") as img_file:
        img_file.write(response.content)

    return image_path


@function_tool
def describe_image(image_path: str, prompt: str) -> str:
    """Describe the image using a vision-capable NRP model.
    Args:
        image_path (str): Path to the image file.
        prompt (str): Prompt to guide the description.
    Returns:
        str: Description of the image.
    """
    base64_image = encode_image(image_path)

    response = vision_client.chat.completions.create(
        model="gemma-small",  # the NRP model confirmed to support image input
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content


style_guidelines = """
## Style Guidelines for All Images:

- **Consistency**: Each image should maintain the same photographic quality with 3D-rendered elements seamlessly integrated
- **Color Palette**: Use a consistent scheme of blues, purples, warm golds, and greens with pops of bright accent colors
- **Lighting**: Professional photography lighting with dramatic but warm tones
- **Infographics**: Semi-transparent holographic projections that don't overwhelm the main subjects
- **Characters**: AI robots should be cute, approachable, and distinctly different from each other while maintaining a family resemblance
- **Icons**: Use universally recognizable symbols (lightbulbs for ideas, gears for processing, hearts for alignment, etc.)
- **Mood**: Optimistic, educational, and slightly futuristic without being cold or intimidating
"""

rubric = """
Score the image on a scale of 1 to 5 using the following scale:
1. **Poor**: The image does not meet the style guidelines at all.
2. **Fair**: The image meets some of the style guidelines but has significant issues.
3. **Good**: The image meets most of the style guidelines but has minor issues.
4. **Very Good**: The image meets all the style guidelines with only a few minor issues.
5. **Excellent**: The image meets all the style guidelines perfectly.
Pass the image if it scores 2 or higher, otherwise fail it.
"""


async def main():
    agent = Agent(
        name="Image generator",
        instructions=f"""
You are an image-generating assistant. Use the generate_image tool to create
an image based on the user's request, translating the style guidelines below
into a single detailed prompt string.
{style_guidelines}
""",
        model="gpt-oss",
        tools=[generate_image],
    )

    class CritqueImage(BaseModel):
        """Result of critiquing image."""

        image_pass: bool
        feedback: str

    critic = Agent(
        name="Image Critic",
        instructions=f"""You are an image critic.
Your task is to evaluate the quality of generated images
based on the provided specific criteria and style guidelines.
Use the describe_image tool to see what's actually in the image before scoring it.
{style_guidelines}
{rubric}
""",
        model="gpt-oss",
        tools=[describe_image],
        output_type=CritqueImage,
    )

    image_description = "an agent generating an image"
    image_name = "agent_image_generation"
    feedback = ""
    image_path = ""

    with trace("Image generation"):
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"Generating image with description: {image_description} {feedback}")
            input = dict(
                description=image_description,
                feedback=feedback,
                file_name=image_name,
            )
            result = await Runner.run(agent, str(input))
            print(result.final_output)
            for item in result.new_items:
                if item.type == "tool_call_output_item" and isinstance(item.output, str):
                    if item.output.startswith("gen_images"):
                        image_path = item.output

            if not image_path:
                print("No image was generated this attempt, retrying...")
                continue

            critique_result = await Runner.run(
                critic,
                f"Please critique the image at {image_path} with the prompt: {image_description}",
            )
            critique = critique_result.final_output
            print(f"Critique eval: pass={critique.image_pass} feedback={critique.feedback}")
            if critique.image_pass:
                break
            feedback = critique.feedback
        else:
            print(f"Reached {max_attempts} attempts without a passing image; using the last one.")

    print(f"Final image saved at: {image_path}")
    if image_path:
        open_file(image_path)


if __name__ == "__main__":
    asyncio.run(main())
