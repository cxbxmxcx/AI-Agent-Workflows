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
Here are image prompts for each slide, designed to be playful yet educational with a consistent hyper-realistic + 3D rendering + infographic style:

## Slide 1: Title Slide
**Prompt:** "Hyper-realistic 3D rendered scene of a sleek humanoid AI agent silhouette made of translucent blue glass, standing confidently with arms crossed, surrounded by floating holographic interface elements and data streams. The agent glows with internal purple-pink gradient lighting. Behind it, a dynamic background shows interconnected nodes and pathways suggesting a neural network. Floating 3D text 'AI AGENTS IN ACTION' hovers above in bold, modern typography with metallic finish. The scene has dramatic lighting with blue and purple color palette, shot from a low angle to convey power and sophistication."

## Slide 2: Why Agents Matter Now
**Prompt:** "Split-screen hyper-realistic 3D scene: Left side shows a person peacefully sleeping in bed at night, while above them float translucent 3D holographic representations of tasks being completed - a miniature airplane booking interface, a rotating calendar with appointments being scheduled, and contract documents with negotiation arrows. Right side shows a sleek AI agent figure orchestrating these tasks with conductor-like gestures. Infographic elements include: a timeline arrow showing '2024-2030', dollar signs floating around '$15B+', and a progress bar showing '40%' with small briefcase icons. The scene has warm bedroom lighting contrasted with cool blue holographic elements."

## Slide 3: Agents vs Assistants vs Chatbots
**Prompt:** "Hyper-realistic 3D rendered scene showing three distinct AI entities on pedestals: Left - a simple chatbot as a basic geometric shape with single speech bubble, Center - an assistant as a more sophisticated humanoid form with multiple floating interface panels, Right - a full agent as a dynamic figure with multiple robotic arms manipulating various tools (wrench, calendar, documents). Above each, floating infographic labels show their capabilities with connecting lines and icons. The scene has clean, modern lighting with each entity glowing in different colors (red, yellow, blue) to show progression of capability."

## Slide 4: What Makes an Agent—True Agency
**Prompt:** "Hyper-realistic 3D rendered AI agent figure in the center of a dynamic circular flow diagram. The agent has a transparent body showing internal gears and neural pathways. Four large 3D arrows circle around it labeled 'SENSE', 'PLAN', 'ACT', 'LEARN' with corresponding icons (eye, brain, hand, lightbulb). The agent's eyes glow as sensors, its head shows processing activity, its hands reach toward various tools, and learning pathways light up throughout its body. The background shows a subtle grid pattern suggesting digital environment, with floating objectives and feedback loops visualized as glowing connections."

## Slide 5: Agents in the Wild
**Prompt:** "Hyper-realistic 3D rendered scene showing four distinct environments floating as separate platforms: Top left - a customer service desk with holographic chatbot resolving tickets (70% counter visible), Top right - a coding workspace with AI hands typing and code flowing, Bottom left - a sales funnel with AI nurturing leads along a 3D pathway, Bottom right - a research library with AI scanning and fact-checking documents. Each platform glows with different colors and shows infographic statistics. A central AI conductor figure oversees all platforms with connecting light beams, emphasizing orchestration across industries."

## Slide 6: The Four Pillars Framework
**Prompt:** "Hyper-realistic 3D rendered ancient Greek temple with four massive crystalline pillars, each glowing with different colors and containing floating icons: Pillar 1 (blue) - tools and gears, Pillar 2 (green) - brain and lightbulb, Pillar 3 (purple) - books and databases, Pillar 4 (orange) - charts and feedback loops. Between the pillars, a sophisticated AI agent figure stands on a platform, with energy flowing between all pillars and converging on the agent. Above, floating 3D text reads 'BUILD ONCE, IMPROVE FOREVER' in golden letters. The scene has dramatic temple lighting with particle effects showing the flow of capabilities."

