# Architecture

Define your project's architectural standards, patterns, and key components below. These are ingested into the Knowledge Graph and used by agents to make design decisions. Architecture documents can be modified with human approval; deviations require governance review.

For larger projects, you can break this into separate files in this folder (e.g. `service-registry.md`, `auth-service.md`, `api-versioning.md`). For smaller projects, a single document works well.

## Architectural Standards

<!-- Replace these examples with your project's actual architecture -->

### Example: API Versioning

**Description:** All public APIs use URL-based versioning (e.g. `/v1/users`).

**Rationale:** Enables backward-compatible evolution without breaking existing clients.

## Patterns

### Example: Service Registry

**Description:** Services register themselves at startup and are discovered via a central registry.

**Usage:** Inject `ServiceRegistry` and call `registry.resolve(ServiceProtocol)`.

## Components

### Example: AuthService

**Description:** Handles JWT-based authentication with refresh token rotation.

**State:** Tracked via observations in the Knowledge Graph.
