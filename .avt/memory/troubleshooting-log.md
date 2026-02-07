# Troubleshooting Log

This file contains problems encountered, approaches tried, and what ultimately worked. Curated by the KG Librarian subagent.

## Format

Each entry should include:
- **Date**: When the issue was encountered
- **Problem**: Description of the issue
- **Component**: Which component(s) were affected
- **Tried**: Approaches that didn't work
- **Solution**: What ultimately resolved the issue
- **KG Reference**: Link to observations in the KG

---

## Example Entry

**Date**: 2024-01-20

**Problem**: Tests failing intermittently in AuthService

**Component**: AuthService, TokenValidator

**Tried**:
- Increasing test timeouts (didn't help)
- Mocking time-based functions (still flaky)
- Adding delays between test cases (unreliable)

**Solution**: The issue was shared mutable state in the TokenValidator singleton. Refactored TokenValidator to be a protocol with instance-based implementations. Each test now gets a fresh instance.

**Root Cause**: Singleton pattern violated our "no singletons in production code" vision standard. The test failures were exposing the architectural issue.

**KG Reference**: Observation added to `TokenValidator` entity: "Refactored from singleton to protocol-based DI on 2024-01-20 to fix test flakiness"

---

## KGClient Compact Race Condition

**Date**: 2026-02-06

**Problem**: Governance decision entities (`governance_decision` type) silently lost after KG curation runs compaction

**Component**: KGClient (governance server), KnowledgeGraph (KG server), JSONLStorage

**Tried**:
- Running curation operations after governance decisions were recorded; entities vanished from JSONL
- Investigated whether the entity type was the issue (it was not)

**Solution**: The root cause is that `KGClient.record_decision()` appends directly to the JSONL file, bypassing the `KnowledgeGraph` in-memory cache. When `compact()` runs (triggered by curation or after 1000 writes), it rewrites the JSONL from memory, dropping any externally appended records. Workaround: call `kg._load_from_storage()` after KGClient writes and before any compaction-triggering operations. Permanent fix: route writes through the KG API.

**Root Cause**: Two independent writers to the same JSONL file (KnowledgeGraph via in-memory cache + KGClient via direct append) without coordination. Classic write-write conflict in append-only storage.

**KG Reference**: See `mcp-servers/knowledge-graph/README.md` "Known Issues" section.

---

## governance_decision EntityType

**Date**: 2026-02-06

**Problem**: Governance decisions written to KG were incorrectly using `entityType: "solution_pattern"`, conflating audit records with actual solution patterns

**Component**: KGClient (`collab_governance/kg_client.py`), EntityType enum (`collab_kg/models.py`)

**Solution**: Added `GOVERNANCE_DECISION = "governance_decision"` to the `EntityType` enum and updated `KGClient.record_decision()` to use the new type. This correctly separates governance audit records from solution patterns in the KG.

**KG Reference**: `EntityType` enum in `mcp-servers/knowledge-graph/collab_kg/models.py`

---

*This file is automatically curated by the KG Librarian. Manual edits should be synced back to the KG.*
