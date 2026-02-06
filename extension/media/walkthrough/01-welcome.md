## System Architecture

```
┌─────────────────────────────────────────┐
│            VS Code Extension            │
│                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │Dashboard │  │ Sidebar  │  │ Status │ │
│  │ Panel    │  │ Tree     │  │  Bar   │ │
│  │          │  │ Views    │  │        │ │
│  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │             │            │      │
└───────┼─────────────┼────────────┼──────┘
        │             │            │
   ┌────▼─────────────▼────────────▼────┐
   │         MCP Server Layer           │
   │                                    │
   │  ┌──────────┐ ┌─────────┐ ┌─────┐ │
   │  │Knowledge │ │Quality  │ │Gov. │ │
   │  │Graph     │ │Server   │ │Srvr │ │
   │  │:3101     │ │:3102    │ │:3103│ │
   │  └──────────┘ └─────────┘ └─────┘ │
   └────────────────────────────────────┘
        │             │            │
   ┌────▼─────────────▼────────────▼────┐
   │          Agent Team                │
   │                                    │
   │  Orchestrator  ·  Worker           │
   │  Quality Reviewer  ·  KG Librarian │
   │  Governance Reviewer  ·  Researcher│
   │  Project Steward                   │
   └────────────────────────────────────┘
```

The extension connects to three MCP servers that provide
institutional memory, quality enforcement, and governance
review. Agents coordinate through the orchestrator to
implement work governed by your project's standards.
