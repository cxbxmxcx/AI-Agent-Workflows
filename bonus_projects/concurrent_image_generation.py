import asyncio
import base64
import os
import subprocess
import sys

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


async def save_and_open(
    image_bytes: bytes, path: str, open_after_save: bool = True
) -> None:
    # Ensure folder exists and do filesystem + OS operations in a worker thread
    def _write():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(image_bytes)

    await asyncio.to_thread(_write)
    if open_after_save:
        await asyncio.to_thread(open_file, path)


async def generate_one(
    idx: int, total: int, agent: Agent, sem: asyncio.Semaphore
) -> None:
    """
    Generate a single image (idx is 1-based), throttled by `sem`.
    Does network call under the semaphore; saves/opens file outside of it.
    """
    prompt = f"Please create image #{idx} of {total}"
    try:
        print(f"Generating image {idx} of {total}...")
        # Limit only the network/tool call concurrency:
        async with sem:
            result = await Runner.run(agent, prompt)

        # Log model output (may interleave across tasks—normal for concurrency)
        if hasattr(result, "final_output"):
            print(result.final_output)

        # Find the first image tool result and save it
        for item in getattr(result, "new_items", []) or []:
            if (
                getattr(item, "type", None) == "tool_call_item"
                and getattr(getattr(item, "raw_item", None), "type", None)
                == "image_generation_call"
            ):
                img_result = getattr(getattr(item, "raw_item", None), "result", None)
                if img_result:
                    image_bytes = base64.b64decode(img_result)
                    image_path = os.path.join("gen_images", f"image{idx}.png")
                    # Do file I/O and OS open without holding the semaphore
                    await save_and_open(image_bytes, image_path, open_after_save=True)
                    break
    except Exception as e:
        print(f"Error generating image {idx}: {e}")


async def main():
    agent = Agent(
        name="Image generator",
        instructions="""
        Here are 9 image prompts for the article sections, designed with a consistent hyper-realistic photography and 3D infographic style:

## 1. Hero Image - "The AI Music Revolution"
**Prompt:** Hyper-realistic photo of a vintage microphone on a recording studio desk, but the microphone is partially dissolving into floating blue digital particles and holographic musical notes. Above it, a 3D holographic projection shows a pie chart splitting "Human" vs "AI" music creation, with iconic symbols like guitars, headphones, and waveforms floating around. The background shows blurred studio equipment with subtle circuit board patterns overlaid. Warm studio lighting contrasts with cool blue digital glows. Musical staff lines project as light beams through the air.

## 2. The Band That Never Existed  
**Prompt:** Hyper-realistic photo of four empty vintage microphone stands on a concert stage, each casting human-shaped shadows despite no one being there. 3D holographic projections above each stand show pixelated "band member" avatars glitching in and out of existence. Floating infographic elements display "1.2M streams" and "#1 Viral Charts" with upward trending arrows. Spotify's green logo hovers as a 3D object with streaming data visualizations flowing from it like ribbons.

## 3. The Red Flags Detection
**Prompt:** Hyper-realistic close-up of a smartphone screen showing a band's Instagram profile, but red warning triangles and question marks float as 3D holograms above the device. The profile photos have subtle digital artifacts and glitch effects. Magnifying glass icons project as light beams scanning the images, revealing hidden grid patterns and pixel distortions. Reddit's orange logo appears as a floating 3D detective badge with tiny digital breadcrumbs trailing behind it.

## 4. Autotune Evolution Timeline
**Prompt:** Hyper-realistic photo of a recording studio mixing board with vintage and modern equipment side by side. Above it, a 3D timeline projection shows the evolution from raw vinyl records morphing into autotuned waveforms, then into AI neural network patterns. T-Pain's iconic hat and Cher's silhouette appear as holographic icons. The timeline ends with a robotic head wearing headphones, singing digital musical notes that transform into human-shaped soundwaves.

## 5. AI Music Toolbox
**Prompt:** Hyper-realistic photo of an open vintage toolbox, but instead of tools, it contains floating 3D icons: a brain-shaped CPU, musical note-shaped memory chips, and a microphone that's half-analog, half-digital. Above the toolbox, holographic interface panels show code snippets transforming into musical notation. Platform logos (Suno, Udio) appear as floating app icons. Cables and wires morph into flowing musical staff lines connecting different AI components.

## 6. The $9 Billion Economic Impact
**Prompt:** Hyper-realistic photo of a balance scale, with gold coins ($9B in royalties) on one side and floating holographic AI music files on the other. Human musicians appear as small 3D figurines on the money side, while robot musicians perform on the digital side. Dollar signs and streaming platform icons float as light projections around the scale. The background shows a concert venue split between empty seats (representing displaced artists) and packed digital avatars.

## 7. The Authenticity Arms Race
**Prompt:** Hyper-realistic photo of two vintage microphones facing each other like dueling pistols. One is covered in organic elements (wood grain, analog knobs) projecting "100% Human Made" certificates as holograms. The other is sleek and digital, projecting AI neural network patterns and binary code. Between them, a 3D holographic "VS" symbol pulses with energy. Musical notes from each side clash and merge in the air, some glowing warm (human) and others cool blue (AI).

## 8. Transparency and Labeling Problem
**Prompt:** Hyper-realistic photo of a music streaming app interface on a tablet, but floating above it are 3D question mark holograms and "AI Generated?" warning labels. Some song titles have glowing transparency badges while others are unmarked. A magnifying glass icon projects a beam of light revealing hidden metadata. Legal scales and gavel icons float as holographic elements, while Spotify and Deezer logos appear as opposing team badges in a game-like interface.

## 9. The Future Harmony
**Prompt:** Hyper-realistic photo of a concert stage where a human musician and a holographic AI performer share the spotlight, creating music together. Their combined sound waves visualize as intertwining DNA helixes made of musical notes. The audience shows both physical humans and digital avatars enjoying the performance. Above the stage, a 3D projection shows a collaborative workflow diagram with hands and circuit patterns working together. Musical instruments morph seamlessly between acoustic and digital forms.

Each image maintains the consistent style of photorealistic base elements enhanced with floating 3D infographic projections, using familiar icons to make complex AI concepts immediately understandable and visually engaging for Medium readers.
       """,
        model="gpt-5-mini",
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

    total_images = 9
    # Limit how many generations run at once (override via IMG_CONCURRENCY env var)
    concurrency = int(os.environ.get("IMG_CONCURRENCY", "5"))
    concurrency = max(1, min(concurrency, total_images))
    sem = asyncio.Semaphore(concurrency)

    with trace("Image generation"):
        tasks = [
            asyncio.create_task(generate_one(i + 1, total_images, agent, sem))
            for i in range(total_images)
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
