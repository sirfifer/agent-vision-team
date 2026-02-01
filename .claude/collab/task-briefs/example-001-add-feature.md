# Task Brief: Example Feature Implementation

**Task ID**: 001
**Priority**: Medium
**Assigned to**: Worker subagent
**Estimated scope**: 1-2 components

## Objective

Add a new feature to demonstrate the collaborative intelligence workflow.

## Context

This is an example task brief that demonstrates the structure workers should receive. In a real scenario, this would contain:
- Specific feature requirements
- Acceptance criteria
- Links to related KG entities
- Architectural constraints from the KG

## Scope

### In Scope
- Creating new components following established patterns
- Writing tests for new functionality
- Updating documentation

### Out of Scope
- Modifying vision-tier entities
- Changing core architectural patterns
- Making breaking changes to public APIs

## Pre-Work Checklist

Before starting implementation:
1. Query KG: `get_entities_by_tier("vision")` — load vision constraints
2. Query KG: `search_nodes("<component name>")` — find related patterns
3. Review any `governed_by` relations for applicable standards

## Implementation Steps

1. Review the task requirements
2. Query the Knowledge Graph for relevant patterns and standards
3. Implement the feature following discovered patterns
4. Write tests to verify functionality
5. Run quality gates: `check_all_gates()`
6. Report completion with structured summary

## Completion Criteria

- All quality gates pass
- No vision or architecture conflicts
- Test coverage meets threshold (80%)
- Code follows established patterns from KG

## Notes

- If you encounter a vision conflict, stop immediately and report it
- If you need to deviate from an architectural pattern, document why
- Update KG observations for the components you modify
