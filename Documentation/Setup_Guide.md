# EventFlow AI — Teammate Setup Guide

Welcome to the **EventFlow AI** project! This guide will walk you through setting up the environment on your local machine so you can pick up development right where the team left off.

---

## 🛠️ 1. Prerequisites

Before cloning the repository, ensure your machine has the following tools installed:

1. **Python 3.13+**: The core language runtime.
2. **[uv](https://docs.astral.sh/uv/)**: An ultra-fast Python package installer and resolver.
   - Install via curl (macOS/Linux): `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Install via PowerShell (Windows): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. **[Ollama](https://ollama.com/)**: Required for running the local Large Language Model. Download and install it from their official website.

---

## 📥 2. Clone the Repository

Clone the project from GitHub and navigate into the root directory:

```bash
git clone https://github.com/withonly-sujal/Turning_Point_Proj.git
cd Turning_Point_Proj
```

---

## 🤖 3. Setup the Local AI Model

EventFlow AI relies on a completely local LLM for maximum privacy. By default, the `config.py` specifies the `qwen3:8b` model. 

Start your Ollama daemon (if it isn't running in the background already), and pull the required model:

```bash
ollama pull qwen3:8b
```
*(Note: This might take a few minutes depending on your internet connection, as the model is a few gigabytes in size).*

---

## 🔐 4. Environment Variables

The Smart Router needs to authenticate with the Solace Event Portal Cloud via the official Solace MCP server. 

1. Create a file named `.env` in the root of the project (`Turning_Point_Proj/.env`).
2. Add your Solace API token and base URL to the file:

```env
SOLACE_API_TOKEN=your_personal_solace_api_token_here
SOLACE_API_BASE_URL=https://api.solace.cloud
```
*(Do NOT use quotes around your API token unless it contains special characters like `#`).*

---

## 🚀 5. Install Dependencies & Run

Because we use `uv`, you don't need to manually create virtual environments. `uv` will automatically read the `pyproject.toml`, set up the virtual environment, install the Solace MCP Server (via `uvx`), and execute the app.

Run the following command from the root of the project to start the CLI interface:

```bash
uv run python -m EventFlow_AI.app
```

**That's it!** You should now see the Persona Selection screen:

```text
Select Persona:                          
  1. Admin     (Full read + write access)
  2. End User  (Read-only access)        
                                 
Enter 1 or 2: 
```

Enjoy building the future of Event-Driven AI! 🚀
