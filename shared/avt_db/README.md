# avt_db: Shared SurrealDB Persistence Layer

Unified embedded database layer for all Agent Vision Team MCP servers and hooks. Replaces the legacy storage (JSONL + 2x SQLite + audit JSONL+SQLite) with a single SurrealKV-backed database at `.avt/avt.db`.

## Activation

Set the environment variable before starting MCP servers:

```bash
export AVT_STORAGE_BACKEND=surreal
```

When unset, each server uses its legacy backend (JSONL or SQLite).

## Package Structure

| Module | Purpose |
|--------|---------|
| `connection.py` | Singleton connection manager (async + sync) |
| `schema.py` | 19-table schema across 5 domains (SCHEMA_VERSION=1) |
| `migration.py` | One-shot migration from JSONL/SQLite to SurrealDB |
| `embeddings.py` | Batch embedding generation via sentence-transformers |
| `vectors.py` | Vector utilities (lazy model loading, cosine similarity) |
| `context_search.py` | Vector-based context route matching |

## Schema Domains

| Domain | Tables | Purpose |
|--------|--------|---------|
| Knowledge Graph | `entity`, `relates_to` | Entities with observations and protection_tier; graph edges |
| Governance | `decision`, `review`, `governed_task`, `task_review`, `holistic_review`, `token_usage` | Decision lifecycle, reviews, task pairing |
| Quality/Trust | `finding`, `dismissal_history` | Quality findings, dismissal justifications |
| Audit | `audit_event`, `event_count`, `session_summary`, `metric_window`, `anomaly` | Event logging, anomaly detection |
| Context | `session_context`, `injection_history`, `context_route` | Context management, vector embeddings |
| Metadata | `schema_meta` | Schema version tracking |

## Connection Modes

```python
# Async (MCP servers)
from avt_db import get_connection
db = await get_connection()
result = await db.query("SELECT * FROM entity WHERE protection_tier = 'vision'")

# Sync (hook scripts, CLI)
from avt_db import get_sync_connection
db = get_sync_connection()
result = db.query("SELECT * FROM entity WHERE name = $name", {"name": "AuthService"})
```

Both modes use a singleton pattern (one instance per process). Connection + schema apply takes ~200ms; subsequent queries take < 5ms.

## Installation

```bash
cd shared
pip install -e .            # Core (surrealdb only)
pip install -e ".[vectors]" # With sentence-transformers for vector search
pip install -e ".[dev]"     # With pytest for running tests
```

## Migration from Legacy

The `migration.py` module provides one-shot migration functions:

- `migrate_kg()`: JSONL knowledge graph to SurrealDB entities/relations
- `migrate_governance()`: SQLite governance.db to SurrealDB decision/review tables
- `migrate_trust_engine()`: SQLite trust-engine.db to SurrealDB finding/dismissal tables

Each function renames the source file to `.bak` after migration. All are idempotent (safe to re-run).

## Running Tests

```bash
cd shared
pip install -e ".[dev]"
python -m pytest avt_db/tests/ -v
```

Tests require the `surrealdb` package. If not installed, tests are skipped gracefully.

## Key Implementation Details

- **Record IDs**: Use `type::thing('entity', $param)` with query params, not string interpolation
- **Graph traversals**: `->relates_to->entity.name` (outgoing), `<-relates_to<-entity.name` (incoming)
- **Array append**: `UPDATE entity:id SET observations += ['new']`
- **Tier protection**: Extracted from observations, enforced on write via `validate_write_access()`
- **SurrealDB version**: 1.0.8 (embedded, surrealkv:// protocol, no network/auth)
