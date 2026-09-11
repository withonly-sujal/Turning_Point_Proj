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
    
    # Use the local modified package
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mcp_path = os.path.join(base_dir, "Solace_MCP_Server", "solace-event-portal-designer-mcp")
    
    return StdioServerParameters(
        command="uvx",
        args=["-q", "--from", mcp_path, "solace-ep-designer-mcp"],
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
                    "enum": ["domain", "application", "event", "event_api", "event_api_product", "schema", "enum"],
                    "description": "The type of entity you want to list or search for."
                },
                "name": {
                    "type": "string",
                    "description": "Optional. The exact name of the entity to search for. If omitted, lists all entities of the specified type."
                },
                "domain_name": {
                    "type": "string",
                    "description": "Optional. The exact name of the domain to filter the search results by."
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
                    "enum": ["domain", "application", "event", "event_api", "event_api_product", "schema", "enum"],
                    "description": "The type of entity you want to create."
                },
                "name": {
                    "type": "string",
                    "description": "The exact name of the new entity."
                },
                "domain_name": {
                    "type": "string",
                    "description": "The exact name of the domain where this entity should reside. Required for applications and events."
                },
                "enum_values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required when creating an enum. The list of string values for the enumeration."
                }
            },
            "required": ["entity_type", "name"]
        }
    },
    {
        "name": "create_solace_entity_version",
        "description": "Creates a new version for an existing Application, Event, Event API, or Event API Product.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["application", "event", "event_api", "event_api_product", "schema", "enum"],
                    "description": "The type of entity you are versioning."
                },
                "entity_id": {
                    "type": "string",
                    "description": "The ID of the parent entity."
                },
                "version": {
                    "type": "string",
                    "description": "The new version string (e.g. '1.0.0')."
                },
                "enum_values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required when versioning an enum. The list of string values for the enumeration."
                }
            },
            "required": ["entity_type", "entity_id", "version"]
        }
    },
    {
        "name": "delete_solace_entity",
        "description": "Deletes a specific Solace Domain, Application, Event, Event API, or Event API Product.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["domain", "application", "event", "event_api", "event_api_product", "schema", "enum"],
                    "description": "The type of entity you are deleting."
                },
                "entity_id": {
                    "type": "string",
                    "description": "The ID of the entity to delete."
                }
            },
            "required": ["entity_type", "entity_id"]
        }
    },
    {
        "name": "delete_solace_entity_version",
        "description": "Deletes a specific version of a Solace Application, Event, Event API, or Event API Product.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["application", "event", "event_api", "event_api_product", "schema", "enum"],
                    "description": "The type of entity version you are deleting."
                },
                "version_id": {
                    "type": "string",
                    "description": "The unique ID of the version to delete."
                }
            },
            "required": ["entity_type", "version_id"]
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
        
        try:
            parsed = json.loads(text)
            return parsed.get("data", parsed)
        except json.JSONDecodeError:
            # If the server returned an error string instead of JSON
            return {"error": text}
    except Exception as e:
        print(f"[DEBUG] MCP Call failed: {tool_name} with {args} - {e}")
        return []


async def _search_entity(session: ClientSession, entity_type: str, name: str = None, domain_name: str = None) -> dict:
    """Executes the search_solace_entity logic."""
    args = {}
    if name:
        args["name"] = name
        
    if domain_name and entity_type != "domain":
        # Resolve the domain name to an applicationDomainId
        domain_res = await _call_mcp(session, "getApplicationDomains", {"name": domain_name})
        if not domain_res:
            return {"error": f"Domain '{domain_name}' not found."}
        args["applicationDomainId"] = domain_res[0]["id"]
    
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
        
    elif entity_type == "event_api":
        data = await _call_mcp(session, "getEventApis", args)
        return {"result": data}
        
    elif entity_type == "event_api_product":
        data = await _call_mcp(session, "getEventApiProducts", args)
        return {"result": data}
        
    elif entity_type == "schema":
        data = await _call_mcp(session, "getSchemas", args)
        return {"result": data}
        
    elif entity_type == "enum":
        # Solace getEnums uses 'names' instead of 'name'
        if "name" in args:
            args["names"] = [args.pop("name")]
        data = await _call_mcp(session, "getEnums", args)
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


