# Design: SurrealDB Unified Storage Backend

## Motivation

The legacy storage layer used five separate stores across three MCP servers:

1. **Knowledge Graph**: JSONL file (`.avt/knowledge-graph.jsonl`)
2. **Governance decisions**: SQLite (`.avt/governance.db`)
3. **Trust engine**: SQLite (`.avt/trust-engine.db`)
4. **Audit events**: JSONL + SQLite
5. **Context reinforcement**: In-memory only

This fragmentation caused several problems:

- **KGClient compaction race condition**: The Governance server's `KGClient.record_decision()` appended directly to JSONL, bypassing the KG's in-memory cache. Compaction rewrote the file from cache, silently dropping those records.
- **No cross-layer queries**: Correlating a governance decision with its KG entity required reading two separate stores manually.
- **No graph traversals**: JSONL stored flat records; answering "what depends on service X?" required loading all entities and filtering in Python.
- **No vector search**: Semantic similarity search was unavailable without a vector-capable store.

## Decision

**SurrealDB 3.0** selected as the unified persistence layer.

### Alternatives Evaluated

ArcadeDB, Graphiti/FalkorDB Lite, Hindsight, Cognee, LanceDB, DuckDB+DuckPGQ, CozoDB, and 10+ others were evaluated. SurrealDB won because it uniquely combines all required capabilities in a single embedded package:

| Capability | SurrealDB | Nearest Alternative |
|-----------|-----------|-------------------|
| Embedded (no server process) | surrealkv:// protocol | CozoDB |
| Graph relations + traversals | Native RELATE + `->edge->` syntax | DuckPGQ (SQL-only) |
| Vector similarity search | `vector::similarity::cosine()` | LanceDB (no graph) |
| Live query subscriptions | Built-in | None (embedded) |
| Record-level permissions | DEFINE ACCESS / PERMISSIONS | None (embedded) |
| Scales to distributed cluster | Zero code changes | None |

## Architecture

### Shared Foundation: `shared/avt_db/`

A single Python package (`avt-db`) provides connection management, schema definitions, migration, and vector utilities. All MCP servers and hook scripts import from this package.

```
shared/avt_db/
  __init__.py        # Public API: get_connection, get_sync_connection, close_connection
  connection.py      # Singleton connection manager (async + sync)
  schema.py          # 19-table schema (SCHEMA_VERSION=1)
  migration.py       # One-shot migration from legacy formats
  embeddings.py      # Batch embedding generation
  vectors.py         # Vector utilities (lazy model loading)
  context_search.py  # Vector-based context route matching
```

### Per-Server Backends

Each MCP server has a drop-in SurrealDB replacement for its storage class:

| Server | Legacy | SurrealDB Backend |
|--------|--------|-------------------|
| Knowledge Graph | `graph.py` (JSONL) | `surreal_graph.py` |
| Quality | `trust_engine.py` (SQLite) | `surreal_trust_engine.py` |
| Governance | `store.py` + `kg_client.py` (SQLite + JSONL) | `surreal_store.py` + `surreal_kg_client.py` |
| Audit hooks | `stats.py` (SQLite) | `surreal_stats.py` |

### Feature Flag

A single environment variable controls all servers:

```bash
export AVT_STORAGE_BACKEND=surreal
```

Each server's `server.py` checks this at module load time and instantiates the appropriate backend. When unset, legacy backends are used.

### Database Location

All servers share one embedded database: `.avt/avt.db` (overridable via `AVT_SURREAL_DB_PATH`).

- **Protocol**: `surrealkv://` (embedded, no network, no auth)
- **Namespace**: `avt`
- **Database**: `main`

## Schema Design

19 tables across 5 domains, all idempotent (`DEFINE ... IF NOT EXISTS`):

**Knowledge Graph**: `entity` (SCHEMALESS, indexed on name/type/tier), `relates_to` (RELATION type for graph edges)

**Governance**: `decision`, `review`, `governed_task`, `task_review`, `holistic_review`, `token_usage`

**Quality/Trust**: `finding`, `dismissal_history`

**Audit**: `audit_event`, `event_count`, `session_summary`, `metric_window`, `anomaly`

**Context Reinforcement**: `session_context`, `injection_history`, `context_route`

**Metadata**: `schema_meta` (version tracking)

Record IDs are sanitized from entity names: lowercase, non-alphanumeric characters replaced with underscores (e.g., "My Service (v2)" becomes `entity:my_service__v2_`).

## Migration Strategy

One-shot migration functions in `migration.py`:

1. `migrate_kg()`: Reads `.avt/knowledge-graph.jsonl`, creates entities with sanitized IDs, extracts protection_tier from observations, creates relations, renames source to `.jsonl.bak`
2. `migrate_governance()`: Reads SQLite tables, parses JSON columns, UPSERTs into SurrealDB
3. `migrate_trust_engine()`: Reads findings and dismissals, migrates with timestamps

All functions are idempotent (skip if `.bak` already exists). Source files are renamed, not deleted, for rollback safety.

## Vector Search

Optional dependency (`pip install avt-db[vectors]`) provides semantic search via sentence-transformers (all-MiniLM-L6-v2, 384 dimensions).

- `embed_all_entities()`: Batch-embeds entity observations
- `semantic_search(query, threshold=0.3)`: Cosine similarity search via `vector::similarity::cosine()`
- `find_similar_entities(entity_name)`: Find entities semantically related to a given entity
- Falls back to Jaccard similarity if embeddings are unavailable

## Performance

- Connection + schema apply: ~200ms (first connection only)
- Subsequent queries: < 5ms
- SurrealDB SDK version: 1.0.8 (Rust-based, embedded)
- Python requirement: >= 3.12

## Testing

Test suites exist at multiple levels:

| Suite | Location | Scope |
|-------|----------|-------|
| Foundation | `shared/avt_db/tests/test_foundation.py` | Connection, schema, CRUD, graph traversals, migration |
| Vector search | `shared/avt_db/tests/test_vector_search.py` | Embeddings, cosine similarity, filtering |
| KG backend | `mcp-servers/knowledge-graph/tests/test_surreal_graph.py` | Entity CRUD, relations, tier protection |
| Governance backend | `mcp-servers/governance/tests_surreal/` | Decisions, reviews, task pairs, token usage |
| Quality backend | `mcp-servers/quality/collab_quality/test_surreal_trust_engine.py` | Findings, dismissals |
| Integration | `scripts/validation/test-surreal-integration.py` | Cross-server import and basic operation check |

All tests skip gracefully if the `surrealdb` package is not installed.
