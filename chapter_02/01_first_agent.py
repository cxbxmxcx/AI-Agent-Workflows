from dotenv import load_dotenv
from agents import Agent, Runner

# Load environment variables from .env file
load_dotenv()

agent = Agent(name="Assistant", instructions="You are a helpful assistant")

result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(result.final_output)