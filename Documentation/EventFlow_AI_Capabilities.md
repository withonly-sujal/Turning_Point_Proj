# EventFlow AI Capabilities

This document outlines the specific operations that the `EventFlow_AI` assistant is currently capable of performing across the Solace Event Portal ecosystem. 

The AI operates using a "Smart Router" architecture, which maps generalized, natural language intents into specific Solace MCP Server API calls.

## Supported Entities & Operations

| Entity | Search / List | Create | Delete | Version Creation | Version Deletion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Application Domain** | ✅ | ✅ | ✅ | *N/A* | *N/A* |
| **Application** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Event (Pub/Sub)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Event API** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Event API Product** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Schema** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Enumeration** | ✅ | ✅ | ✅ | ✅ | ✅ |

*(Note: Application Domains do not inherently have versions in Solace, so versioning operations do not apply to them).*

---

## Detailed Operation Breakdown

### 1. Search & Discovery
**Tool:** `search_solace_entity`
- **Capabilities:**
  - List all entities of a specific type.
  - Search for a specific entity by its exact name.
  - Filter entities (like Applications, Events, Event APIs, Schemas, Enumerations) by the specific **Domain Name** they reside in.

### 2. Creation
**Tool:** `create_solace_entity`
- **Capabilities:**
  - Create new Application Domains.
  - Create new Applications, Events, Event APIs, Event API Products, Schemas, and Enumerations.
  - *Note: When creating a non-domain entity, it is automatically assigned the `solace` Broker Type and initialized with a `0.1.0` version where applicable.*

### 3. Versioning
**Tool:** `create_solace_entity_version`
- **Capabilities:**
  - Create new specific versions (e.g., `1.0.0`, `1.1.0`) for existing Applications, Events, Event APIs, Event API Products, Schemas, and Enumerations.

### 4. Deletion (Destructive)
**Tools:** `delete_solace_entity`, `delete_solace_entity_version`
- **Capabilities:**
  - Perform hard deletes of any supported entity (Domain, Application, Event, Event API, Event API Product, Schema, Enumeration).
  - Perform hard deletes of specific *versions* of those entities.
  - **Warning:** Deleting an Application Domain will cascade and potentially affect entities residing within it.

### 5. Relationship Mapping
**Tool:** `get_entity_relationships`
- **Capabilities:**
  - **Domain to Applications:** Fetch all applications residing inside a specific Application Domain.
  - **Application to Events:** Fetch the specific Events that a given Application version is declared to **produce** or **consume**.
