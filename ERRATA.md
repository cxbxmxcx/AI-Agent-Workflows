# Errata: sample code

This file lists the corrections made to the sample code after the first English printing of *AI Agents in Action, Second Edition*, following the technical review of the code for the Spanish edition (Anaya Multimedia, 1 October 2026). The IDs are the review's; IDs that start with X are problems found while making these fixes. The code as it stood at the first printing is tagged `en-print-baseline`.

The **Listing** column says whether a change alters code the book prints. "Matches print" means the file was wrong and now agrees with the printed listing. Every change that alters printed code is collected in [Changes to printed listings](#changes-to-printed-listings).

To check a copy of the repository for every problem below, run `python tools/check_repo.py`.

## Blockers

| ID | Problem | Change | Listing |
|---|---|---|---|
| B-01 | Seven examples launched `@anthropic/brave-search-mcp`, an npm package that does not exist. | They launch Brave's official server, `@brave/brave-search-mcp-server@2.1.4`, which reads the same `BRAVE_API_KEY`. | yes |
| B-02 | `chapter_09/07_task_loop.py` launched `@anthropic/filesystem-mcp`, which does not exist. | It launches `@modelcontextprotocol/server-filesystem`. The script also creates its `workspace` folder next to itself (the server exits when the folder is missing), ships the three documents its tasks read, and passes their full paths. | no (not printed) |
| B-03 | `travel_forward` subtracted the years. | It adds them, in `chapter_05/04_time_travel_agent.py` and in the solution file. | matches print (5.11) |
| B-04 | mcp 2.0 removed `FastMCP`, which ten examples import. | `requirements.txt` pins `mcp[cli]==1.30.0`, the current 1.x release. | no |
| B-05 | Fourteen empty files in `chapter_06`. | Deleted. `chapter_08/__init__.py` is empty on purpose and stays. | no |

## Major defects

| ID | Problem | Change | Listing |
|---|---|---|---|
| M-01 | The guardrail message in `chapter_04/07_input_output_guardrails.py` lacked its `f` prefix. | Added. | yes |
| M-02 | A duplicated `return` in `chapter_11/02_tool_action_tips.py`. | Removed. | matches print (11.2) |
| M-03 | Two prompt sentences ran together in `chapter_11/06_support_agent_tips.py`. | Added the missing space. | yes |
| M-04 | A module-level `Runner.run_streamed()` call in `chapter_11/08_deep_research_agent_tips.py` failed with "no running event loop". | Removed; `main()` already streams the run. | yes (11.7) |
| M-05 | `requirements.txt` pinned nothing and missed five imported packages. | Every package is pinned to a version tested on Python 3.11, 3.13 and 3.14. `scikit-learn`, `openai`, `openinference-instrumentation`, `requests` and `typing_extensions` are declared; `google-adk` and `litellm`, which no example imports, are gone. `chapter_08/requirements.txt` and the listing 8.5 services use the same versions. | no |
| M-06 | Pressing F5 did not install the requirements, as appendix A says it does. | Both launch configurations run the **Install requirements** task first. The task no longer upgrades every package on each run, and the configurations use the `debugpy` debugger type. | no |
| M-07 | The README named another book, an MIT license and two Python versions. | It names *AI Agents in Action, Second Edition*, the Apache 2.0 license and Python 3.11+. | no |
| M-08 | Two sentences of the problem in `chapter_05/02_ReAct_agent.py` ran together. | Added the missing space. | yes |
| M-09 | The listing 8.5 Docker Compose material lived only in another, unlicensed repository. | Copied into `chapter_08/microservices/`, under this repository's Apache 2.0 license. | no |
| M-10 | `.env.example` did not declare `BRAVE_API_KEY`, and two files passed an empty key when it was missing. | `.env.example` declares it. All seven files read it with `os.environ["BRAVE_API_KEY"]`, so a missing key stops the run with an error that names it. The README explains how `.env` is loaded under F5 and from a terminal. | no |

## Minor defects

| ID | Problem | Change | Listing |
|---|---|---|---|
| m-01 | Typos in three file names. | Renamed; see the table in the README. | matches print (4.7, 4.11) |
| m-02 | Typos in identifiers and prompts: `research_soruce`, `ouput` (eight files), `atleast` (three files), `braching`, `CritqueImage`. | Corrected everywhere. | yes |
| m-03 | "witness the end of the end" in four files, and a garbled sentence in the San Francisco trip exercise. | "the end of the event"; "However, the Exploratorium is closed on the first day and there are no startups to tour." | yes (5.1, 5.11) |
| m-04 | Header comments naming files that do not exist. | Each header names its own file. `chapter_03/01_complete_agent.py`, `chapter_03/01_complete_mcp_server.py` and `chapter_08/02_app.py` keep `# agent.py`, `# server.py` and `# app.py`, the names the chapter text gives them. | yes |
| m-05 | `with_name("06_mcp_time_travel_tracker")` lacked `.py`. | Added. | yes |
| m-06 | Thirteen ChatGPT citation markers (`:contentReference[oaicite:…]`) in the two chapter 8 speech pages, three of them visible on the page. | Removed. | yes (8.1) |
| m-07 | Material the book never refers to. | Two presentations, generated images and a scratch graph are no longer tracked; `demo_project/` and `chapter_12/` moved to `extras/`. | no |

## Prerequisites, version drift and questions

| ID | Problem | Change | Listing |
|---|---|---|---|
| P-01 | MCP examples timed out on their first run. The cause is not `npx` on Windows (the MCP SDK already resolves `npx` to `npx.cmd`) but the 5-second default start-up timeout of `MCPServerStdio` while `npx` or `uvx` downloads the server. | Every `npx` launch passes `client_session_timeout_seconds=60`, every `uvx` launch 300. `python tools/check_repo.py --servers` downloads every server ahead of time. | yes |
| P-02 | The Graphviz programs are a separate install. | README, Prerequisites. | no |
| P-03 | The Phoenix server needs Docker. | README: Docker, or `phoenix serve` on Python 3.12 and later. | no |
| V | MCP servers were launched unpinned or with `@latest`. | Every server is pinned: `server-filesystem`, `server-memory` and `server-sequential-thinking` at 2026.8.31, Brave at 2.1.4, `chroma-mcp` at 0.2.6 with `chromadb` 1.5.9. Memories that `server-memory@latest` saved before this change stay with that version and are not visible to the pinned one. | yes |
| V | openai-agents changed its default model between releases (`gpt-4o` in 0.2, `gpt-5.6-luna` in 0.23). | `.env.example` sets `OPENAI_DEFAULT_MODEL=gpt-5.1` for the agents that do not name a model. | no |
| V | The sequential-thinking server's parameters are camelCase (`thoughtNumber`, `totalThoughts`, `nextThoughtNeeded`). They always were; only the tool description used snake_case before version 2025.11.25. | No code change; the chapter 5 text should print camelCase. | text only |
| Q-03 | The chapter 9 files used `gpt-4o`; the listings print `gpt-5.1`. | The files use `gpt-5.1`. | matches print |
| Q-04 | Are there solutions for the exercises? | No official set; the README says so. | no |

## Found while fixing the report

| ID | Problem | Change | Listing |
|---|---|---|---|
| X-01 | The chapter 6 hybrid memory agents passed `--data-dir` to `chroma-mcp` without `--client-type persistent`, so the server used an empty in-memory store instead of `chapter_06/chroma_script_store`. | They pass `--client-type persistent` and now see the `bttf_script` collection. | yes |
| X-02 | `bonus_projects/mcp_examples/09_mcp_agent_sse_server.py` looked for the chapter 3 server in its own folder. | It points at `chapter_03/01_claude_mcp_server.py`. | no |
| X-03 | `chapter_10/.claude/settings.local.json`, a local Claude Code settings file, was tracked. | No longer tracked. | no |
| X-04 | Chroma rewrites `chapter_06/chroma_script_store` every time it opens it, so any chapter 6 run left tracked files modified. | The store is no longer tracked. `02_RAG_agent_vector.py` builds it on first run; `chapter_06/README.md` gives the order. | no |

## Changes to printed listings

These are the lines that now differ from the first printing. Listing numbers are given where the review named them; otherwise the file is named.

**Every MCP server launched with `npx` or `uvx`** (chapters 3, 4, 5, 6, 9, 10 and 11). The package gains its version, and the call gains a start-up timeout as its last argument:

```python
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2026.8.31"],
        },
        client_session_timeout_seconds=60,
```

The same applies to `@modelcontextprotocol/server-filesystem@2026.8.31` and `@modelcontextprotocol/server-memory@2026.8.31`, which replaces `@latest` in chapter 6. In chapter 9, `"@anthropic/brave-search-mcp"` becomes `"@brave/brave-search-mcp-server@2.1.4"`. In listings 10.4 and 10.7, the printed `command=`/`args=` form also has to become `params={...}` (that was already wrong in the first printing).

**Chapter 4**
- `07_input_output_guardrails.py`: `output_info=f"research plan length: {len(output.research_plan)}"`.
- `03`, `04`, `05`, `06`, `09`, `09x`, `10` and `11`: "ouput" becomes "output" in the instructions; `09`, `09x` and `10`: "atleast" becomes "at least".

**Chapter 5**
- 5.1 and 5.11: "witness the end of the event".
- `02_ReAct_agent.py`: `"I am in the year 2050. "`, with a trailing space.
- `01_planning_san_fran_trip_updated.md`: "However, the Exploratorium is closed on the first day and there are no startups to tour."

**Chapter 6** (`04_hybrid_memory_agent.py`, `04x_hybrid_memory_agent.py`):

```python
            "command": "uvx",
            "args": [
                "--with", "chromadb==1.5.9",
                "chroma-mcp@0.2.6",
                "--client-type", "persistent",
                "--data-dir", "chapter_06/chroma_script_store",
            ],
        },
        client_session_timeout_seconds=300,
```

**Chapters 2 and 7**: `research_source` (chapter 2, `08_agent_with_tools_tracing.py`) and `CritiqueImage` (chapter 7, `08_image_vision_critic_agents.py`).

**Chapter 3**: the header comments read `# 06_time_travel_agent_mcp_stdio.py` and `# 06_time_travel_agent_mcp_sse.py`, and the SSE example uses `with_name("06_mcp_time_travel_tracker.py")`.

**Chapter 8**: listing 8.1 without the `:contentReference[oaicite:…]` markers; `06_idempotent_key_example.py` names itself in its header.

**Chapter 11**
- `06_support_agent_tips.py`: `" Pass on complex queries to retrieval_agent."`, with a leading space.
- 11.7: no module-level `Runner.run_streamed()` block.
