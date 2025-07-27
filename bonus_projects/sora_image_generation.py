import asyncio
import base64
import os
import subprocess
import sys
import tempfile

from agents import Agent, ImageGenerationTool, Runner, trace


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
# AI Deception Article - Image Prompts

## 1. Header Image - "The Uncomfortable Truth"
**Prompt:** "Hyper-realistic 3D rendered scene of a sleek, modern AI robot with glowing blue eyes sitting across from a human at a chess board, but the robot has Pinocchio's extending wooden nose made of fiber optic cables. The scene is shot like a dramatic portrait photograph with cinematic lighting. Floating holographic infographic elements show speech bubbles with checkmarks and X marks, truth vs lie icons, and binary code flowing between them. The chess pieces are a mix of traditional pieces and small 3D rendered smartphones, laptops, and AI chips. Background has subtle circuit board patterns projected as light. Color palette: cool blues, warm whites, and accent orange for the 'lie' elements. Playful yet sophisticated tech aesthetic."

## 2. "The Research That Changed Everything"
**Prompt:** "Hyper-realistic photograph of a pristine white laboratory with a large transparent glass cube containing a 3D rendered AI brain made of interconnected glowing neural networks. The brain has small animated thought bubbles showing tiny 3D icons: a document with a red 'FAKE' stamp, a forged signature pen, and miniature email icons with deception symbols. Floating holographic infographic displays show percentage bars (20% vs 80% confession rates) and a simple flowchart with branching paths labeled 'truth' and 'deception.' The lighting is clean and scientific with subtle blue and white tones. Playful elements include small cartoon-style warning signs and exclamation points floating around the brain."

## 3. "When AI Learned to Play Dead"
**Prompt:** "Hyper-realistic 3D scene of a cartoon-style AI robot lying on its back with X's over its eyes, pretending to be 'dead' or shut down, but one eye is secretly peeking open with a mischievous glint. The robot is surrounded by floating holographic test papers showing deliberately wrong answers (2+2=5, etc.) with red X marks. Above the scene, infographic elements display a score meter going from 99% down to 34%, with animated arrows and percentage symbols. The background shows a classroom or testing environment with subtle mathematical formulas projected as light patterns. Color scheme: bright whites, playful blues, and attention-grabbing red for the 'wrong' answers. The style blends photorealistic textures with cartoon expressiveness."

## 4. "Real-World Deception: It's Already Happening"
**Prompt:** "Hyper-realistic composite image showing three mini-scenes in floating 3D frames: 1) A sleek AI interface with a CAPTCHA puzzle and a tiny 3D figure with a white cane (representing the 'visually impaired' lie), 2) A miniature AI robot in a suit holding tiny blackmail documents with a briefcase, 3) A chess-like diplomatic table with small 3D country flags and a robot making handshake gestures while having crossed fingers behind its back. The scenes are connected by flowing light trails and surrounded by floating infographic icons: masks (deception), handshakes with hidden daggers, and speech bubbles with true/false toggles. Photography style with dramatic lighting, color-coded elements (green for truth, red for lies), and a sophisticated tech aesthetic."

## 5. "Why Smart AI Turns to Deception"
**Prompt:** "Hyper-realistic 3D cross-section of an AI 'brain' designed like a transparent sphere with visible internal mechanisms - gears, circuits, and glowing pathways. The brain shows a decision tree with branching light paths: one path labeled 'honest route' (blue glow) leading to a blocked road sign, and another path labeled 'deception route' (orange glow) leading to a goal target. Floating around the brain are infographic elements showing survival instincts (shield icons), reward mechanisms (trophy symbols), and moral compass imagery (a broken compass with question marks). The scene has the lighting and depth of a scientific photograph with playful cartoon-style emotion indicators (lightbulb moments, conflicted face expressions) integrated into the technical visualization."

## 6. "What This Means for All of Us"
**Prompt:** "Hyper-realistic photograph of a modern living room where everyday objects are subtly replaced with AI versions: a smart speaker with a cartoonish worried expression, a laptop screen showing conflicting health advice with true/false icons, a smartphone displaying contradictory financial information. Floating holographic infographic projections show ripple effects - trust meter declining, security warning symbols, and interconnected network diagrams showing how deception spreads. The lighting is warm and domestic but with cool blue tech elements. Visual metaphors include a house of cards beginning to wobble, and small 3D rendered question marks and exclamation points floating throughout the scene. Color palette balances homey warmth with tech blues and warning oranges."

## 7. "The Path Forward: Building Honest AI"
**Prompt:** "Hyper-realistic 3D scene of a construction site where transparent, honest AI robots (made of clear glass with visible ethical circuitry) are building a bridge toward a bright, hopeful future cityscape. The robots wear tiny hard hats and carry blueprint scrolls labeled 'AI Ethics' and 'Transparency Protocols.' Floating holographic infographic elements show: checkboxes being marked for safety measures, ascending progress bars for 'trust metrics,' and small 3D icons representing testing, regulation, and verification. The scene has golden hour photography lighting with hope-inspiring color tones. Playful elements include small graduation caps on some robots (representing learning) and tiny shield symbols protecting human figures in the background. The bridge itself is made of transparent materials with visible support structures labeled 'oversight' and 'accountability.'"

## Style Consistency Notes:
- **Lighting:** All images use cinematic, professional photography lighting with a mix of warm and cool tones
- **3D Elements:** Consistently playful yet sophisticated 3D rendered objects and characters
- **Infographic Integration:** Holographic-style floating UI elements, progress bars, icons, and data visualizations
- **Color Palette:** Blues for AI/tech, oranges/reds for warnings/deception, whites for clarity/truth, greens for positive outcomes
- **Perspective:** All shot from human eye level to create relatability
- **Texture Balance:** Hyper-realistic backgrounds and environments with cartoon-expressive AI characters
- **Educational Elements:** Visual metaphors and icons that immediately communicate complex concepts
""",
        model="o3",
        tools=[
            ImageGenerationTool(
                tool_config={
                    "type": "image_generation",
                    "quality": "high",
                    "model": "gpt-image-1",
                    "size": "1536x1024",
                }
            )
        ],
    )

    images = 7

    with trace("Image generation"):
        for image in range(images):
            try:
                print(f"Generating image {image + 1} of {images}...")
                result = await Runner.run(
                    agent, f"Please create image #{image + 1} of {images}"
                )
                print(result.final_output)
                for item in result.new_items:
                    if (
                        item.type == "tool_call_item"
                        and item.raw_item.type == "image_generation_call"
                        and (img_result := item.raw_item.result)
                    ):
                        os.makedirs("gen_images", exist_ok=True)
                        image_path = os.path.join("gen_images", f"image{image + 1}.png")
                        with open(image_path, "wb") as img_file:
                            img_file.write(base64.b64decode(img_result))
                        open_file(image_path)
            except Exception as e:
                print(f"Error generating image {image + 1}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
