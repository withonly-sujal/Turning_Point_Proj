"""
EventFlow_AI/llm_client.py
---------------------------
Local LLM interface and Persona Engine.

Connects to your locally-running Ollama instance using the OpenAI-compatible
API. No data ever leaves your machine.

Personas
--------
ADMIN      -- Full Read + Write access to all 35 Solace tools.
END_USER   -- Read-only access. Mutating calls are blocked with an escalation
              warning before they are even sent to the LLM.
"""

from openai import AsyncOpenAI

from . import config

# ── Ollama client (100% local) ─────────────────────────────────────────────
client = AsyncOpenAI(
    base_url=config.OLLAMA_BASE_URL,
    api_key="ollama",               # Ollama ignores this value, but SDK requires it
)

# ── Read-only tool names (safe for End User) ───────────────────────────────
READ_ONLY_PREFIXES = ("get", "list")

# ── System Prompts ─────────────────────────────────────────────────────────
_BASE_PROMPT = """You are EventFlow AI, an expert assistant for the Solace Event Portal.
You help users understand and manage their Event-Driven Architecture.
When answering, always be concise and structured. Use bullet points or tables when listing data.
If a tool returns an empty list, say so clearly and suggest next steps.
Never fabricate data — only report what the tools return."""

SYSTEM_PROMPTS = {
    "admin": _BASE_PROMPT + """

You are operating in ADMIN mode.
You have full read AND write access to all Solace Event Portal Designer tools.
You may create, update, and delete application domains, applications, events, and schemas.""",

    "end_user": _BASE_PROMPT + """

You are operating in END USER (Read-Only) mode.
You may ONLY use tools that start with 'get' or 'list'.
If the user asks you to create, update, or delete anything, respond with:
  "This action requires Administrator privileges. Please contact your admin."
Do not attempt to call any mutating tool under any circumstances.""",
}


# ── Persona safety guard ───────────────────────────────────────────────────
def is_tool_allowed(tool_name: str, persona: str) -> bool:
    """Return True if the persona is allowed to call this tool."""
    if persona == "admin":
        return True
    # End user: only read-only prefixes
    return tool_name.lower().startswith(READ_ONLY_PREFIXES)


# ── LLM call helpers ───────────────────────────────────────────────────────
async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
) -> object:
    """
    Send a conversation to the local Qwen model and return the raw response.

    Parameters
    ----------
    messages   : Full conversation history in OpenAI chat format.
    tools      : Optional list of OpenAI-format tool schemas.
    tool_choice: "auto" lets the model decide; "none" disables tool calling.
    """
    kwargs = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    response = await client.chat.completions.create(**kwargs)
    return response


def mcp_to_openai_tool(tool: dict) -> dict:
    """
    Convert an MCP tool definition into the OpenAI function-calling format
    expected by the chat completions API.
    """
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
        },
    }
