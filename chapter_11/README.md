# Chapter 11 examples

The files in this folder illustrate the practices the chapter describes. Some are complete programs; others sketch a pattern and leave placeholders where your own components go, so they stop with an error if you run them as they are.

| File | Runs as is? | Notes |
|---|---|---|
| `01_core_persona_tips.py` | Yes | |
| `02_tool_action_tips.py` | Yes | |
| `03_reasoning_planning_tips.py` | Yes | Starts the sequential-thinking MCP server with `npx`. |
| `04_knowledge_memory_tips.py` | No, sketch | `load_vector_kb` stands for your own vector-store wrapper (FAISS, Weaviate, Chroma, ...). |
| `05_evaluation_feedback_tips.py` | Yes | Needs a running Phoenix server (see the README in the repository root). |
| `06_support_agent_tips.py` | No, sketch | `retrieval_agent = Agent(...)` stands for your retrieval agent; the comment lists the tools to add. |
| `07_rag_agent_tips.py` | Defines an agent only | `retrieve` returns a fixed passage; replace it with a query against your index. |
| `08_deep_research_agent_tips.py` | No, sketch | `web_search_tool`, `extract_tool` and `analyze_tool` stand for your tools, for example `WebSearchTool()`. |

To turn a sketch into a working program, replace each placeholder with a real component, as the comment next to it suggests.
