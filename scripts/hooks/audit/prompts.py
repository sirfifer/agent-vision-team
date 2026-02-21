"""Prompt builders for each tier of the audit escalation chain.

Each tier gets a progressively richer prompt:
- Haiku: anomaly batch + matching directives + recent statistics (quick triage)
- Sonnet: Haiku's triage + full event window + settings + directives (substantive analysis)
- Opus: Sonnet's analysis + full context package (strategic deep dive)
"""

from __future__ import annotations

import json
from pathlib import Path


def build_haiku_prompt(
    anomalies: list[dict],
    directives: list[dict],
    recent_stats: dict,
    recent_recommendations: list[dict],
) -> str:
    """Build the Haiku triage prompt.

    Haiku's job: quick pattern recognition. Is this a known pattern or something new?
    Should we escalate to Sonnet?
    """
    anomaly_lines = []
    for a in anomalies:
        anomaly_lines.append(f"- [{a.get('severity', 'info')}] {a.get('type', 'unknown')}: {a.get('description', '')}")
        metrics = a.get("metric_values", {})
        if metrics:
            anomaly_lines.append(f"  Metrics: {json.dumps(metrics)}")

    directive_questions = []
    for d in directives:
        directive_questions.append(f"- **{d['id']}**: {d.get('haiku_question', '')}")

    rec_lines = []
    for r in recent_recommendations[:5]:
        rec_lines.append(
            f"- [{r.get('status', 'unknown')}] {r.get('anomaly_type', '')}: "
            f"{r.get('suggestion', 'no suggestion')} (seen {r.get('evidence_count', 0)}x)"
        )

    return f"""You are an audit triage agent. Analyze these anomalies and determine if they need deeper analysis.

## Detected Anomalies
{chr(10).join(anomaly_lines) if anomaly_lines else "(none)"}

## Questions to Consider (from observation directives)
{chr(10).join(directive_questions) if directive_questions else "(none)"}

## Recent Statistics
{json.dumps(recent_stats, indent=2) if recent_stats else "(none available)"}

## Existing Recommendations
{chr(10).join(rec_lines) if rec_lines else "(none)"}

## Instructions
Return ONLY a JSON object:
{{
  "verdict": "known_pattern" | "emerging_pattern" | "milestone",
  "analysis": "brief explanation of what you see",
  "escalate": true | false,
  "recommendations": [
    {{
      "anomaly_type": "the anomaly type",
      "suggestion": "actionable suggestion",
      "category": "setting_tune | prompt_revision | range_adjustment | governance_health | coverage_gap | general"
    }}
  ]
}}

Rules:
- "known_pattern": anomaly matches an existing recommendation or is a known recurring pattern
- "emerging_pattern": anomaly shows a new trend worth investigating
- "milestone": significant event that warrants strategic analysis
- Set escalate=true ONLY for emerging_pattern or milestone
- Keep analysis under 200 words
- Recommendations should be specific and actionable
- If the anomaly is covered by an existing recommendation with high evidence count, say so"""


def build_sonnet_prompt(
    haiku_triage: dict,
    anomalies: list[dict],
    directives: list[dict],
    event_window: list[dict],
    current_settings: dict,
    existing_recommendations: list[dict],
) -> str:
    """Build the Sonnet analysis prompt.

    Sonnet's job: substantive analysis. Correlate across data, draft refined recommendations,
    decide if Opus deep dive is needed.
    """
    directive_questions = []
    for d in directives:
        directive_questions.append(f"- **{d['id']}**: {d.get('sonnet_question', '')}")
        directive_questions.append(f"  Opus trigger: {d.get('opus_trigger', 'none')}")

    event_summary = _summarize_events(event_window)

    return f"""You are a governance and quality analysis agent. Perform substantive analysis of these audit findings.

## Haiku Triage Result
- Verdict: {haiku_triage.get("verdict", "unknown")}
- Analysis: {haiku_triage.get("analysis", "none")}
- Preliminary recommendations: {json.dumps(haiku_triage.get("recommendations", []), indent=2)}

## Anomaly Details
{json.dumps(anomalies, indent=2)}

## Analysis Questions (from observation directives)
{chr(10).join(directive_questions)}

## Recent Event Activity
{event_summary}

## Current Settings
{json.dumps(current_settings, indent=2) if current_settings else "(not available)"}

## Existing Recommendations
{json.dumps(existing_recommendations, indent=2) if existing_recommendations else "(none)"}

## Instructions
Return ONLY a JSON object:
{{
  "analysis": "detailed analysis (500 words max)",
  "recommendations": [
    {{
      "anomaly_type": "the anomaly type this addresses",
      "suggestion": "specific, actionable recommendation",
      "category": "setting_tune" | "prompt_revision" | "range_adjustment" | "governance_health" | "coverage_gap",
      "evidence": "what data supports this recommendation",
      "confidence": "high" | "medium" | "low"
    }}
  ],
  "escalate_to_opus": true | false,
  "opus_context": "if escalating, describe the specific strategic question for Opus"
}}

Rules:
- Correlate anomalies with settings values and event patterns
- For setting recommendations, specify the current value AND the recommended value
- For prompt recommendations, identify the specific prompt and suggest wording changes
- Set escalate_to_opus=true ONLY if you see a significant milestone or systemic issue
- Check the Opus trigger conditions from each directive to decide escalation
- If superseding an existing recommendation, note which one
- Be constructive: focus on what would improve outcomes, not what is wrong"""


