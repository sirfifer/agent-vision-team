# Research Prompts

> **IMPORTANT**: This directory is ONLY for research prompt definitions consumed by AVT
> researcher agents in a deployed AVT installation. If you are a Claude Code agent doing
> development work on the AVT codebase, this directory is not for you.

This directory contains research prompt definitions for the researcher agent.

## Format

Research prompts use YAML frontmatter with markdown content:

```yaml
---
type: periodic | exploratory
topic: "What to research"
context: "Why this matters"
scope: "Boundaries of the research"
model_hint: opus | sonnet | auto
output: change_report | research_brief | custom
schedule:
  type: once | daily | weekly | monthly
  time: "HH:MM"
  day_of_week: 0-6  # for weekly
  day_of_month: 1-31  # for monthly
related_entities:
  - "KG entity names"
---

# Research Prompt Title

## Research Instructions

Detailed instructions for the researcher...

## Scope

What to include and exclude...
```

## Creating Prompts

Prompts can be created via:
1. The dashboard Research Prompts panel
2. Manually creating files with the `rp-xxx.md` naming convention

## Execution

Prompts are executed by spawning the researcher subagent:
```
Task tool -> subagent_type: researcher
prompt: "Execute the research prompt in .avt/research-prompts/rp-xxx.md"
```
