# AI Agents In Action (2nd Edition)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![OpenAI](https://img.shields.io/badge/OpenAI-API-blue)](https://platform.openai.com/) [![MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://platform.openai.com/docs/guides/mcp)

This repository contains sample code for the book "Build a Deep Research Agent from Scratch." The code demonstrates how to create and run an AI agent using OpenAI's tools and APIs.

## Setup Instructions

### 1. Clone the Repository

To get started, clone this repository to your local machine:

```bash
git clone https://github.com/cxbxmxcx/AI-Agent-Workflows.git
cd AI-Agent-Workflows
```

### 2. Create Your Environment

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

### 3. Install Dependencies

#### Path A: Using VS Code Debugging

If you have VS Code, you can simply start debugging (press `F5`) to run the examples. The required dependencies will be installed automatically as part of the debugging process.

#### Path B: Manual Installation

Alternatively, you can manually install the dependencies using pip:

```bash
pip install -r requirements.txt
```

### 4. Configure the Environment

Create a `.env` file in the root directory to store your OpenAI API key. Use the provided `.env.example` file as a template:

#### Example `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

Replace `your_openai_api_key_here` with your actual OpenAI API key. You can obtain an API key from [OpenAI's API Keys page](https://platform.openai.com/account/api-keys).

#### Using a third-party OpenAI-compatible provider

If you are running the examples against a relay or a token plan from another
vendor, uncomment `OPENAI_BASE_URL` in your `.env` and point it at that
provider:

```
OPENAI_API_KEY=the_key_your_provider_issued
OPENAI_BASE_URL=https://your-provider.example.com/v1
AGENT_MODEL=the_model_your_provider_serves
```

Every example imports `agents_config.py`, which does three things once
`OPENAI_BASE_URL` is set:

- switches the Agents SDK from `/v1/responses` to `/v1/chat/completions`,
  because most third-party providers only implement the latter;
- disables OpenAI tracing, which would otherwise be rejected by
  api.openai.com;
- and, if `AGENT_MODEL` is set, runs every agent on that model.

`AGENT_MODEL` matters because most examples hardcode the OpenAI models the book
uses (`gpt-4o`, `gpt-5-mini`, `o3`, `gpt-4.1`), and the rest name no model at
all, so they fall back to the SDK's own default (`gpt-5.6-luna` in
openai-agents 0.22.2). Neither is something most providers serve. Set
`AGENT_MODEL` and every agent uses it; leave it unset and each example keeps the
model the book chose.

The first two are overridable with `OPENAI_AGENTS_CHAT_API=0` and
`OPENAI_AGENTS_DISABLE_TRACING=0`. With no `OPENAI_BASE_URL` set, nothing
changes and the examples behave exactly as described in the book.

Two things are not agents and so need their own model settings:

- the image examples (`chapter_07/07`, `chapter_07/08`, `chapter_08/02_app.py`
  and `bonus_projects/`) ask for `gpt-image-1`, which only OpenAI hosts. On a
  third-party endpoint `agents_config.image_tool()` swaps in a local tool that
  calls `POST /images/generations`, so set `IMAGE_MODEL` to an image model your
  provider serves (and `IMAGE_SIZE` if it rejects the size the book asks for);
- the embedding examples (`chapter_06/document_query_chromadb.py` and
  `chapter_06/document_visualizing_embeddings.py`) need `EMBEDDING_MODEL`, which
  does not fall back to `AGENT_MODEL` because a chat model cannot produce
  embeddings.

The vision call in `chapter_07/08_image_vision_critic_agents.py` talks to the
provider directly rather than through an agent, so it follows `VISION_MODEL`,
falling back to `AGENT_MODEL`. `chapter_02/02` sets `temperature=0.0`, which
reasoning-style models reject — set `AGENT_TEMPERATURE=1` if yours is one.

### 5. Run the Code

To execute the sample code, navigate to the desired chapter and run the Python file. For example:

```bash
python chapter_02/01_first_agent.py
```

This will run the agent and display the output in the terminal.

## Notes

- Ensure you are using the correct Python interpreter that matches your environment.
- The `.env` file should not be shared or committed to version control to keep your API key secure.
