# EventFlow AI Capabilities

This document outlines the specific operations that the `EventFlow_AI` assistant is currently capable of performing across the Solace Event Portal (Design-Time) and Solace Event Broker (Runtime). 

The AI operates using a "Smart Router" architecture, which maps generalized, natural language intents into specific Solace API or MCP Server calls, specifically optimized to keep the cognitive load low for smaller LLMs (like Qwen 8B).

## Supported Entities & Operations (Design-Time / Event Portal)

| Entity | Search / List | Create | Delete | Version Creation | Version Deletion | Duplicate | Mutate Relationships | Impact Analysis |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Application Domain** | ✅ | ✅ | ✅ | *N/A* | *N/A* | ❌ | ❌ | ❌ |
| **Application** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Event (Pub/Sub)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Event API** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Event API Product** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Schema** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Enumeration** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |

*(Note: Application Domains do not inherently have versions in Solace, so versioning operations do not apply to them).*

---

## Detailed Operation Breakdown

### 1. Search, Discovery & Deep Traversal
**Tools:** `search_solace_entity`, `get_entity_relationships`
- **Capabilities:**
  - Search for a specific entity by its exact name or ID.
  - Filter entities by the specific **Domain Name** they reside in.
  - **Domain to Applications:** Fetch all applications residing inside a specific Application Domain.
  - **Application to Events:** Fetch the specific Events that a given Application version is declared to **produce** or **consume**.
  - **Product to APIs:** Fetch the Event APIs bundled within an Event API Product.
  - **API to Applications:** Fetch the Applications that consume an Event API (via reverse lookup).

### 2. Creation & Versioning
**Tools:** `create_solace_entity`, `create_solace_entity_version`
- **Capabilities:**
  - Create new Application Domains, Applications, Events, Event APIs, Event API Products, Schemas, and Enumerations.
  - Create new specific versions (e.g., `1.0.0`, `1.1.0`) for existing entities.

### 3. Duplication (Cloning)
**Tool:** `duplicate_solace_entity`
- **Capabilities:**
  - Clones an existing entity, automatically strips system metadata, and publishes a new version with identical configurations and relationships under a new name.

### 4. Relationship Mutations
**Tool:** `update_entity_relationship`
- **Capabilities:**
  - Dynamically link entities together (e.g., adding an Event to an Event API, or an Event API to a Product) without the AI having to manually construct complex JSON PATCH arrays.

### 5. Impact Analysis (Reverse Dependency Lookup)
**Tool:** `get_entity_impact`
- **Capabilities:**
  - Performs a reverse graph lookup (using the `referencedBy` API) to determine what other entities rely on a given entity version. (e.g., "Which Products will break if I modify this Event?").

### 6. Deletion (Destructive)
**Tools:** `delete_solace_entity`, `delete_solace_entity_version`
- **Capabilities:**
  - Perform hard deletes of any supported entity or specific *versions* of those entities.
  - **Warning:** Deleting an Application Domain will cascade and potentially affect entities residing within it.

---

## Supported Broker Operations (Runtime / SEMP v2)

The AI connects directly to the Solace Event Broker via the SEMP v2 Config and Monitor REST APIs, utilizing macro-tools to manage runtime resources.

### 7. Queue Management
**Tool:** `manage_solace_queue`
- **Capabilities:**
  - **Get:** Fetch detailed configuration and realtime monitoring stats for a queue (e.g., checking spool usage or bindings).
  - **Create:** Provision a new queue with specific QoS settings like Max TTL and Max Spool Usage.
  - **Update:** Modify existing queue configurations on the fly.
  - **Delete:** Remove a queue from the broker.
  - **Duplicate:** Read an existing queue's configuration, create a new queue with identical settings, and automatically copy all topic subscriptions over.

### 8. Topic Subscriptions
**Tool:** `manage_queue_subscription`
- **Capabilities:**
  - **List:** View all topic subscriptions mapped to a specific queue.
  - **Add:** Bind a new Solace topic filter (supporting `*` and `>`) to a queue.
  - **Remove:** Delete a specific topic subscription from a queue.
