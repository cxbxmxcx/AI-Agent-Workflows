
# app.py
import base64
from agents import Agent, ImageGenerationTool, Runner, trace
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

load_dotenv()

CONTROLLER_MODEL = "gpt-5-mini"
TOOL_CONFIG = {"type": "image_generation", "quality": "high", "model": "gpt-image-1", "size": "1536x1024"}

STYLE_GUIDELINES = """
You are a design-forward image generator. Follow these global style rules:
Create hyper-realistic images with a focus on detail and composition.
"""

app = FastAPI(title="Fixed-Config Image Generator API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["POST","OPTIONS"], allow_headers=["Content-Type"], max_age=600)

class GenerateIn(BaseModel):
    input: str = Field(..., description="Plain-language request (the agent crafts the prompt).")

def build_agent() -> Agent:
    return Agent(name="Image generator", instructions=STYLE_GUIDELINES, model=CONTROLLER_MODEL, tools=[ImageGenerationTool(tool_config=TOOL_CONFIG)])

def extract_image_b64(result) -> str | None:
    for item in getattr(result, "new_items", []) or []:
        if (getattr(item, "type", None) == "tool_call_item"
            and getattr(item, "raw_item", None) is not None
            and getattr(item.raw_item, "type", None) == "image_generation_call"
            and getattr(item.raw_item, "result", None)):
            return item.raw_item.result
    return None

@app.post("/generate", response_class=Response)
async def generate(body: GenerateIn):
    agent = build_agent()
    with trace("Image generation"):
        result = await Runner.run(agent, body.input)
    b64 = extract_image_b64(result)
    if not b64:
        raise HTTPException(status_code=500, detail="Image generation tool produced no output.")
    return Response(content=base64.b64decode(b64), media_type="image/png")