## Slide 7: Pillar 1 – Actions & Tools
**Prompt:** "Hyper-realistic 3D rendered workshop scene with an AI agent's hands manipulating various floating tools: API connectors shaped like USB cables, browser windows being controlled by holographic hands, OS terminal windows opening in mid-air, and hardware components responding to gesture commands. The agent stands behind a workbench made of light, with tool schemas floating as translucent blueprints. A large quote bubble shows 'Agents DO things; assistants SAY things' with emphasis on 'DO' glowing brightly. The scene has workshop lighting with blue technical glows and sparks flying from active tools."

## Slide 8: Pillar 2 – Reasoning & Planning
**Prompt:** "Hyper-realistic 3D rendered scene showing an AI agent's transparent head with visible brain activity, surrounded by floating thought bubbles connected by glowing pathways. The thought process flows in a circular pattern: 'THINK' → 'ACT' → 'OBSERVE' → repeat, with each stage showing different 3D representations (gears for thinking, hands for acting, eyes for observing). Above the agent, a hierarchical tree structure shows goal decomposition with smaller sub-goals branching out. The scene has a cerebral blue-white lighting with neural pathway effects and mathematical equations floating in the background."

## Slide 9: Pillar 3 – Memory & Knowledge
**Prompt:** "Hyper-realistic 3D rendered digital library scene with an AI agent at the center, surrounded by floating databases visualized as crystalline structures (vector DB as interconnected nodes, SQL as structured blocks, graph DB as network webs). The agent has one hand reaching into a 'long-term storage' vault and another accessing a 'short-term scratchpad' that looks like a holographic notepad. RAG architecture flows are shown as glowing data streams connecting external knowledge sources to the agent's processing core. The scene has a warm library ambiance with cool digital highlights and floating books transforming into data."

## Slide 10: Pillar 4 – Evaluation & Feedback
**Prompt:** "Hyper-realistic 3D rendered scene showing an AI agent standing before a large holographic mirror that reflects not just its image, but also performance metrics, charts, and feedback loops. To one side, a human figure provides input through a glowing feedback interface, while on the other side, automated evaluation systems show A/B testing results as floating comparison panels. The agent holds a clipboard showing self-critique notes. Above, red-team warning indicators and logging data streams flow like ribbons. The scene has analytical lighting with green (positive) and red (negative) feedback indicators glowing throughout."

## Slide 11: The Complete Agent Loop
**Prompt:** "Hyper-realistic 3D rendered scene showing a sophisticated AI agent at the center of a dynamic orbital system. Four planets representing the pillars orbit around the agent, connected by flowing energy streams. The agent processes multi-modal inputs (text, voice, images) shown as different colored light beams entering from various angles. Tool orchestration is visualized as the agent conducting an orchestra of floating tools and interfaces. Error handling appears as defensive shields that activate when problems occur. The scene has a cosmic feel with the agent as the central star, surrounded by the orbital mechanics of its capabilities."

## Slide 12: Integration Challenges & Solutions
**Prompt:** "Hyper-realistic 3D rendered scene split into 'problem' and 'solution' halves. Left side shows chaos: fragmented tools scattered and broken, tangled cables representing context switching, and security barriers blocking access. Right side shows harmony: tools connected through universal adapters, smooth conveyor belts showing seamless workflows, and protective sandboxes containing safe operations. In the center, an AI agent acts as a bridge, with one hand touching the chaotic side and the other organizing the solution side. The transition from chaos to order is shown through color gradient from red to blue."

## Slide 13: MCP: Universal Tool Integration
**Prompt:** "Hyper-realistic 3D rendered scene showing a giant USB-C connector floating in space, but instead of metal, it's made of flowing data streams and light. Around it, various tools and applications (represented as different shaped objects) are connecting through identical glowing ports. An AI agent conductor stands nearby, orchestrating the connections with gesture commands. Above, floating protocol endpoints ('/prompt', '/tools', '/resources') appear as glowing waypoints. The scene emphasizes universal connectivity with streams of data flowing seamlessly between all connected tools. Blue and white lighting with electrical connection effects."

