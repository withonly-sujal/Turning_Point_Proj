"""
EventFlow_AI/app.py
--------------------
Interactive CLI terminal interface for EventFlow AI.

Usage
-----
    uv run python EventFlow_AI/app.py

Slash Commands
--------------
    /help     Show available commands
    /tools    List all 35 available Solace tools
    /clear    Clear conversation (restart context)
    /persona  Switch between Admin and End User mode
    /exit     Exit the application
"""

import asyncio
import sys

# config must be imported first to fix Windows UTF-8 encoding
from . import config
from . import mcp_client as mcp
from . import agent

# ── Banner ──────────────────────────────────────────────────────────────────
BANNER = """
==========================================================================
  EventFlow AI  --  Solace Event Portal Assistant
  Model  : {model}
  Persona: {{persona}}
==========================================================================
  Type your question, or use a slash command:
    /help  /tools  /clear  /persona  /exit
--------------------------------------------------------------------------
""".format(model=config.OLLAMA_MODEL)

HELP_TEXT = """
Slash Commands:
  /help     Show this help message
  /tools    List all 35 available Solace MCP tools
  /clear    Clear the screen
  /persona  Switch persona (Admin / End User)
  /exit     Exit EventFlow AI
"""


# ── Persona selection ────────────────────────────────────────────────────────
def select_persona() -> str:
    print("\nSelect Persona:")
    print("  1. Admin     (Full read + write access)")
    print("  2. End User  (Read-only access)")
    while True:
        choice = input("\nEnter 1 or 2: ").strip()
        if choice == "1":
            return "admin"
        if choice == "2":
            return "end_user"
        print("Please enter 1 or 2.")


def persona_label(persona: str) -> str:
    return "Admin" if persona == "admin" else "End User (Read-Only)"


# ── Main application loop ────────────────────────────────────────────────────
async def main():
    try:
        config.validate()
    except EnvironmentError as e:
        print(e)
        sys.exit(1)

    persona = select_persona()
    print(BANNER.format(persona=persona_label(persona)))

    print("[...] Connecting to Solace MCP Server, please wait...\n")

    try:
        async with mcp.managed_session() as session:
            all_tools = mcp.GENERALIZED_TOOLS

            print(f"[OK] Connected — Smart Router Active.\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\nGoodbye!")
                    break

                if not user_input:
                    continue

                # ── Slash commands ───────────────────────────────────────
                if user_input.lower() == "/exit":
                    print("Goodbye!")
                    break

                elif user_input.lower() == "/help":
                    print(HELP_TEXT)

                elif user_input.lower() == "/clear":
                    print("\033[2J\033[H", end="")   # ANSI clear screen
                    print(BANNER.format(persona=persona_label(persona)))

                elif user_input.lower() == "/persona":
                    persona = select_persona()
                    print(f"\n[OK] Switched to: {persona_label(persona)}\n")

                elif user_input.lower() == "/tools":
                    print(f"\nAvailable Tools ({len(all_tools)} total):")
                    for i, t in enumerate(all_tools, 1):
                        desc = t.get("description", "")
                        short = desc.split(".")[0][:60] if desc else ""
                        print(f"  {i:>2}. {t['name']:<45} {short}")
                    print()

                else:
                    # ── Standard query: run orchestrator ─────────────────
                    print("\n[...] Thinking...\n")
                    try:
                        answer = await agent.run(user_input, session, persona)
                        print(f"EventFlow AI:\n{answer}\n")
                        print("-" * 72)
                    except Exception as exc:
                        print(f"[ERROR] {exc}\n")

    except Exception as exc:
        print(f"\n[ERROR] Failed to connect to Solace MCP Server: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
