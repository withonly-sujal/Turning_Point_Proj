"""
EventFlow_AI/mcp_client.py
---------------------------
Manages the persistent async connection to the Solace MCP Server.
Implements the "Smart Router" architecture, exposing generalized
tools to the LLM and orchestrating the complex relational Solace
REST calls underneath.
"""

import os
import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import config

# ── MCP Server Parameters ─────────────────────────────────────────────────
def _get_server_params() -> StdioServerParameters:
    env = {
        **os.environ,
        "SOLACE_API_TOKEN": config.SOLACE_API_TOKEN,
        "SOLACE_API_BASE_URL": config.SOLACE_API_BASE_URL,
    }
    return StdioServerParameters(
        command="uvx",
        args=["-q", "--from", "solace-event-portal-designer-mcp", "solace-ep-designer-mcp"],
        env=env,
    )

# ── Context Manager ────────────────────────────────────────────────────────
@asynccontextmanager
async def managed_session():
    """Async context manager that yields an initialized MCP ClientSession."""
    async with stdio_client(_get_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


# ── Generalized Tool Schemas for LLM ───────────────────────────────────────
GENERALIZED_TOOLS = [
    {
        "name": "search_solace_entity",
        "description": "Lists all entities of a given type, or finds a specific entity if 'name' is provided.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["domain", "application", "event"],
                    "description": "The type of entity you want to list or search for."
                },
                "name": {
                    "type": "string",
                    "description": "Optional. The exact name of the entity to search for. If omitted, lists all entities of the specified type."
                }
            },
            "required": ["entity_type"]
        }
    },
    {
        "name": "get_entity_relationships",
        "description": "Fetches the related objects (like applications inside a domain, or events produced/consumed by an application).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The ID of the parent entity."
                },
                "relationship_type": {
                    "type": "string",
                    "enum": ["applications", "produced_events", "consumed_events"],
                    "description": "The type of relationship you want to explore."
                }
            },
            "required": ["entity_id", "relationship_type"]
        }
    },
    {
        "name": "create_solace_entity",
        "description": "Creates a new Solace Domain, Application, or Event, along with its initial version (0.1.0).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["domain", "application", "event"],
                    "description": "The type of entity you want to create."
                },
                "name": {
                    "type": "string",
                    "description": "The exact name of the new entity."
                },
                "domain_name": {
                    "type": "string",
                    "description": "The exact name of the domain where this entity should reside. Required for applications and events."
                }
            },
            "required": ["entity_type", "name"]
        }
    },
    {
        "name": "create_solace_entity_version",
        "description": "Creates a new version for an existing Application or Event.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["application", "event"],
                    "description": "The type of entity you are versioning."
                },
                "entity_id": {
                    "type": "string",
                    "description": "The ID of the parent application or event."
                },
                "version": {
                    "type": "string",
                    "description": "The new version string (e.g. '1.0.0')."
                }
            },
            "required": ["entity_type", "entity_id", "version"]
        }
    }
]

# ── Smart Router Logic (Python Backend) ────────────────────────────────────

async def _call_mcp(session: ClientSession, tool_name: str, args: dict) -> list | dict:
    """Helper to execute an MCP tool and parse its JSON output."""
    try:
        result = await session.call_tool(tool_name, args)
        parts = [c.text for c in result.content if c.type == "text"]
        text = "".join(parts)
        if not text.strip():
            return []
        
        parsed = json.loads(text)
        return parsed.get("data", parsed)
    except Exception as e:
        print(f"[DEBUG] MCP Call failed: {tool_name} with {args} - {e}")
        return []


async def _search_entity(session: ClientSession, entity_type: str, name: str = None) -> dict:
    """Executes the search_solace_entity logic."""
    args = {}
    if name:
        args["name"] = name
    
    if entity_type == "domain":
        # Solace getApplicationDomains allows filtering by name
        data = await _call_mcp(session, "getApplicationDomains", args)
        return {"result": data}
        
    elif entity_type == "application":
        # Solace getApplications allows filtering by name
        data = await _call_mcp(session, "getApplications", args)
        return {"result": data}
        
    elif entity_type == "event":
        # Solace getEvents allows filtering by name
        data = await _call_mcp(session, "getEvents", args)
        return {"result": data}
        
    return {"error": f"Unsupported entity_type: {entity_type}"}


