import os

from agents import Agent, Runner, trace
from dotenv import load_dotenv
from openai import AsyncOpenAI

os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "http://localhost:6006"

from agents import set_default_openai_api, set_default_openai_client, set_trace_processors
from phoenix.otel import register

load_dotenv()

client = AsyncOpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=os.getenv("NRP_API_KEY"),
)
set_default_openai_client(client, use_for_tracing=False)
set_default_openai_api("chat_completions")

set_trace_processors([])  # Disable default trace processors
# configure the Phoenix tracer
tracer_provider = register(
    project_name="agents",  # Default is 'default'
    auto_instrument=True,  # Auto-instrument your app based on installed dependencies
)

agent = Agent(name="Assistant", instructions="You are a helpful assistant", model="gpt-oss")


async def main():
    with trace("Haiku Generator"):
        result = await Runner.run(
            agent, "Write a haiku about recursion in programming."
        )
        print(result.final_output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
