# Known Issues & Limitations

This document tracks known issues, missing capabilities, or limitations within the EventFlow AI and Solace MCP ecosystem, along with the reasoning behind them and proposed solutions.

---

## 1. Lack of "Duplicate" or "Clone" Capability

### What it is
The AI cannot currently duplicate or clone existing complex entities, such as taking an existing "NOTAM" Event API Product and directly duplicating it into a "NOTAMv2" product.

### Why it is
The Solace Event Portal REST API (EP API v2)—which powers our MCP server under the hood—does not provide a native `/clone` or `/duplicate` endpoint. While the Solace Web UI has a "Clone" button, the UI achieves this by running a complex sequence of GET and POST requests in the background. Currently, the AI's MCP tools only map to single-action operations (Create, Read, Delete, Version) and do not have a built-in macro to handle deep cloning.

### What we can do about it
To support this in the future, we need to build a custom "Orchestrator Tool" (e.g., `duplicate_event_api_product`) within the MCP server or the AI middleware. This tool would programmatically replicate the Web UI's behavior:
1. **Fetch:** Perform a GET request to retrieve the target entity and its version payload (including linked components).
2. **Clean:** Strip out system-generated metadata (`id`, `createdTime`, etc.) and mutate the `name` field to the requested new name.
3. **Recreate:** Perform POST requests to recreate the parent entity and its new `0.1.0` version, reattaching all the child links to the newly generated ID.

---

## 2. Missing Event API Tools (Resolved)

### What it is
Earlier in development, the AI was entirely missing the ability to manage Event APIs (and other specific architecture objects), despite them being a core part of the Solace Event Portal. 

### Why it is
The MCP Server leverages an OpenAPI parser to automatically generate tools from the Solace REST API documentation. However, the parser relies on explicit routing rules (defined in `server.py`) to know which endpoints should be exposed as AI tools. The route mappings for `eventApis`, `eventApiProducts`, `schemas`, and `enums` were originally omitted or excluded from the `RouteMap` list.

### What we can do about it
**Status:** Resolved. 
We fixed this by explicitly adding the missing entity routes to the `server.py` router configuration:
```python
RouteMap(pattern=r"^/api/v2/architecture/eventApis(/\{id\})?$", mcp_type=MCPType.TOOL),
RouteMap(pattern=r"^/api/v2/architecture/eventApiVersions(/\{versionId\})?$", mcp_type=MCPType.TOOL),
```
Going forward, if any new Solace entities (like new AsyncAPI objects) are unsupported by the AI, the first troubleshooting step should be to check the `RouteMap` in `solace-event-portal-designer-mcp/src/.../server.py` to ensure the specific API endpoint is being exposed to the parser.

---

## 3. Inability to Search Entities by ID (Resolved)

### What it is
The AI failed to locate an application domain when provided with its ID (e.g., `yjjffaefbje`). Instead, it incorrectly attempted to search for a domain with that ID as its *name*, returning zero results.

### Why it is
The `search_solace_entity` tool schema exposed to the LLM only provided `name` and `domain_name` fields. It completely lacked an `entity_id` field. Because of this, when the LLM was asked to search by ID, it placed the ID into the `name` field as a fallback, causing the underlying Solace query (`getApplicationDomains(name="...")`) to fail.

### What we can do about it
**Status:** Resolved.
We updated the `search_solace_entity` tool schema in `mcp_client.py` to accept an optional `entity_id` parameter. We then updated the `_search_entity` function to detect `entity_id` and map it to the underlying `ids` array parameter expected by Solace API retrieval tools.