async def _create_entity(session: ClientSession, entity_type: str, name: str, domain_name: str = None, enum_values: list = None) -> dict:
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

    elif entity_type == "event_api":
        data = await _call_mcp(session, "createEventApi", {
            "name": name,
            "applicationDomainId": domain_id,
            "brokerType": "solace"
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        evt_api_id = entity.get("id")
        if not evt_api_id:
            return {"error": f"Created event api but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createEventApiVersion", {
            "eventApiId": evt_api_id,
            "version": "0.1.0"
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    elif entity_type == "event_api_product":
        data = await _call_mcp(session, "createEventApiProduct", {
            "name": name,
            "applicationDomainId": domain_id,
            "brokerType": "solace"
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        evt_api_prod_id = entity.get("id")
        if not evt_api_prod_id:
            return {"error": f"Created event api product but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createEventApiProductVersion", {
            "eventApiProductId": evt_api_prod_id,
            "version": "0.1.0"
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    elif entity_type == "schema":
        data = await _call_mcp(session, "createSchema", {
            "name": name,
            "applicationDomainId": domain_id,
            "schemaType": "jsonSchema"  # Defaulting to jsonSchema, can be enhanced later
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        schema_id = entity.get("id")
        if not schema_id:
            return {"error": f"Created schema but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createSchemaVersion", {
            "schemaId": schema_id,
            "version": "0.1.0"
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    elif entity_type == "enum":
        if not enum_values:
            return {"error": "enum_values is required when creating an enum"}
            
        data = await _call_mcp(session, "createEnum", {
            "name": name,
            "applicationDomainId": domain_id
        })
        entity = data[0] if isinstance(data, list) and len(data) > 0 else data
        enum_id = entity.get("id")
        if not enum_id:
            return {"error": f"Created enum but couldn't get ID. Response: {data}"}

        ver_data = await _call_mcp(session, "createEnumVersion", {
            "enumId": enum_id,
            "version": "0.1.0",
            "values": [{"value": v} for v in enum_values]
        })
        return {"result": {"entity": entity, "initial_version": ver_data}}

    return {"error": f"Unsupported entity_type: {entity_type}"}


async def _create_version(session: ClientSession, entity_type: str, entity_id: str, version: str, enum_values: list = None) -> dict:
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
    elif entity_type == "event_api":
        ver_data = await _call_mcp(session, "createEventApiVersion", {
            "eventApiId": entity_id,
            "version": version
        })
        return {"result": ver_data}
    elif entity_type == "event_api_product":
        ver_data = await _call_mcp(session, "createEventApiProductVersion", {
            "eventApiProductId": entity_id,
            "version": version
        })
        return {"result": ver_data}
    elif entity_type == "schema":
        ver_data = await _call_mcp(session, "createSchemaVersion", {
            "schemaId": entity_id,
            "version": version
        })
        return {"result": ver_data}
    elif entity_type == "enum":
        if not enum_values:
            return {"error": "enum_values is required when versioning an enum"}
            
        ver_data = await _call_mcp(session, "createEnumVersion", {
            "enumId": entity_id,
            "version": version,
            "values": [{"value": v} for v in enum_values]
        })
        return {"result": ver_data}
    
    return {"error": f"Unsupported entity_type: {entity_type}"}


async def _delete_entity(session: ClientSession, entity_type: str, entity_id: str) -> dict:
    """Executes the delete_solace_entity logic."""
    if entity_type == "domain":
        res = await _call_mcp(session, "deleteApplicationDomain", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted application domain with ID {entity_id}"}
    elif entity_type == "application":
        res = await _call_mcp(session, "deleteApplication", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted application with ID {entity_id}"}
    elif entity_type == "event":
        res = await _call_mcp(session, "deleteEvent", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event with ID {entity_id}"}
    elif entity_type == "event_api":
        res = await _call_mcp(session, "deleteEventApi", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event api with ID {entity_id}"}
    elif entity_type == "event_api_product":
        res = await _call_mcp(session, "deleteEventApiProduct", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event api product with ID {entity_id}"}
    elif entity_type == "schema":
        res = await _call_mcp(session, "deleteSchema", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted schema with ID {entity_id}"}
    elif entity_type == "enum":
        res = await _call_mcp(session, "deleteEnum", {"id": entity_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted enum with ID {entity_id}"}
    
    return {"error": f"Unsupported entity_type for deletion: {entity_type}"}


async def _delete_version(session: ClientSession, entity_type: str, version_id: str) -> dict:
    """Executes the delete_solace_entity_version logic."""
    if entity_type == "application":
        res = await _call_mcp(session, "deleteApplicationVersion", {"versionId": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted application version {version_id}"}
    elif entity_type == "event":
        res = await _call_mcp(session, "deleteEventVersion", {"id": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event version {version_id}"}
    elif entity_type == "event_api":
        res = await _call_mcp(session, "deleteEventApiVersion", {"versionId": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event api version {version_id}"}
    elif entity_type == "event_api_product":
        res = await _call_mcp(session, "deleteEventApiProductVersion", {"versionId": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted event api product version {version_id}"}
    elif entity_type == "schema":
        res = await _call_mcp(session, "deleteSchemaVersion", {"id": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted schema version {version_id}"}
    elif entity_type == "enum":
        res = await _call_mcp(session, "deleteEnumVersion", {"id": version_id})
        if isinstance(res, dict) and "error" in res: return res
        return {"result": f"Successfully deleted enum version {version_id}"}
    
    return {"error": f"Unsupported entity_type for version deletion: {entity_type}"}


# ── The Interceptor ────────────────────────────────────────────────────────
async def execute_smart_tool(session: ClientSession, tool_name: str, args: dict) -> str:
    """Routes the LLM's generic tool call to the Python mapping engine."""
    
    try:
        if tool_name == "search_solace_entity":
            result = await _search_entity(session, args.get("entity_type"), args.get("name"), args.get("domain_name"))
        elif tool_name == "get_entity_relationships":
            result = await _get_relationships(session, args.get("entity_id"), args.get("relationship_type"))
        elif tool_name == "create_solace_entity":
            result = await _create_entity(session, args.get("entity_type"), args.get("name"), args.get("domain_name"), args.get("enum_values"))
        elif tool_name == "create_solace_entity_version":
            result = await _create_version(session, args.get("entity_type"), args.get("entity_id"), args.get("version"), args.get("enum_values"))
        elif tool_name == "delete_solace_entity":
            result = await _delete_entity(session, args.get("entity_type"), args.get("entity_id"))
        elif tool_name == "delete_solace_entity_version":
            result = await _delete_version(session, args.get("entity_type"), args.get("version_id"))
        else:
            return json.dumps({"error": f"Unknown smart tool: {tool_name}"})
            
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Execution failed: {str(exc)}"})
