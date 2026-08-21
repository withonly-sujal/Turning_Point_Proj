"""
EventFlow_AI/agent.py
----------------------
Orchestration Loop.

Exposes only the highly-abstracted Smart Router tools to the LLM.
Intercepts tool calls and routes them to the Python backend to resolve
the complex Solace graph automatically.
"""

import json
from mcp import ClientSession

from . import config
from . import mcp_client as mcp
from . import llm_client as llm


async def run(user_query: str, session: ClientSession, persona: str) -> str:
    """
    Run the orchestration loop for a single user query using the Smart Router tools.
    """

    # ── Inject the Generalized Tools ──────────────────────────────────────────
    openai_tools = [llm.mcp_to_openai_tool(t) for t in mcp.GENERALIZED_TOOLS]

    messages = [
        {"role": "system", "content": llm.SYSTEM_PROMPTS[persona]},
        {"role": "user", "content": user_query},
    ]

    for round_num in range(config.MAX_TOOL_ROUNDS):
        response = await llm.chat(messages, tools=openai_tools)
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

        # Execute each requested Smart Tool and append results
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # Execute via Smart Router
            tool_result = await mcp.execute_smart_tool(session, tool_name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    # If we exhausted all rounds without a final answer, ask one more time
    response = await llm.chat(messages, tool_choice="none")
    return response.choices[0].message.content or "(no response after max rounds)"
