# AI Agent Workflows — NRP Edition

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![NRP](https://img.shields.io/badge/inference-NRP-orange)](https://nrp.ai/) [![MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io/)

This is the class repository for this course. It's a modified version of the sample code from the book *"Build a Deep Research Agent from Scratch"*, adapted so every lesson runs against **NRP (National Research Platform / Nautilus)** — a free, self-hosted, OpenAI-compatible inference endpoint — instead of a paid OpenAI account. You do not need an OpenAI account or API key for the vast majority of this course.

> 📘 **For full setup details, chapter-by-chapter requirements, and troubleshooting, see [`STUDENT_SETUP.md`](STUDENT_SETUP.md).** The quick version is below.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/vinodkahuja/AI-Agent-Workflows.git
cd AI-Agent-Workflows
```

Before each class, pull the latest updates:

```bash
git pull
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

```bash
pip install -r requirements.txt
```

See `STUDENT_SETUP.md` for additional non-Python tools this course also needs (Node.js — a specific version matters, Graphviz, `uv`), since those aren't installed via pip.

### 4. Configure the Environment

Create a `.env` file in the root directory with your NRP credentials (**not** an OpenAI key — this repo has been repointed to a free NRP endpoint):

```
NRP_API_KEY=your_nrp_api_key_here
NRP_BASE_URL=https://ellm.nrp-nautilus.io/v1
```

Ask your instructor for the token if you don't have one. See `.env.example` for a copy-paste template. Never commit `.env` to version control.

### 5. Run the Code

To execute the sample code, navigate to the desired chapter and run the Python file. For example:

```bash
python chapter_02/01_first_agent.py
```

This will run the agent and display the output in the terminal.

## Notes

- Ensure you are using the correct Python interpreter that matches your environment.
- The `.env` file should not be shared or committed to version control to keep your credentials secure.
- Do not follow any OpenAI-specific setup instructions you find referenced elsewhere in this repo (e.g. in code comments or chapter files) — this repo has been adapted to use NRP; `STUDENT_SETUP.md` is the authoritative guide for this class.

## About this repo

This is a fork of the original book's companion repository, [cxbxmxcx/AI-Agent-Workflows](https://github.com/cxbxmxcx/AI-Agent-Workflows), modified for classroom use:

- All chapters repointed from OpenAI's API to NRP's free, self-hosted, OpenAI-compatible endpoint
- Local console-based tracing (no OpenAI account needed for tracing either)
- Several pre-existing bugs fixed (guardrail logic, missing exception handling, MCP connection timeouts)
- Free, open-source alternatives added for the two capabilities NRP doesn't support: image generation (chapters 7/8, via Pollinations.ai) and voice (chapter 8, via Whisper + Piper)

## License

MIT — see [LICENSE](LICENSE). Original code and book content © the original author; modifications for NRP/classroom use as noted above.
