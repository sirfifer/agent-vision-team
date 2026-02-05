# Vision Standards

Define your project's core principles below. Each standard is an inviolable rule that governs all development. Once ingested into the Knowledge Graph, vision standards are immutable — only humans can modify them.

For larger projects, you can split standards into separate files in this folder (e.g. `no-singletons.md`, `error-handling.md`). For smaller projects, listing them all here works well.

## Standards

<!-- Replace these examples with your project's actual vision standards -->

### Example: Protocol-Based Dependency Injection

**Statement:** All services use protocol-based dependency injection.

**Rationale:** Enables testability and loose coupling between components.

### Example: No Singletons in Production Code

**Statement:** No singletons in production code (test mocks are OK).

**Rationale:** Singletons create hidden coupling and make testing difficult.
