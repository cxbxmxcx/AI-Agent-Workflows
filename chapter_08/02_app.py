import pathlib as _pathlib
import sys as _sys

_root = next(p for p in _pathlib.Path(__file__).resolve().parents
             if (p / "agents_config.py").is_file())
_sys.path.insert(0, str(_root))

import agents_config  # noqa: E402,F401

# app.py
import os
import tempfile

# Agents SDK (matches your example import path)
from agents import Agent, Runner, trace
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Load environment variables from .env file (e.g. OPENAI_API_KEY)
load_dotenv()

# ----- Fixed configuration -----
# the LLM running the agent
CONTROLLER_MODEL = agents_config.model("gpt-5-mini")

STYLE_GUIDELINES = """
## Style Guidelines for All Images:

- **Consistency**: Each image should maintain the same photographic quality with 3D-rendered elements seamlessly integrated
- **Color Palette**: Use a consistent scheme of blues, purples, warm golds, and greens with pops of bright accent colors
- **Lighting**: Professional photography lighting with dramatic but warm tones
- **Infographics**: Semi-transparent holographic projections that don't overwhelm the main subjects
- **Characters**: AI robots should be cute, approachable, and distinctly different from each other while maintaining a family resemblance
- **Icons**: Use universally recognizable symbols (lightbulbs for ideas, gears for processing, hearts for alignment, etc.)
- **Mood**: Optimistic, educational, and slightly futuristic without being cold or intimidating
"""

# ----- FastAPI -----
app = FastAPI(title="Fixed-Config Image Generator API", version="1.0.0")

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


def build_agent() -> Agent:
    """
    Build a fresh agent per request to avoid cross-request memory/state.
    Tool configuration is FIXED here and not user-overridable.
    """
    return Agent(
        name="Image generator",
        instructions=STYLE_GUIDELINES,
        model=CONTROLLER_MODEL,
        tools=[agents_config.image_tool(size="1536x1024")],
    )


@app.post("/generate", response_class=Response)
async def generate(body: GenerateIn):
    # The only variable is the input text. Everything else is fixed in code.
    with tempfile.TemporaryDirectory() as workdir:
        image_path = os.path.join(workdir, "image.png")
        agent = build_agent()
        print(f"Generating image for input: {body.input}")
        with trace("Image generation"):
            result = await Runner.run(agent, body.input)

        png_bytes = agents_config.save_image(result, image_path)
        if not png_bytes:
            raise HTTPException(
                status_code=500, detail="Image generation tool produced no output."
            )

    print("Image generation successful, returning PNG bytes.")
    # Return the PNG bytes directly. No filenames, no JSON—just the image.
    return Response(content=png_bytes, media_type="image/png")
