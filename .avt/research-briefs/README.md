# Research Briefs

This directory contains research output from the researcher agent.

## Naming Convention

- Change Reports: `cr-YYYY-MM-DD-topic.md`
- Research Briefs: `rb-YYYY-MM-DD-topic.md`

## Change Report Format

For periodic/maintenance research:

```markdown
## Change Report: [Technology/API Name]

**Date**: YYYY-MM-DD
**Scope**: What was checked
**Sources**: URLs consulted

### Breaking Changes
- [Change]: [Impact] -> [Required Action]

### Deprecations
- [Feature]: [Timeline] -> [Migration Path]

### New Features
- [Feature]: [Relevance to Project]

### Security Advisories
- [Advisory]: [Severity] -> [Required Action]

### Recommendations
1. Priority action items
```

## Research Brief Format

For exploratory/design research:

```markdown
## Research Brief: [Topic]

**Question**: What decision this informs
**Date**: YYYY-MM-DD
**Sources**: Key sources consulted

### Context
Why this research was needed

### Options Evaluated

#### Option A: [Name]
- **How it works**: Conceptual overview
- **Pros**: In our context
- **Cons**: In our context
- **Integration**: What it would take
- **Risks**: What could go wrong

### Analysis
Comparative analysis, key tradeoffs

### Recommendation
Recommended approach with rationale

### Open Questions
What still needs human decision or further research
```

## Integration

Research briefs are:
1. Referenced in task briefs for workers
2. Key findings are recorded in the Knowledge Graph
3. Significant discoveries become baseline knowledge for future research