## Slide 14: Advanced Planning Strategies
**Prompt:** "Hyper-realistic 3D rendered scene showing multiple AI agents collaborating on a complex planning board that floats in mid-air. The board displays a hierarchical tree structure with main goals at the top branching into sub-goals. Some agents work on different levels of the hierarchy, while others show dynamic replanning by moving puzzle pieces around. A behavior tree appears as a living, growing structure with branches that light up as decisions are made. The scene has a war room feel with strategic lighting and holographic battle plans, but with a collaborative, constructive atmosphere."

## Slide 15: Challenges and Limitations
**Prompt:** "Hyper-realistic 3D rendered scene showing an AI agent navigating through an obstacle course of challenges. The agent encounters: a reliability maze with some paths leading to dead ends, a cost meter showing rising expenses, a trust balance scale that's slightly tipping, and an alignment compass pointing in multiple directions. Above each obstacle, mitigation strategies appear as helpful tools: human oversight shown as a guiding light, gradual automation as stepping stones, and robust testing as safety nets. The scene has dramatic lighting with the agent showing determination while acknowledging the challenges."

## Slide 16: The Business Case for Agents
**Prompt:** "Hyper-realistic 3D rendered corporate boardroom scene with an AI agent presenting to executive figures (shown as silhouettes). The agent points to floating 3D charts and graphs showing ROI growth, 24/7 availability clocks, quality consistency meters, and scalability arrows pointing upward. A timeline pathway shows the investment journey from pilot to scale to ROI over 12 months. Dollar signs and percentage increases float around the presentation. The scene has professional lighting with blue corporate colors and golden success indicators highlighting the business benefits."

## Slide 17: Future Roadmap
**Prompt:** "Hyper-realistic 3D rendered scene showing a winding pathway extending into the distance, with milestone markers at different points. Near milestones (12 months) show improved reasoning gears, better tool integration symbols, and human-AI collaboration handshakes. Distant milestones (2026+) show multiple AI agents working together in organizational charts, autonomous business processes as self-running machinery, and AI-native workflows as futuristic cityscapes. The path glows with progress indicators and the scene has a forward-looking, optimistic lighting with sunrise colors suggesting bright future possibilities."

## Slide 18: Getting Started Today
**Prompt:** "Hyper-realistic 3D rendered scene showing a user sitting at a desk with four floating action items around them: 1) A magnifying glass examining repetitive workflow elements, 2) Various agent platform logos (Claude, GPT-4, AutoGPT) as interactive holographic interfaces, 3) A construction toolkit building a simple proof-of-concept, 4) A measurement dashboard showing impact metrics. The scene has an inviting, accessible feel with warm lighting and the user appearing confident and ready to begin. Tutorial arrows and helpful hints float around as guidance elements."

## Slide 19: Building Your First Agent
**Prompt:** "Hyper-realistic 3D rendered scene showing a step-by-step construction process with an AI agent being built layer by layer. Each step is represented as a floating platform: 1) Goal definition with target symbols, 2) Tool selection with various instruments, 3) Planning loop design with circular flowcharts, 4) Memory implementation with data storage, 5) Evaluation systems with feedback meters, 6) Testing with multiple scenario bubbles. A master builder figure (representing the developer) orchestrates the process with architectural blueprints floating nearby. The scene has workshop lighting with construction progress indicators and a sense of accomplishment."

Each prompt maintains the consistent hyper-realistic + 3D rendering + infographic style while being playful and educational, using visual metaphors that make complex concepts accessible and memorable.
""",
        model="gpt-4o",
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

    images = 19

    with trace("Image generation"):
        for image in range(images):
            print(f"Generating image {image + 1} of {images}...")
            result = await Runner.run(
                agent, f"Please create slide image #{image + 1} of {images}"
            )
            print(result.final_output)
            for item in result.new_items:
                if (
                    item.type == "tool_call_item"
                    and item.raw_item.type == "image_generation_call"
                    and (img_result := item.raw_item.result)
                ):
                    os.makedirs("gen_images", exist_ok=True)
                    image_path = os.path.join(
                        "gen_images", f"slide2_image{image + 1}.png"
                    )
                    with open(image_path, "wb") as img_file:
                        img_file.write(base64.b64decode(img_result))
                    open_file(image_path)


if __name__ == "__main__":
    asyncio.run(main())
