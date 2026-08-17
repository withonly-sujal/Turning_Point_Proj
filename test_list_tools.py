"""
test_list_tools.py
------------------
Starts the Solace Event Portal Designer MCP server as a subprocess,
sends it an MCP JSON-RPC `tools/list` request over stdin/stdout,
and prints all registered tools.

Usage:
    cd e:\\Turning_Point_Proj
    python test_list_tools.py

Requirements:
    - SOLACE_API_TOKEN must be set in .env (or as an env var)
    - `uvx` must be available on PATH (comes with `uv`)
"""

import subprocess
import json
import os
import sys

# Force UTF-8 output on Windows terminal to avoid cp1252 encode errors
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

# Load credentials from root .env
load_dotenv()

token = os.getenv("SOLACE_API_TOKEN")
base_url = os.getenv("SOLACE_API_BASE_URL", "https://api.solace.cloud")

if not token or token == "your_token_here":
    print("[ERROR] SOLACE_API_TOKEN is not set in your .env file.")
    print("   -> Open .env and replace 'your_token_here' with your real token.")
    print("   -> Get a token at: https://console.solace.cloud/ > API Tokens")
    sys.exit(1)

print(f"[OK] Token loaded  : {'*' * (len(token) - 6)}{token[-6:]}")
print(f"[OK] Base URL      : {base_url}")
print()
print("[...] Starting MCP server and sending tools/list request...")

# MCP JSON-RPC messages — initialize then list tools
initialize_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    }
}) + "\n"

initialized_notification = json.dumps({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}) + "\n"

list_tools_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}) + "\n"

env = {**os.environ, "SOLACE_API_TOKEN": token, "SOLACE_API_BASE_URL": base_url}

try:
    proc = subprocess.Popen(
        ["uvx", "--from", "solace-event-portal-designer-mcp", "solace-ep-designer-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",      # Force UTF-8 -- Windows defaults to cp1252 which breaks MCP output
        errors="replace",      # Replace undecodable bytes instead of crashing
        env=env,
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "Solace_MCP_Server", "solace-event-portal-designer-mcp")
    )

    # Send all messages
    stdin_payload = initialize_msg + initialized_notification + list_tools_msg
    try:
        stdout, stderr = proc.communicate(input=stdin_payload, timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("[ERROR] Timeout: server did not respond within 60 seconds.")
        sys.exit(1)

    if stdout is None:
        print("[ERROR] No output received from the server. Check stderr below.")
        if stderr:
            print(stderr)
        sys.exit(1)

    # Parse responses (one JSON object per line)
    tools = []
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if msg.get("id") == 2 and "result" in msg:
                tools = msg["result"].get("tools", [])
        except json.JSONDecodeError:
            pass  # Skip non-JSON lines

    if stderr:
        print("-- Server stderr (logs) ------------------------------------------")
        print(stderr[:2000])
        print("------------------------------------------------------------------")
        print()

    if not tools:
        print("[WARN] No tools received. Check stderr above for errors.")
    else:
        print(f"[SUCCESS] MCP server registered {len(tools)} tools:\n")
        print(f"{'#':<4} {'Tool Name':<55} Description")
        print("-" * 120)
        for i, tool in enumerate(tools, 1):
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            # Trim description to first sentence for readability
            short_desc = desc.split(".")[0].strip()[:60] if desc else ""
            print(f"{i:<4} {name:<55} {short_desc}")
        print("-" * 120)
        print(f"\nTotal: {len(tools)} tools")

except FileNotFoundError:
    print("[ERROR] `uvx` not found. Make sure `uv` is installed and on your PATH.")
    print("   -> Install uv: https://docs.astral.sh/uv/getting-started/installation/")
    sys.exit(1)
