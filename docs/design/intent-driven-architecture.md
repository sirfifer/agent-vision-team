# Intent-Driven Architecture: Design Document

## Overview

This design introduces three interconnected capabilities that transform the architecture layer from a static registry of rules into a living, self-justifying system:

1. **Intent & Outcome Metadata** on every architectural entity
2. **Vision-Aligned Architecture Ingestion** with collaborative enrichment
3. **Intent-Driven Architectural Evolution** with real experimentation

The governing principle: constraints should carry their own justification, and that justification becomes the basis for intelligently evolving those constraints.

---

## Part 1: Intent & Outcome as First-Class Metadata

### The Problem

Today, architectural entities carry descriptions ("ServiceRegistry Pattern: decouple service creation from consumption") but not structured *intent* (why it exists) or *desired outcome* (what measurable result it produces). Without these, governance can only say "you're breaking architecture" rather than engaging with whether the architecture is being well-served.

### Data Model

KG entities store observations as `list[str]`. Rather than changing this core model, we add new structured observation prefixes (consistent with existing `protection_tier:`, `statement:`, `rationale:`):

```
intent: <why this decision exists, what problem it solves>
desired_outcome: <what measurable result this should produce>
outcome_metric: <metric_name>|<success_criteria>|<baseline_value>
vision_alignment: <vision_entity_name>|<explanation of how it serves that standard>
metadata_completeness: full|partial|none
```

New relation type `serves_vision` formally links architecture entities to vision standards.

### Files Modified

| File | Change |
|------|--------|
| `mcp-servers/knowledge-graph/collab_kg/models.py` | Add `OUTCOME_METRIC`, `EVOLUTION_PROPOSAL`, `EXPERIMENT_RESULT` to `EntityType` enum |
| `mcp-servers/knowledge-graph/collab_kg/metadata.py` (new) | Helper functions: `get_intent()`, `get_desired_outcome()`, `get_outcome_metrics()`, `get_vision_alignments()`, `get_metadata_completeness()`, `build_intent_observations()` |
| `mcp-servers/knowledge-graph/collab_kg/server.py` | Add tools: `get_architecture_completeness`, `set_entity_metadata`, `validate_ingestion` |
| `mcp-servers/knowledge-graph/collab_kg/ingestion.py` | Extract `## Intent`, `## Desired Outcome`, `## Metrics`, `## Vision Alignment` sections during parsing |

### Backward Compatibility

- Existing entities without intent/outcome continue to function
- All new observation prefixes are additive; existing code ignores them
- `metadata_completeness: none` is the implicit default for legacy entities
- JSONL storage format is unchanged
- Existing E2E tests pass without modification

---

## Part 2: Vision-Aligned Architecture Ingestion

### The Problem

Currently, architecture documents are ingested in bulk without validating that each granular piece (a) has clear intent/outcome, or (b) serves the project's vision. A user can ingest an architecture doc that contains decisions orthogonal to or conflicting with their vision standards, and the system won't catch this until governance blocks a worker downstream.

### Two Paths to Architecture

**Path A: Explicit (user creates architecture documents)**
- User writes or pastes architecture content in the wizard
- Claude formats it (existing flow)
- User reviews and saves (existing flow)
- New: after ingestion, an enrichment step validates each entity

