"""
EventFlow_AI/agent.py
----------------------
Two-Phase Tool Orchestration Loop.

Phase 0 -- Tool Discovery
  Send the user's query + a compact (~5KB) list of all 35 tool names +
  one-sentence descriptions. Ask Qwen which tools it wants to use.

Phase 1+ -- Targeted Execution
  Inject the *full* (but pruned) schemas of only the tools Qwen requested.
  Execute those tools against the Solace MCP Server.
  Feed the results back to Qwen for final summarization.
  Repeat up to MAX_TOOL_ROUNDS times.
"""

import json

from mcp import ClientSession

from . import config
from . import mcp_client as mcp
from . import llm_client as llm


async def run(user_query: str, session: ClientSession, persona: str) -> str:
    """
    Run the full two-phase orchestration loop for a single user query.

    Parameters
    ----------
    user_query : The user's natural language input.
    session    : An active MCP ClientSession (from mcp_client.managed_session).
    persona    : "admin" or "end_user".

    Returns
    -------
    str : The final synthesized natural language response from Qwen.
    """

    # ── Fetch tool catalogue from MCP Server ──────────────────────────────
    all_tools = await mcp.fetch_all_tools(session)
    tool_map = {t["name"]: t for t in all_tools}

    # ── PHASE 0: Tool Discovery ────────────────────────────────────────────
    # Send compact tool list so the LLM doesn't get overwhelmed at this stage.
    compact_tools = mcp.to_compact_tools(all_tools)
    compact_tools_text = json.dumps(compact_tools, indent=2)

    discovery_system = (
        llm.SYSTEM_PROMPTS[persona]
        + "\n\n"
        + "## Available Tools (compact listing)\n"
        + compact_tools_text
        + "\n\nBased on the user's question, identify which tool names you need "
          "to call. Reply with ONLY a JSON array of tool names, e.g.: "
          '[\"getApplicationDomains\", \"getEvents\"]'
    )

    discovery_messages = [
        {"role": "system", "content": discovery_system},
        {"role": "user", "content": user_query},
    ]

    discovery_response = await llm.chat(discovery_messages, tool_choice="none")
    raw_text = discovery_response.choices[0].message.content or "[]"

    # Parse the JSON array of tool names Qwen selected
    selected_tool_names: list[str] = []
    try:
        # Extract a JSON array from wherever Qwen put it in its response
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start != -1 and end > start:
            selected_tool_names = json.loads(raw_text[start:end])
    except (json.JSONDecodeError, ValueError):
        # If Qwen didn't return parseable JSON, skip Phase 1 and answer directly
        selected_tool_names = []

    # ── Persona Guard: filter out disallowed tools ─────────────────────────
    blocked = [t for t in selected_tool_names if not llm.is_tool_allowed(t, persona)]
    selected_tool_names = [t for t in selected_tool_names if llm.is_tool_allowed(t, persona)]

    if blocked and not selected_tool_names:
        return (
            "This action requires Administrator privileges. "
            "Please contact your admin to perform write operations."
        )

    # ── PHASE 1+: Targeted Execution Loop ─────────────────────────────────
    # Build the full conversation with pruned schemas of selected tools only.
    selected_tools_full = [
        mcp.prune_tool(tool_map[name])
        for name in selected_tool_names
        if name in tool_map
    ]

    openai_tools = [llm.mcp_to_openai_tool(t) for t in selected_tools_full]

    messages = [
        {"role": "system", "content": llm.SYSTEM_PROMPTS[persona]},
        {"role": "user", "content": user_query},
    ]

    for round_num in range(config.MAX_TOOL_ROUNDS):
        response = await llm.chat(messages, tools=openai_tools if openai_tools else None)
        choice = response.choices[0]
        message = choice.message

        # No more tool calls → Qwen has the final answer
        if not message.tool_calls:
            return message.content or "(no response)"

        # Append the assistant's tool-calling message to history
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        })

        # Execute each requested tool and append results
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # Persona guard — double-check at execution time
            if not llm.is_tool_allowed(tool_name, persona):
                tool_result = json.dumps({
                    "error": "Blocked by persona policy: insufficient privileges."
                })
            else:
                try:
                    tool_result = await mcp.execute_tool(session, tool_name, args)
                except Exception as exc:
                    tool_result = json.dumps({"error": str(exc)})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    # If we exhausted all rounds without a final answer, ask one more time
    response = await llm.chat(messages, tool_choice="none")
    return response.choices[0].message.content or "(no response after max rounds)"
