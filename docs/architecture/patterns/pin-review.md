# PIN Review Methodology

## Type

pattern

## Description

All governance AI reviews follow the PIN (Positive, Innovative, Negative) methodology. Every review verdict includes `strengths_summary`, and every finding includes `strengths` and `salvage_guidance`. A blocked verdict does not mean "everything is wrong"; it means specific concerns need addressing while preserving identified strengths.

## Structure

```mermaid
graph TD
    Input["Decision/Plan Input"]
    Rev["AI Reviewer"]

    subgraph PIN Analysis
        P["Positive<br/>Identify strengths"]
        I["Innovative<br/>Acknowledge creativity"]
        N["Negative<br/>Assess concerns"]
    end

    subgraph Output
        V["Verdict<br/>(approved/blocked/needs_human_review)"]
        S["strengths_summary"]
        F["Findings[]<br/>each with strengths + salvage_guidance"]
        G["Guidance"]
    end

    Input --> Rev
    Rev --> P
    Rev --> I
    Rev --> N
    P --> S
    I --> S
    N --> F
    F --> G
    S --> V
    F --> V
```

## Key Properties

- Constructive by design: even blocked verdicts highlight what to preserve
- Standards verified: every approval lists which standards were checked
- Salvage guidance: every finding explains how to fix while keeping good parts
- Applied to: `submit_decision`, `submit_plan_for_review`, `submit_completion_review`
