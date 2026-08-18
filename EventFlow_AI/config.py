"""
EventFlow_AI/config.py
-----------------------
Centralized environment & encoding configuration.
Loaded once at startup by all other modules.
"""

import os
import sys
from dotenv import load_dotenv

# ── Windows terminal UTF-8 fix ─────────────────────────────────────────────
def _fix_encoding():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")

_fix_encoding()

# ── Load .env from project root ────────────────────────────────────────────
# Resolves to e:\Turning_Point_Proj\.env regardless of where the script runs.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))

# ── Exported configuration values ─────────────────────────────────────────
SOLACE_API_TOKEN: str = os.getenv("SOLACE_API_TOKEN", "")
SOLACE_API_BASE_URL: str = os.getenv("SOLACE_API_BASE_URL", "https://api.solace.cloud")

# Ollama / local model settings
OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
OLLAMA_MODEL: str = "qwen3:8b"

# Safety limits
MAX_TOOL_ROUNDS: int = 8       # Max consecutive tool calls per user query

def validate():
    """Raise early if critical credentials are missing."""
    if not SOLACE_API_TOKEN or SOLACE_API_TOKEN == "your_token_here":
        raise EnvironmentError(
            "[ERROR] SOLACE_API_TOKEN is not set.\n"
            "   -> Open .env and add your token from https://console.solace.cloud/"
        )
