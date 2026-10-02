# Chapter 6 examples

Run `02_RAG_agent_vector.py` (or `02_RAG_agent_hybrid.py`) before the hybrid memory agents. It builds the Chroma vector store in `chapter_06/chroma_script_store` from `sample_documents/back_to_the_future.txt`, and `04_hybrid_memory_agent.py` and `04x_hybrid_memory_agent.py` query that store through the `chroma-mcp` server. The first run also downloads Chroma's default embedding model, about 80 MB.

The store is not part of the repository, because Chroma rewrites its files every time it opens them; it is built on your machine instead.

`03_create_memories_mcp.py` saves memories that `03_mcp_memory_agent.py`, `03_mcp_memory_manage_agent.py` and the `04` agents read back. They share them because they all launch the same pinned version of `@modelcontextprotocol/server-memory`, which keeps its data next to its installed package.
