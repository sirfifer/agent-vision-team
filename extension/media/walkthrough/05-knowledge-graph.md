## Knowledge Graph Data Flow

```
  ┌──────────────────────────────────────┐
  │         Your Documents               │
  │                                      │
  │  docs/vision/*.md                    │
  │  docs/architecture/*.md              │
  └──────────────┬───────────────────────┘
                 │
          Ingestion (Setup Wizard
           or manual command)
                 │
  ┌──────────────▼───────────────────────┐
  │        Knowledge Graph               │
  │     (.avt/knowledge-graph.jsonl)      │
  │                                      │
  │  ┌──────────┐  ┌──────────────────┐  │
  │  │ Entities │  │ Relations        │  │
  │  │          │  │                  │  │
  │  │ vision   │──│ entity ←→ entity │  │
  │  │ arch     │  │                  │  │
  │  │ quality  │  └──────────────────┘  │
  │  └──────────┘                        │
  │       ▲              │               │
  │       │         Observations         │
  │       │      (grow over time)        │
  └───────┼──────────────┼───────────────┘
          │              │
   ┌──────┴─────┐  ┌─────▼──────┐
   │ KG         │  │ Agents     │
   │ Librarian  │  │ query KG   │
   │ curates    │  │ for context │
   └────────────┘  └────────────┘
```

### What gets stored

- **Vision standards** — Immutable principles (tier-protected)
- **Architecture patterns** — Component designs, API patterns
- **Quality observations** — Problems found, solutions applied
- **Solution patterns** — Promoted from recurring observations
- **Decision history** — What was decided and why

The KG Librarian periodically curates: consolidating
redundant observations, promoting patterns, and syncing
important entries to archival files in `.avt/memory/`.
