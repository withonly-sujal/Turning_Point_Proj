# EventFlow AI Feature Backlog

Based on the prompt test requirements, here are the identified tasks needed to achieve full functionality.

## 🛠️ Epic 1: Event Portal (Design-Time) Enhancements
To handle complex Design-Time prompts, we need to expand the capabilities of `mcp_client.py` and the underlying Solace MCP Server.

*   **Task 1: Build a "Duplicate Entity" Orchestrator Tool**
    *   *Requirement:* Ability to clone a complex entity (like an Event API Product) and all its underlying links/versions.
    *   *Implementation:* A custom Python function that fetches the target entity, strips IDs, and posts a new entity with identical configurations.
*   **Task 2: Build an "Update Relationship" Tool**
    *   *Requirement:* Ability to add or remove objects from an existing entity version, such as adding an event to an Event API.
    *   *Implementation:* Expose Solace PATCH/PUT endpoints to modify the linked entities of a version.
*   **Task 3: Expand Relationship Graph Traversal**
    *   *Requirement:* Ability to drill down from an Event API Product to its Event APIs, or find apps consuming a specific Event API.
    *   *Implementation:* Add `event_apis` and `consuming_applications` to the `relationship_type` enum in the `get_entity_relationships` tool.
*   **Task 4: Implement Impact Analysis Tools (Reverse Lookups)**
    *   *Requirement:* Ability to query the blast radius of a change, such as finding which Event API Products use a specific Event, or finding outdated schema references.
    *   *Implementation:* Build a tool that leverages Solace's cross-reference/dependency API endpoints.

## 🚀 Epic 2: Event Broker (Runtime) Integration
To handle the prompts in the "Runtime / Event Broker" section, we need to build a completely new integration. The current system only talks to the design portal, not the actual messaging routers.

*   **Task 5: Integrate SEMP API MCP Server**
    *   *Requirement:* Establish a connection to the Solace PubSub+ SEMP (Solace Element Management Protocol) API to manage the runtime broker.
*   **Task 6: Build Queue Management Tools**
    *   *Requirement:* Ability to view queue configs, duplicate queues, and modify settings like TTL.
    *   *Implementation:* Expose tools like `get_queue_config`, `create_queue`, and `update_queue`.
*   **Task 7: Build Topic Subscription Tools**
    *   *Requirement:* Ability to manage topic subscriptions mapped to specific queues.
    *   *Implementation:* Expose tools like `add_queue_subscription`, `remove_queue_subscription`, and `get_queue_subscriptions`.
