# docker run -it --rm -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

import os

from agents import Agent, Runner, set_default_openai_client, set_default_openai_api, trace
from dotenv import load_dotenv
from openai import AsyncOpenAI

os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "http://localhost:6006"

from agents import set_trace_processors
from openinference.instrumentation import (
    using_metadata,
    using_session,
)

# pip install openinference-instrumentation arize-phoenix-otel
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

model = "gpt-oss"
agent = Agent(name="Assistant", instructions="Always answer in a Haiku", model=model)


async def main():
    agent_input = dict(question="why is the sky blue?")
    metadata = dict(run_id="abc123", env="dev", customer_tier="pro", model=model)
    with (
        using_session("sess-42"),
        using_metadata(metadata),
    ):
        with trace("Haiku Generator"):
            result = await Runner.run(agent, str(agent_input))
            print(result.final_output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
