# AI Agents In Action (2nd Edition)

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/) [![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE) [![OpenAI](https://img.shields.io/badge/OpenAI-API-blue)](https://platform.openai.com/) [![MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io/)

This repository contains the sample code for the book *AI Agents in Action, Second Edition* (Manning). The code demonstrates how to build and run AI agents with the OpenAI Agents SDK and the Model Context Protocol (MCP).

## Setup Instructions

### 1. Clone the Repository

To get started, clone this repository to your local machine:

```bash
git clone https://github.com/cxbxmxcx/AI-Agent-Workflows.git
cd AI-Agent-Workflows
```

### 2. Install the Prerequisites

- **Python 3.11 or later.** The pinned requirements are tested on Python 3.11, 3.13 and 3.14.
- **Node.js 20 or later.** The MCP servers the examples start with `npx` run on Node.js (see appendix B).
- **Graphviz.** Chapter 4 draws agent graphs with `draw_graph(...).view()`, which needs the Graphviz programs on your `PATH`, not only the Python package. Install them from [graphviz.org](https://graphviz.org/download/).
- **Docker, or the Phoenix server (chapter 7).** The tracing examples send their traces to Phoenix. Either start the container named at the top of each chapter 7 tracing file, or skip Docker and start the same server with `phoenix serve`. On Python 3.12 and later, `requirements.txt` installs the `phoenix` command; on Python 3.11, use Docker.

### 3. Create Your Environment

This project requires **Python 3.11+**. Create and activate a Python virtual environment:

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

If you prefer to use an external Python environment, ensure you set the Python path in VS Code:

1. Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS).
2. Search for "Python: Select Interpreter."
3. Choose the Python interpreter for your environment.

### 4. Install Dependencies

#### Path A: Using VS Code Debugging

If you have VS Code, you can simply start debugging (press `F5`) to run the examples. The **Install requirements** task runs before every launch and installs whatever `requirements.txt` lists that is missing, so the first launch takes a few minutes and later ones start right away.

#### Path B: Manual Installation

Alternatively, you can manually install the dependencies using pip:

```bash
pip install -r requirements.txt
```

`requirements.txt` pins the exact versions the examples are tested with. Keep them as they are: `mcp` in particular must stay below 2.0, because version 2 removed the `FastMCP` class the chapter 3 and 4 servers are built on.

### 5. Configure the Environment

Copy `.env.example` to a file named `.env` in the root directory and fill in your keys:

```
OPENAI_API_KEY=your_openai_api_key
BRAVE_API_KEY=your_brave_api_key
OPENAI_DEFAULT_MODEL=gpt-5.1
```

- `OPENAI_API_KEY` is needed by every example. You can obtain an API key from [OpenAI's API Keys page](https://platform.openai.com/account/api-keys).
- `BRAVE_API_KEY` is needed by the chapter 9 and 10 research agents, which search the web through the Brave Search MCP server. You can obtain one from the [Brave Search API page](https://brave.com/search/api/).
- `OPENAI_DEFAULT_MODEL` sets the model for every agent that does not name one. Without it, the Agents SDK falls back to its own default, which changes from release to release.

VS Code loads `.env` for you when you start an example with `F5`. Most examples do not load it themselves, so when you run them from a terminal, either set the variables in your shell or let python-dotenv load the file:

```bash
python -m dotenv run -- python chapter_04/01_single_agent_multiple_mcp.py
```

### 6. Run the Code

Run the examples from the repository root, because several of them open files by paths relative to it. For example:

```bash
python chapter_02/01_first_agent.py
```

This will run the agent and display the output in the terminal.

## MCP Servers on the First Run

Many examples start MCP servers with `npx` (Node.js) or `uvx` (Python). The first time an example starts a server, `npx` or `uvx` downloads it, which can take from a few seconds to a minute or more; the examples wait long enough for that. To download every server ahead of time, run:

```bash
python tools/check_repo.py --servers
```

## Repository Layout

- `chapter_02` to `chapter_11`: the code for each chapter of the book.
- `bonus_projects/`: extra examples that go beyond the book.
- `extras/`: material that is not part of the book: `demo_project/`, a demo sequence built from the chapter 2 to 6 examples, and `chapter_12/`, an Agent2Agent (A2A) client sketch.
- `tools/check_repo.py`: checks the repository for known problems and downloads the MCP servers ahead of time.

## Renamed Files

Three files were renamed after the first printing to fix typos in their names:

| First printing | Now |
|---|---|
| `chapter_04/06_agent_to_agent_monitroing_handoffs.py` | `chapter_04/06_agent_to_agent_monitoring_handoffs.py` |
| `chapter_04/10_agent__guardrails_retry.py` | `chapter_04/10_agent_guardrails_retry.py` |
| `chapter_05/04_time_travel_agent_soluriont.py` | `chapter_05/04_time_travel_agent_solution.py` |

## Exercises

The exercises at the end of each chapter are open-ended, and there is no official set of solutions. `chapter_05/04_time_travel_agent_solution.py` is a worked solution for one of the chapter 5 exercises.

## Notes

- Ensure you are using the correct Python interpreter that matches your environment.
- The `.env` file should not be shared or committed to version control to keep your API key secure.
