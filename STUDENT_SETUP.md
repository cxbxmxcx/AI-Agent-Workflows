# Student Setup Guide — AI Agent Workflows (NRP Edition)

This course uses the same code as *"Build a Deep Research Agent from Scratch"* (see `README.md`), but instead of calling OpenAI's API directly, our agents talk to **NRP (National Research Platform / Nautilus)** — a free, self-hosted, OpenAI-compatible inference endpoint. That means **you do not need an OpenAI account or API key** for the vast majority of the course. Follow this guide before Chapter 2.

---

## 1. Software to install

| Tool | Version | Why you need it | Install |
|---|---|---|---|
| **Python** | 3.11 or 3.12 | Runs all the agent code | [python.org/downloads](https://www.python.org/downloads/) |
| **Git** | any recent | Clone the course repo | [git-scm.com](https://git-scm.com/downloads) |
| **Node.js** | **22.x LTS — NOT v24** | Powers `npx`-based MCP tool servers (filesystem, sequential-thinking, memory) used from Chapter 3 onward | see §3 below — install via a version manager, not directly |
| **uv** | latest | Provides `uvx`, used to run the `chroma-mcp` server in Chapter 6 | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **Graphviz** | latest | Renders agent/handoff diagrams in Chapter 4 (`05_visualizing_agent_flows.py`) | [graphviz.org/download](https://graphviz.org/download/) — on Windows, also add it to PATH during install |
| **VS Code** (recommended) | latest | IDE used throughout the course | [code.visualstudio.com](https://code.visualstudio.com/) |
| **Docker Desktop** (optional) | latest | Only needed if you want to containerize the Chapter 8 image-agent backend | [docker.com/get-started](https://www.docker.com/get-started/) |

> ⚠️ **Do not install Node.js v24.** Several MCP server packages (`@modelcontextprotocol/server-sequential-thinking`, etc.) fail on Node 24 with an `ERR_UNSUPPORTED_DIR_IMPORT` error because Node 24 enforces stricter ES-module resolution than these packages' dependencies support. **Node 22 LTS works correctly.**

---

## 2. Get the code

Clone the class repo (this is the instructor's fork, kept up to date with NRP-specific fixes — not the original book repo):

```bash
git clone https://github.com/vinodkahuja/AI-Agent-Workflows.git
cd AI-Agent-Workflows
```

### Staying up to date before each class

New chapters and fixes get pushed to this repo throughout the course. **Before each class, pull the latest changes:**

```bash
cd AI-Agent-Workflows
git pull
```

If `git pull` reports a conflict because you've edited a course file yourself, the simplest fix is to stash your local changes first, pull, then re-apply them:
```bash
git stash
git pull
git stash pop
```

## 3. Install Node.js 22 LTS (do this even if you already have another Node version)

Use a version manager so you can switch Node versions cleanly — don't install Node 22 directly on top of another version.

**Windows** — install [nvm4w (nvm for Windows)](https://github.com/coreybutler/nvm-windows):
```powershell
winget install CoreyButler.NVMforWindows
```
Then, in a **new** terminal:
```powershell
nvm install 22
nvm use 22
```
**Important (Windows only):** after running `nvm use 22` for the first time, **restart your computer** (not just the terminal or VS Code). Windows doesn't always propagate new environment variables to already-running or newly-launched applications until a full reboot. After rebooting, confirm:
```powershell
node -v      # should print v22.x.x
npx -v
```

**macOS/Linux** — install [nvm](https://github.com/nvm-sh/nvm):
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install 22
nvm use 22
```

## 4. Set up the Python environment

```bash
python -m venv venv
```
**Windows:** `venv\Scripts\activate`
**macOS/Linux:** `source venv/bin/activate`

```bash
pip install -r requirements.txt
```

## 5. Configure your `.env` file (NRP, not OpenAI)

Create a file named `.env` in the repo root with:
```
NRP_API_KEY=<the token your instructor provides>
NRP_BASE_URL=https://ellm.nrp-nautilus.io/v1
```
You do **not** need `OPENAI_API_KEY` for the course material (the one exception is noted in §7 below). Never commit `.env` to version control.

## 6. Pre-warm the MCP tool servers

The first time any script launches an `npx`-based MCP server, `npx` has to download and install the package — this can take longer than the code's default 5-second connection timeout and cause a `McpError: Timed out` on the very first run. Avoid this by pre-warming the two most common ones **once**, in a plain terminal (not through Python):

```bash
npx -y @modelcontextprotocol/server-sequential-thinking
```
Wait for it to print something like "running on stdio", then press `Ctrl+C`.

```bash
npx -y @modelcontextprotocol/server-filesystem .
```
Same — wait for confirmation output, then `Ctrl+C`.

If you later see `ERR_MODULE_NOT_FOUND` or similar errors from `npx` (usually only if you switched Node versions after already running these once), your npx cache may be stale/corrupted for the old Node version. Fix it by clearing the cache and re-running the commands above:

**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\npm-cache\_npx"
```
**macOS/Linux:**
```bash
rm -rf ~/.npm/_npx
```

## 7. Verify your setup

Run the simplest agent script to confirm everything is wired up correctly:
```bash
python chapter_02/01_first_agent.py
```
You should see trace/span output in the console followed by a 5-item research plan as the final answer, coming from NRP's `gpt-oss` model — no OpenAI account required.

Then try a Chapter 3 MCP example to confirm Node/npx are working:
```bash
python chapter_03/02_mcp_agent_stdio_server.py
```

---

## 8. Chapter-specific extras

| Chapter/topic | Extra requirement |
|---|---|
| Chapter 6 (`04_hybrid_memory_agent.py`, `04x_...`) | Needs `uvx` (comes with `uv`, already in requirements) to run the `chroma-mcp` server |
| Chapters 7/8/11 — Arize Phoenix tracing files (`09_arize_phoenix_tracing.py`, `07_phoenix_metadata.py`, `05_evaluation_feedback_tips.py`) | Need a local Phoenix collector running: `pip install arize-phoenix` (already in requirements) then run `phoenix serve` in a separate terminal before executing the script — it listens on `localhost:6006` |
| Chapter 9/10 — deep-research/capstone loops using Brave Search | Need a `BRAVE_API_KEY` in `.env` (get one free at [brave.com/search/api](https://brave.com/search/api/)) — without it, those specific demo scripts will fail at the MCP search-server step, unrelated to NRP |
| Chapter 7 (`07_image_generation_agent.py`, `08_image_vision_critic_agents.py`) and Chapter 8 (`01_embedded_agent_speech*.html`, `03_realtime_image_agent.html`, `02_app.py`) | **The originals are not supported on NRP** — they use OpenAI's hosted image-generation tool and Realtime/voice API, which have no NRP equivalent, and require a real `OPENAI_API_KEY` + OpenAI billing (each file has a comment at the top explaining this). **Free NRP-based alternatives exist instead** — use these: `chapter_07/07x_image_generation_agent_free.py` and `08x_image_vision_critic_agents_free.py` (Pollinations.ai for image generation, `gemma-small` for vision), `chapter_08/02x_app.py` (same Pollinations swap, as a FastAPI backend), and `chapter_08/01x_embedded_agent_speech.py` (a local voice pipeline: faster-whisper for speech-to-text, `gpt-oss` for the conversation, Piper for text-to-speech — run with `python 01x_embedded_agent_speech.py`, needs a working microphone). The `x` files need no OpenAI account at all. |
| Chapter 8 Docker setup | Only needed if containerizing `02_app.py` — see `chapter_08/README_DOCKER.md` |
| Chapter 4 (`05_visualizing_agent_flows.py`) | Needs Graphviz installed and on PATH, or `draw_graph(...).view()` will fail to render |

---

## 9. Common problems & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `McpError: Timed out while waiting for response... Waited 5.0 seconds` (first run of any MCP script) | Subprocess (`mcp run` or `npx`) cold-start takes longer than the SDK's default timeout | Just re-run the script — subsequent starts are much faster once cached. Pre-warming (§6) avoids this entirely for npx-based servers. |
| `ERR_UNSUPPORTED_DIR_IMPORT` from any `npx @modelcontextprotocol/...` command | You're on Node.js v24 | Switch to Node 22 LTS (§3) |
| `FileNotFoundError: [WinError 2] The system cannot find the file specified` when a script tries to launch `npx` | Windows hasn't picked up your new Node version's PATH yet | Reboot your machine (not just the terminal/VS Code) |
| `ERR_MODULE_NOT_FOUND` from npx right after switching Node versions | Stale npx cache from the old Node version | Clear the npx cache (§6) and re-run |
| A RAG/tool-calling agent loops and hits `MaxTurnsExceeded` | Occasional model-quality quirk of the fast `gpt-oss` model re-invoking a tool instead of finalizing | Not a setup problem — try re-running, or ask your instructor about switching that specific file to `model="qwen3"` |
| Script hangs with no output on a Phoenix-tracing file | No local Phoenix collector running | Run `phoenix serve` in another terminal first (§8) |
