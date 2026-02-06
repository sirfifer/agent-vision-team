## Protection Hierarchy

```
  ╔═══════════════════════════════════════╗
  ║          VISION  (Tier 1)             ║
  ║                                       ║
  ║  Core principles and invariants       ║
  ║  Modified by: Humans only             ║
  ║                                       ║
  ║  Examples:                            ║
  ║  · "All services use protocol-based   ║
  ║     dependency injection"             ║
  ║  · "No singletons in production code" ║
  ╚═══════════════════╤═══════════════════╝
                      │  overrides
  ╔═══════════════════▼═══════════════════╗
  ║       ARCHITECTURE  (Tier 2)          ║
  ║                                       ║
  ║  Patterns, components, abstractions   ║
  ║  Modified by: Human or Orchestrator   ║
  ║                (with approval)        ║
  ║                                       ║
  ║  Examples:                            ║
  ║  · ServiceRegistry pattern            ║
  ║  · AuthService component design       ║
  ╚═══════════════════╤═══════════════════╝
                      │  overrides
  ╔═══════════════════▼═══════════════════╗
  ║         QUALITY  (Tier 3)             ║
  ║                                       ║
  ║  Observations, findings, notes        ║
  ║  Modified by: Any agent               ║
  ║                                       ║
  ║  Examples:                            ║
  ║  · "AuthService lacks error handling" ║
  ║  · "Login flow refactored 2024-01-15" ║
  ╚═══════════════════════════════════════╝
```

**Key rule:** Lower tiers cannot modify or contradict
higher tiers. Vision conflicts stop all related work.
