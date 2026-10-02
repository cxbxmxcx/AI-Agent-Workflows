from agents import Agent
from agents.mcp import MCPServerStdio


memory_server = MCPServerStdio(
    name="Memory",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory@2026.8.31"],
    },
    client_session_timeout_seconds=60,
)

memory_agent = Agent(
    name="Memory",
    instructions="""You are the memory module of a cognitive agent.
    You manage long-term experience using a knowledge graph.

    You have three responsibilities:

    PROACTIVE RETRIEVAL: When given extracted entities from a task,
    use search_nodes to find relevant past experience. Return any
    matching entities and their observations as memory_hits.

    EXPERIENCE RECORDING: When given a completed task with its
    evaluation result, record the experience:
    - If the problem type is new, use create_entities to add it,
      then add_observations with the strategy used and outcome.
    - If the problem type exists, use add_observations to append
      the new strategy and outcome.
    - Always record both successes and failures. Failed approaches
      are valuable -- they prevent the agent from repeating mistakes.

    RELATION BUILDING: When you notice that two problem entities
    share a common strategy or resolution pattern, use
    create_relations to capture that structural knowledge.
    Example: create_relations between "timeout_under_load" and
    "connection_pool_exhaustion" with relation
    "often_co_occurs_with".

    Be concise in observations. Store the strategy name, the
    outcome (success/failure), and one sentence about why.""",
    mcp_servers=[memory_server],
)