def build_opus_prompt(
    sonnet_analysis: dict,
    anomalies: list[dict],
    directives: list[dict],
    event_window: list[dict],
    current_settings: dict,
    existing_recommendations: list[dict],
    session_summaries: list[dict],
) -> str:
    """Build the Opus deep dive prompt.

    Opus's job: strategic analysis. Root cause analysis, systemic recommendations,
    setting range changes, prompt effectiveness evaluation.
    The prompt is constructed by Sonnet with full context.
    """
    event_summary = _summarize_events(event_window)

    directive_triggers = []
    for d in directives:
        directive_triggers.append(f"- **{d['id']}**: {d.get('opus_trigger', 'none')}")

    session_lines = []
    for s in session_summaries[:10]:
        session_lines.append(
            f"- {s.get('session_id', 'unknown')[:8]}: "
            f"{s.get('total_events', 0)} events, "
            f"{s.get('approval_count', 0)} approved, "
            f"{s.get('block_count', 0)} blocked, "
            f"{s.get('task_count', 0)} tasks"
        )

    return f"""You are a strategic audit analyst performing a deep dive into system behavior patterns.

## Sonnet's Analysis
{json.dumps(sonnet_analysis, indent=2)}

## Strategic Question
{sonnet_analysis.get("opus_context", "Perform a comprehensive analysis of the anomaly patterns.")}

## Anomaly Details
{json.dumps(anomalies, indent=2)}

## Directive Trigger Conditions (why this deep dive was triggered)
{chr(10).join(directive_triggers)}

## Recent Event Activity
{event_summary}

## Current Settings (with ranges where applicable)
{json.dumps(current_settings, indent=2) if current_settings else "(not available)"}

## Session Summaries (recent)
{chr(10).join(session_lines) if session_lines else "(none)"}

## Existing Recommendations
{json.dumps(existing_recommendations, indent=2) if existing_recommendations else "(none)"}

## Instructions
Return ONLY a JSON object:
{{
  "deep_analysis": "comprehensive strategic analysis (1000 words max)",
  "root_causes": [
    {{
      "description": "root cause description",
      "evidence": "supporting evidence from the data",
      "impact": "how this affects system outcomes"
    }}
  ],
  "recommendations": [
    {{
      "anomaly_type": "the anomaly type or 'systemic'",
      "suggestion": "specific recommendation",
      "category": "setting_tune" | "prompt_revision" | "range_adjustment" | "governance_health" | "coverage_gap",
      "evidence": "data supporting this recommendation",
      "priority": "high" | "medium" | "low",
      "scope": "which settings/prompts/components are affected"
    }}
  ],
  "setting_range_changes": [
    {{
      "setting": "setting path (e.g., thresholds.governance_block_rate)",
      "current_range": "current min-max",
      "recommended_range": "new min-max",
      "rationale": "why this range should change"
    }}
  ],
  "prompt_assessments": [
    {{
      "prompt_id": "which prompt (e.g., context-reinforcement, agent-definition)",
      "effectiveness": "high" | "medium" | "low",
      "issue": "what is not working",
      "suggestion": "specific wording or approach change"
    }}
  ]
}}

Rules:
- Focus on root causes, not symptoms
- For setting changes, specify exact values with evidence
- For range changes, explain why the current range is insufficient
- For prompt assessments, reference specific observed outcomes
- Prioritize recommendations by potential impact
- Be constructive: acknowledge what is working well
- Consider cross-setting interactions and systemic effects"""


def _summarize_events(events: list[dict], max_lines: int = 30) -> str:
    """Create a concise summary of events for LLM consumption."""
    if not events:
        return "(no events)"

    # Group by type
    by_type: dict[str, int] = {}
    for e in events:
        etype = e.get("type", "unknown")
        by_type[etype] = by_type.get(etype, 0) + 1

    lines = [f"Total: {len(events)} events"]
    for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"  {etype}: {count}")
        if len(lines) >= max_lines:
            lines.append(f"  ... and {len(by_type) - max_lines + 1} more types")
            break

    # Show last few events with details
    lines.append("")
    lines.append("Recent events (last 5):")
    for e in events[-5:]:
        data_str = json.dumps(e.get("data", {}))
        if len(data_str) > 200:
            data_str = data_str[:200] + "..."
        lines.append(
            f"  [{e.get('type', '?')}] {e.get('ts_iso', '?')} session={e.get('session_id', '?')[:8]} data={data_str}"
        )

    return "\n".join(lines)


def load_directives(directives_path: "Path | str | None" = None) -> list[dict]:
    """Load observation directives from the directives.json file."""
    if directives_path is None:
        directives_path = Path(__file__).parent / "directives.json"
    else:
        directives_path = Path(directives_path)

    if not directives_path.exists():
        return []

    try:
        data = json.loads(directives_path.read_text())
        return data.get("directives", [])
    except (json.JSONDecodeError, OSError):
        return []


def match_directives(anomalies: list[dict], directives: list[dict]) -> list[dict]:
    """Find directives relevant to the given anomalies.

    Matches based on the anomaly type against directive watch patterns.
    """
    if not directives:
        return []

    anomaly_types = {a.get("type", "") for a in anomalies}
    matched = []

    for directive in directives:
        watches = directive.get("watches", [])
        for watch in watches:
            if watch == "*":
                matched.append(directive)
                break
            # Simple glob matching: trailing wildcard matches prefix
            if watch.endswith("*"):
                # e.g. "governance.*" -> "governance."
                prefix = watch[:-1]
                if any(at.startswith(prefix) for at in anomaly_types):
                    matched.append(directive)
                    break
            elif watch in anomaly_types:
                matched.append(directive)
                break

    return matched
