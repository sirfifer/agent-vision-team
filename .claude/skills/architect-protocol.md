---
name: architect-protocol
description: Architect Protocol for designing architecture with intent and expected outcomes
user_invocable: true
---

# Architect Protocol

The architect subagent designs architecture with explicit intent and expected outcomes for every decision.

## When to Spawn the Architect

- **Project bootstrap**: When setting up a new project's architecture from vision standards
- **Major feature design**: When a feature requires multiple new architectural decisions
- **Cross-cutting concerns**: When a change affects multiple components or layers
- **Vision alignment questions**: When it's unclear how to serve a vision standard architecturally

## Architect vs Worker

| Concern | Architect | Worker |
|---------|-----------|--------|
| Designs architecture | Yes | No |
| Writes implementation code | No | Yes |
| Submits decisions with intent/outcome | Yes (required) | Yes (required) |
| Produces task briefs for workers | Yes | No |
| Implements task briefs | No | Yes |
| Runs quality gates | No | Yes |

## Intent and Outcome Protocol

Every architectural decision (whether from architect or worker) must include when calling `submit_decision`:

- **intent**: WHY this decision is being made. What problem does it solve?
- **expected_outcome**: WHAT measurable result is expected. Tied to vision where applicable.
- **vision_references**: WHICH vision standard names this outcome serves.

The governance reviewer evaluates intent/outcome quality as part of every decision review. Missing or vague intent/outcome is flagged as a quality finding.

This protocol forces deliberate thinking: articulating an expected outcome before choosing an approach changes how options are evaluated and produces architecture traceable back to vision standards.
