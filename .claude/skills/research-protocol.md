---
name: research-protocol
description: Research Protocol for gathering intelligence to inform development decisions
user_invocable: true
---

# Research Protocol

The researcher subagent gathers intelligence to inform development decisions and track external changes that affect the project.

## Research Modes

1. **Periodic/Maintenance Research**: Scheduled or triggered research to track external changes
   - Monitor APIs, frameworks, and tools the project depends on
   - Detect breaking changes, deprecations, or new features
   - Track security advisories for dependencies
   - Example: Monitoring Claude Code for new features or changes

2. **Exploratory/Design Research**: Deep investigation to inform new development
   - Research approaches before architectural decisions
   - Compare alternative technologies or patterns
   - Investigate unfamiliar domains the project is entering
   - Example: Evaluating authentication libraries before implementing auth

## When to Use the Researcher

- **Before architectural decisions**: Spawn researcher to gather options and tradeoffs
- **When integrating external services**: Research API patterns, rate limits, best practices
- **When adopting new technologies**: Comprehensive technology evaluation
- **For periodic dependency monitoring**: Track changes in key dependencies

## Research Workflow

1. **Create research prompt**: Define the research in `.avt/research-prompts/` or via the dashboard
2. **Spawn researcher**:
   ```
   Task tool -> subagent_type: researcher
   prompt: "Execute the research prompt in .avt/research-prompts/rp-xxx.md"
   ```
3. **Researcher outputs**: Research briefs stored in `.avt/research-briefs/`
4. **Use findings**: Reference research briefs in task briefs for workers

## Model Selection

The researcher uses different models based on complexity:
- **Opus 4.6**: Novel domains, architectural decisions, security analysis, ambiguous requirements
- **Sonnet 4.5**: Changelog monitoring, version updates, straightforward API documentation

When spawning the researcher, specify `model: opus` or `model: sonnet` based on complexity, or use `model_hint: auto` to let the system decide.

## Research Outputs

- **Change Reports**: Structured reports for periodic/maintenance research with actionable items
- **Research Briefs**: Comprehensive analysis for exploratory research with recommendations

## Example: Monitoring External Dependencies

**Task**: Set up periodic monitoring for Claude Code updates

1. **Create research prompt** (via dashboard or manually):
   ```yaml
   type: periodic
   topic: "Claude Code CLI updates and new features"
   context: "This project depends on Claude Code. We need to track new features, breaking changes, and best practices."
   scope: "Check official Anthropic documentation, changelog, and release notes"
   model_hint: sonnet
   output: change_report
   schedule:
     type: weekly
     day_of_week: 1
     time: "09:00"
   ```

2. **Research runs automatically** on schedule or on-demand
3. **Review change reports** in `.avt/research-briefs/`
4. **Act on findings**: Create task briefs for any required updates