async def _get_relationships(session: ClientSession, entity_id: str, relationship_type: str) -> dict:
    """Executes the get_entity_relationships logic by chaining Solace tools."""
    
    if relationship_type == "applications":
        # Find all apps within a domain
        data = await _call_mcp(session, "getApplications", {"applicationDomainId": entity_id})
        # Keep it clean for the LLM
        clean_apps = [{"id": a["id"], "name": a["name"]} for a in data if "id" in a and "name" in a]
        return {"result": clean_apps}
        
    elif relationship_type in ["produced_events", "consumed_events"]:
        # 1. We have the App ID. We need its latest Version ID to see its events.
        app_versions = await _call_mcp(session, "getApplicationVersions", {"applicationIds": [entity_id]})
        
        if not app_versions:
            return {"result": [], "message": "No application versions found for this app ID."}
            
        # Grab the first (latest) version
        latest_version = app_versions[0]
        
        # 2. Extract the IDs of the events it produces/consumes
        if relationship_type == "produced_events":
            event_version_ids = latest_version.get("declaredProducedEventVersionIds", [])
        else:
            event_version_ids = latest_version.get("declaredConsumedEventVersionIds", [])
            
        if not event_version_ids:
            return {"result": []}
            
        # 3. Solace requires us to fetch the actual event names using getEventVersions
        resolved_events = []
        for ev_id in event_version_ids:
            # We fetch the specific event version to get its parent Event ID, but we can also just
            # return the event version data. Let's fetch the event version.
            ev_data = await _call_mcp(session, "getEventVersions", {"ids": [ev_id]})
            if ev_data:
                ev = ev_data[0]
                resolved_events.append({
                    "version_id": ev.get("id"),
                    "event_id": ev.get("eventId"),
                    "version": ev.get("version"),
                    "description": ev.get("description", "")
                })
                
        # 4. To get the pretty event NAME, we could query getEvent using the event_id, but the version often suffices.
        # For a truly complete answer, let's look up the parent Event to get the name.
        for ev in resolved_events:
            parent_event = await _call_mcp(session, "getEvents", {"ids": [ev["event_id"]]})
            if parent_event:
                ev["name"] = parent_event[0].get("name", "Unknown")

        return {"result": resolved_events}

    return {"error": f"Unsupported relationship_type: {relationship_type}"}


async def _create_entity(session: ClientSession, entity_type: str, name: str, domain_name: str = None) -> dict:
    """Executes the create_solace_entity logic."""
    # 1. Check if it exists
    existing = await _search_entity(session, entity_type, name)
    if existing.get("result") and len(existing["result"]) > 0:
        return {"error": f"{entity_type.capitalize()} '{name}' already exists. Use create_solace_entity_version to add a new version."}

    # 2. Create Domain (no parent required)
    if entity_type == "domain":
        data = await _call_mcp(session, "createApplicationDomain", {"name": name})
        return {"result": data}

    # 3. For app and event, we need a domain
    if not domain_name:
        return {"error": "domain_name is required for applications and events."}

    # Resolve domain ID
    domain_search = await _search_entity(session, "domain", domain_name)
    if not domain_search.get("result") or len(domain_search["result"]) == 0:
        return {"error": f"Domain '{domain_name}' not found."}
    
    domain_id = domain_search["result"][0]["id"]

    # 4. Create entity and its initial version
    if entity_type == "application":
        data = await _call_mcp(session, "createApplication", {
            "name": name,
            "applicationDomainId": domain_id,
            "applicationType": "standard",
            "brokerType": "solace"
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        app_id = entity.get("id")
        if not app_id:
            return {"error": f"Created app but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createApplicationVersion", {
            "applicationId": app_id,
            "version": "0.1.0"
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    elif entity_type == "event":
        data = await _call_mcp(session, "createEvent", {
            "name": name,
            "applicationDomainId": domain_id
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        evt_id = entity.get("id")
        if not evt_id:
            return {"error": f"Created event but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createEventVersion", {
            "eventId": evt_id,
            "version": "0.1.0"
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    return {"error": f"Unsupported entity_type: {entity_type}"}


async def _create_version(session: ClientSession, entity_type: str, entity_id: str, version: str) -> dict:
    """Executes the create_solace_entity_version logic."""
    if entity_type == "application":
        ver_data = await _call_mcp(session, "createApplicationVersion", {
            "applicationId": entity_id,
            "version": version
        })
        return {"result": ver_data}
    elif entity_type == "event":
        ver_data = await _call_mcp(session, "createEventVersion", {
            "eventId": entity_id,
            "version": version
        })
        return {"result": ver_data}
    
    return {"error": f"Unsupported entity_type: {entity_type}"}


# ── The Interceptor ────────────────────────────────────────────────────────
async def execute_smart_tool(session: ClientSession, tool_name: str, args: dict) -> str:
    """Routes the LLM's generic tool call to the Python mapping engine."""
    
    try:
        if tool_name == "search_solace_entity":
            result = await _search_entity(session, args.get("entity_type"), args.get("name"))
        elif tool_name == "get_entity_relationships":
            result = await _get_relationships(session, args.get("entity_id"), args.get("relationship_type"))
        elif tool_name == "create_solace_entity":
            result = await _create_entity(session, args.get("entity_type"), args.get("name"), args.get("domain_name"))
        elif tool_name == "create_solace_entity_version":
            result = await _create_version(session, args.get("entity_type"), args.get("entity_id"), args.get("version"))
        else:
            return json.dumps({"error": f"Unknown smart tool: {tool_name}"})
            
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Execution failed: {str(exc)}"})
