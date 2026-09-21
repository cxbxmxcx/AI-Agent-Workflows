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

from agents import Agent, Runner, trace


def open_file(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", path], check=False)  # macOS
    elif os.name == "nt":  # Windows
        os.startfile(path)  # type: ignore
    elif os.name == "posix":
        subprocess.run(["xdg-open", path], check=False)  # Linux/Unix
    else:
        print(f"Don't know how to open files on this platform: {sys.platform}")


async def main():
    agent = Agent(
        name="Image generator",
        instructions="""
## Style Guidelines for All Images:

- **Consistency**: Each image should maintain the same photographic quality with 3D-rendered elements seamlessly integrated
- **Color Palette**: Use a consistent scheme of blues, purples, warm golds, and greens with pops of bright accent colors
- **Lighting**: Professional photography lighting with dramatic but warm tones
- **Infographics**: Semi-transparent holographic projections that don't overwhelm the main subjects
- **Characters**: AI robots should be cute, approachable, and distinctly different from each other while maintaining a family resemblance
- **Icons**: Use universally recognizable symbols (lightbulbs for ideas, gears for processing, hearts for alignment, etc.)
- **Mood**: Optimistic, educational, and slightly futuristic without being cold or intimidating
""",
        model=agents_config.model("gpt-5-mini"),
        tools=[agents_config.image_tool(size="1536x1024")],
    )

    image_description = "an agent generating an image"
    image_name = "agent_image_generation"
    image_path = os.path.join("gen_images", f"{image_name}.png")

    with trace("Image generation"):
        result = await Runner.run(agent, image_description)
        print(result.final_output)
        if agents_config.save_image(result, image_path):
            open_file(image_path)


if __name__ == "__main__":
    asyncio.run(main())
