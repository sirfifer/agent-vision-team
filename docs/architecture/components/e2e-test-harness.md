# E2E Test Harness

## Type

component

## Description

End-to-end testing framework with 14 scenarios covering the full governance lifecycle. Each scenario generates a unique project, exercises MCP server interactions, and validates outcomes through domain-agnostic structural assertions. Supports parallel execution via ThreadPoolExecutor.

## Usage

Run via `python e2e/run-e2e.py` or `bash e2e/run-e2e.sh`. Supports `--parallel` flag and scenario filtering.

## Internal Structure

```mermaid
graph TD
    Runner["run-e2e.py"]
    BS["BaseScenario"]
    Gen["ProjectGenerator"]
    Val["Validation Harness"]
    Par["Parallel Executor"]

    Runner --> BS
    Runner --> Par
    BS --> Gen
    BS --> Val
    Par --> BS

    subgraph Scenarios
        S1["s01: Basic Entity CRUD"]
        S2["s02: Tier Protection"]
        S14["s14: Full Lifecycle"]
    end

    BS --> S1
    BS --> S2
    BS --> S14
```

## Dependencies

- pytest (for assertions)
- MCP servers (library mode or HTTP mode)
- ThreadPoolExecutor (parallel execution)

## Patterns Used

- E2E Scenario Pattern (P7)
- Structural assertions (domain-agnostic)
