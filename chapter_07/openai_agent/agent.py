from google.adk.agents import LlmAgent  # alias: Agent
from google.adk.models.lite_llm import LiteLlm  # <- OpenAI bridge

# ❶ Choose the model (any name LiteLLM recognises)
model = LiteLlm(model="openai/gpt-4o")  # GPT-4o via OpenAI API

# ❷ Create the agent – no tools needed for a chat-only demo
root_agent = LlmAgent(
    model=model,
    name="openai_demo_agent",
    instruction="You are a concise assistant who always answers in Markdown.",
)
