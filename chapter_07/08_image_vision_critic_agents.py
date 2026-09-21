import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

import asyncio
import os
import subprocess
import sys

from agents import Agent, Runner, function_tool, trace
from pydantic import BaseModel


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
def describe_image(image_path: str, prompt: str) -> str:
    """Describe the image using the GPT-5 model.
    Args:
        image_path (str): Path to the image file.
        prompt (str): Prompt to guide the description.
    Returns:
        str: Description of the image.
    """
    return agents_config.vision_completion(
        image_path,
        "what's in this image?",
        agents_config.vision_model("gpt-5-mini"),
    )


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
        instructions=style_guidelines,
        model=agents_config.model("gpt-5-mini"),
        tools=[agents_config.image_tool(size="1536x1024")],
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
{style_guidelines}
{rubric}
""",
        model=agents_config.model("gpt-5-mini"),  # Specify the model to use
        tools=[describe_image],
        output_type=CritqueImage,
    )

    image_description = "an agent generating an image"
    image_name = "agent_image_generation"
    image_path = os.path.join("gen_images", f"{image_name}.png")
    feedback = ""

    with trace("Image generation"):
        while failing := True:
            print(f"Generating image with description: {image_description} {feedback}")
            input = dict(
                description=image_description,
                feedback=feedback,
            )
            result = await Runner.run(agent, str(input))
            print(result.final_output)
            agents_config.save_image(result, image_path)
            critique_result = await Runner.run(
                critic,
                f"Please critique the image at {image_path} with the prompt: {image_description}",
            )
            critique = critique_result.final_output
            failing = critique.image_pass is False
            feedback = critique.feedback
            print(f"Critique eval: {failing}")
    print(f"Final image saved at: {image_path}")
    open_file(image_path)


if __name__ == "__main__":
    asyncio.run(main())