**Path B: Emergent (architecture arises from Claude's work)**
- Workers make decisions (pattern_choice, component_design) during tasks
- Governance approves the decisions
- Approved decisions are recorded as quality-tier `solution_pattern` entities
- KG Librarian identifies recurring patterns
- New: promotion to architecture tier requires intent/outcome enrichment

### Enrichment Flow (Path A)

After architecture documents are ingested and KG entities are created, a new enrichment step runs:

1. Call `validate_ingestion('architecture')` to get completeness status of every entity
2. Display each entity with its completeness status (complete / partial / missing)
3. For entities missing intent/outcome:
   - Claude proposes intent, outcome, and vision alignments based on the entity's description and available vision standards
   - User accepts, edits, or replaces Claude's suggestions
   - If Claude's proposed intent/outcome naturally covers vision alignment, nothing more is needed
   - If vision alignment is unclear, Claude proposes how the entity might serve specific standards, or suggests architectural modifications that would better serve the vision
4. For entities where no vision alignment exists and none can be inferred:
   - Flag for human attention ("This architectural decision doesn't appear to serve any vision standard")
   - Human can explain the connection, mark as utility (no direct vision link), or reconsider the decision
5. Save enriched metadata back to KG entities

### Enrichment Flow (Path B: Emergent)

When the KG Librarian or orchestrator proposes promoting a quality-tier decision to an architecture entity:

1. System loads the original governance decision and its review verdict
2. Claude proposes intent/outcome based on the decision context
3. Human reviews and approves the promotion with enriched metadata
4. New architecture entity is created with full intent/outcome/vision-alignment

### Key Design Principle: Collaboration Over Blocking

The enrichment step is collaborative, not a gate. Architecture can be ingested with partial metadata. The system tracks completeness and nudges toward full enrichment, but it does not block work. The enrichment can happen iteratively:
- First pass: capture what's obvious
- Later passes: refine as the project matures
- Ongoing: the KG Librarian flags entities whose metadata has gone stale

### Files Modified

| File | Change |
|------|--------|
| `extension/src/providers/DashboardWebviewProvider.ts` | Update `ARCHITECTURE_FORMAT_PROMPT` to include Intent/Desired Outcome/Metrics/Vision Alignment sections; add handlers for `validateIngestion`, `suggestEntityMetadata`, `saveEntityMetadata` |
| `extension/webview-dashboard/src/components/wizard/steps/ArchitectureEnrichmentStep.tsx` (new) | Post-ingestion enrichment wizard step |
| `extension/webview-dashboard/src/types.ts` | Add `'architecture-enrichment'` to WizardStep, new message types |
| `extension/webview-dashboard/src/context/DashboardContext.tsx` | State for enrichment results, suggestions |
| `.claude/agents/kg-librarian.md` | Add architecture metadata curation and completeness monitoring protocol |
| `.claude/agents/worker.md` | Add intent-aware decision making section |

### Claude's Suggestion Prompt (for enrichment)

When suggesting metadata for an entity, Claude receives:
- The entity's existing observations (description, rationale, usage, etc.)
- All loaded vision standards
- Other architecture entities (for cross-reference)

And proposes: intent, desired outcome, suggested metrics, vision alignments, and a confidence level. The prompt emphasizes: if the intent/outcome naturally demonstrates vision alignment, that is sufficient; do not manufacture artificial connections.

---

## Part 3: Intent-Driven Architectural Evolution

### The Problem

When an agent believes a better approach exists for achieving an architectural entity's stated purpose, the current system can only block or approve. There is no path for structured experimentation and evidence-based evolution.

### Three Zones of Work

| Zone | Condition | Behavior |
|------|-----------|----------|
| **Covered, compliant** | Work follows existing architecture | Normal governance review, proceed |
| **Uncovered** | No architecture applies | Open territory; propose new architecture |
| **Covered, but improvable** | Agent believes it can better serve intent/outcome | Evolution proposal workflow |

### Evolution Workflow

```
Agent recognizes potential improvement
    |
    v
propose_evolution(target_entity, proposed_change, rationale, experiment_plan, validation_criteria)
    |
    v
Governance reviews proposal against intent/outcome/vision
    |--- blocked: rationale insufficient or violates vision
    |--- needs_human_review: significant architectural scope
    |--- approved for experimentation
            |
            v
        Agent works in isolated git worktree
        Collects REAL evidence via submit_experiment_evidence()
            |
            v
        present_evolution_results() compiles side-by-side comparison
            |
            v
        Human reviews:
            |--- rejected: recorded as attempted approach in KG
            |--- needs_more_evidence: back to experimentation
            |--- approved:
                    |
                    v
                KG entity updated with new architecture
                Cascading alignment tasks generated for dependent entities
                Evolution recorded in institutional memory
```

### New Governance Tools

| Tool | Purpose |
|------|---------|
| `propose_evolution(target_entity, proposed_change, rationale, experiment_plan, validation_criteria, agent)` | Submit an evolution proposal referencing the entity's intent/outcome |
| `submit_experiment_evidence(proposal_id, evidence_type, evidence_data, agent)` | Submit real evidence from an experiment |
| `present_evolution_results(proposal_id, agent)` | Compile and present side-by-side comparison for human review |
| `approve_evolution(proposal_id, verdict, guidance, cascade_tasks)` | Human approval/rejection with optional cascade |
| `propose_architecture_promotion(decision_id, entity_name, entity_type, intent, desired_outcome, ...)` | Promote an approved decision to a formal architecture entity |

### Validation Integrity ("Real, Not Mock")

This is the hardest enforcement problem in the design. An agent can produce convincing but hollow validation. The system enforces integrity through:

**Structural checks** (automated, in `evidence_validator.py`):
- Evidence source paths must exist on disk
- Timestamps must be within the experiment's time window
- Test output must contain actual pass/fail counts, not just assertions of success
- Benchmark data must have numeric values
- No mock environment flags set (unless in E2E testing)

**Validation contract** (auto-generated from outcome metadata):
- The entity's `outcome_metric` observations define what success looks like
- The agent does not define its own success criteria; the system generates the contract
- The same measurement is run against both current architecture (control) and proposed (experiment)

**Independent reproduction**:
- After the proposing agent submits evidence, a separate agent (quality-reviewer or a dedicated verifier) re-runs the validation
- If results diverge beyond a tolerance, the experiment is invalidated
- Both sets of results are presented to the human

**What this prevents**:
- Custom benchmarks designed to favor the proposal
- Mock tests that assert success without testing real behavior
- Synthetic data that doesn't represent actual system conditions
- "Proving" improvement by testing against a strawman baseline

### Cascading Alignment

When an evolution is approved, the system identifies downstream impact:
1. Query KG for all entities with `follows_pattern` or `serves_vision` relations to the evolved entity
2. For each affected entity, create a governed task: "Align X with the evolved Y"
3. Each alignment task includes the change description and guidance from the approval

### Files Modified

| File | Change |
|------|--------|
| `mcp-servers/governance/collab_governance/models.py` | Add `ARCHITECTURE_EVOLUTION`, `EXPERIMENT_PROPOSAL`, `EXPERIMENT_RESULT` to `DecisionCategory`; add `EvolutionProposal` model |
| `mcp-servers/governance/collab_governance/store.py` | Add `evolution_proposals` table with CRUD methods |
| `mcp-servers/governance/collab_governance/server.py` | Add all five new tools (propose, evidence, present, approve, promote) |
| `mcp-servers/governance/collab_governance/reviewer.py` | Add `review_evolution_proposal()` method; add `_format_architecture_with_intent()` that surfaces intent/outcome in review prompts; update `_build_decision_prompt()` instructions to consider intent |
| `mcp-servers/governance/collab_governance/kg_client.py` | Add `get_entity_with_metadata()`, `get_entities_serving_vision()` |
| `mcp-servers/governance/collab_governance/evidence_validator.py` (new) | Evidence integrity validation |
| `.claude/agents/governance-reviewer.md` | Add intent-based review protocol for evolution proposals |

---

## Part 4: Governance Reviewer Enhancement

### Current State

The reviewer formats architecture as: `- **name** (type): first 3 observations` (reviewer.py:383-392). It checks decisions against vision and architecture using flat rule matching. Intent is implicit, inferred by the AI.

### Enhanced State

New `_format_architecture_with_intent()` method surfaces structured metadata:

```
- **service_registry_pattern** (pattern): Decouple service creation from consumption
  Intent: Enable any component to be tested in isolation without real dependencies
  Desired Outcome: Every consumer testable with stubs in < 500ms
  Serves: protocol_based_di (All services swappable via protocols)
```

Updated review instructions:

```
1. Check if this decision CONFLICTS with any vision standard. If yes, verdict is "blocked".
2. Check if this decision deviates from established architecture patterns.
   When checking alignment, consider whether the decision serves the INTENT
   of the pattern, not just its literal form. A decision that achieves the
   pattern's desired outcome through a different mechanism may be acceptable.
3. If the decision affects an architecture entity, verify it serves that
   entity's stated intent and desired outcome.
4. If the decision is a "deviation" or "scope_change" category, verdict
   should be "needs_human_review".
5. If the decision aligns with standards and serves their intent, verdict
   is "approved".
```

This is the key behavioral shift: governance evaluates against intent, not just form.

---

## Part 5: Edge Cases

### No Vision Standards Defined Yet

- Intent and desired outcome can still be captured (they stand alone)
- Vision alignment fields left empty; `metadata_completeness: partial`
- When vision standards are added later, `validate_ingestion('architecture')` identifies entities needing alignment
- The enrichment step shows a notice: "No vision standards defined yet. Vision alignment will be checked later."

### Partial Metadata

Allowed and tracked. `metadata_completeness` has three levels:
- `none`: legacy entity, no structured metadata
- `partial`: some fields present (e.g., intent but no outcome)
- `full`: intent + outcome + at least one vision alignment

System nudges toward completeness but does not block.

### Conflicting Architectural Entities

Two entities with conflicting intents or overlapping outcomes:
- Detected during `validate_ingestion` by comparing intents and outcomes
- Flagged as a governance finding requiring human resolution

### Architecture Emerging Without a Document

When no architecture document exists and Claude makes all decisions:
- Each approved `pattern_choice` or `component_design` decision is recorded
- The system tracks these as potential architecture
- After threshold occurrences (3+), the KG Librarian flags for promotion
- Promotion requires intent/outcome enrichment (with Claude proposing, human approving)
- This is the organic path; it works exactly like the document path except the source is Claude's decisions rather than a human-authored document

### Evolution Proposal for Entity with Missing Metadata

If an agent proposes evolution against an entity lacking intent/outcome:
- The proposal is routed to `needs_human_review`
- Guidance explains: "This entity lacks structured intent/outcome. Please enrich it before evolution can be evaluated."
- This creates natural pressure to enrich metadata

---

## Implementation Sequence

### Phase 1: Data Model + Metadata Helpers
1. Add new `EntityType` values to KG models
2. Create `metadata.py` helper module
3. Add KG server tools: `get_architecture_completeness`, `set_entity_metadata`, `validate_ingestion`
4. Add governance model extensions: new `DecisionCategory` values, `EvolutionProposal` model
5. Add `evolution_proposals` SQLite table
6. E2E scenario: `s14_architecture_metadata.py`

### Phase 2: Ingestion Enhancement
1. Extend `parse_document()` to extract intent/outcome/metrics/vision-alignment sections
2. Update `ARCHITECTURE_FORMAT_PROMPT` in DashboardWebviewProvider
3. Build `ArchitectureEnrichmentStep.tsx` wizard step
4. Wire up message handlers: `validateIngestion`, `suggestEntityMetadata`, `saveEntityMetadata`
5. E2E scenario: `s15_ingestion_with_metadata.py`

### Phase 3: Governance Reviewer Enhancement
1. Add `_format_architecture_with_intent()` to reviewer
2. Update `_build_decision_prompt()` instructions
3. Add `review_evolution_proposal()` method
4. Update KG client with `get_entity_with_metadata()`, `get_entities_serving_vision()`
5. Update agent definitions: worker, governance-reviewer, kg-librarian

### Phase 4: Evolution Workflow
1. Implement `propose_evolution`, `submit_experiment_evidence`, `present_evolution_results`, `approve_evolution`, `propose_architecture_promotion` tools
2. Create `evidence_validator.py`
3. Implement cascading alignment task generation
4. E2E scenarios: `s16_evolution_proposal_lifecycle.py`, `s17_cascading_alignment.py`

---

## Verification

### Unit Testing
- `metadata.py` helpers: parse and build observation strings correctly
- `evidence_validator.py`: reject synthetic evidence, accept real evidence
- `ingestion.py`: extract new sections from formatted architecture documents

### E2E Testing
- **s14**: Create architecture entity with intent/outcome, verify `get_architecture_completeness` reports it correctly, verify `set_entity_metadata` updates it
- **s15**: Ingest an architecture document containing Intent/Desired Outcome sections, verify entities have structured metadata
- **s16**: Full evolution lifecycle: propose, experiment, submit evidence, present, approve, verify KG entity updated
- **s17**: After evolution approval, verify cascading alignment tasks are created for dependent entities

### Manual Validation
- Walk through the enrichment wizard step with a real architecture document
- Verify Claude's suggestions for intent/outcome are meaningful
- Submit an evolution proposal and verify the side-by-side comparison is useful to a human reviewer
