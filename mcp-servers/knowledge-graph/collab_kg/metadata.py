"""Helpers for reading and writing structured metadata on KG entities.

Architectural entities carry structured metadata as observation strings with
known prefixes. This module provides typed access without changing the core
Entity model (observations remain list[str] for backward compatibility).

Observation prefixes handled here:
    intent:               Why this architectural decision exists
    outcome_metric:       metric_name|success_criteria|baseline_value  (optional, zero or more)
    vision_alignment:     vision_entity_name|explanation
    metadata_completeness: full|partial|none
"""

from typing import Optional


def get_intent(observations: list[str]) -> Optional[str]:
    """Extract intent from observations."""
    for obs in observations:
        if obs.startswith("intent: "):
            return obs[len("intent: "):]
    return None


def get_outcome_metrics(observations: list[str]) -> list[dict]:
    """Parse all outcome_metric observations into structured dicts.

    Each metric observation has the format: metric_name|success_criteria|baseline_value
    """
    metrics = []
    for obs in observations:
        if obs.startswith("outcome_metric: "):
            raw = obs[len("outcome_metric: "):]
            parts = raw.split("|")
            if len(parts) >= 3:
                metrics.append({
                    "name": parts[0].strip(),
                    "criteria": parts[1].strip(),
                    "baseline": parts[2].strip(),
                })
            elif len(parts) == 2:
                metrics.append({
                    "name": parts[0].strip(),
                    "criteria": parts[1].strip(),
                    "baseline": "not measured",
                })
    return metrics


def get_vision_alignments(observations: list[str]) -> list[dict]:
    """Parse all vision_alignment observations into structured dicts.

    Each alignment observation has the format: vision_entity_name|explanation
    """
    alignments = []
    for obs in observations:
        if obs.startswith("vision_alignment: "):
            raw = obs[len("vision_alignment: "):]
            parts = raw.split("|", 1)
            alignments.append({
                "vision_entity": parts[0].strip(),
                "explanation": parts[1].strip() if len(parts) > 1 else "",
            })
    return alignments


def get_metadata_completeness(observations: list[str]) -> str:
    """Determine metadata completeness level from observations.

    Returns:
        "full" if intent + at least one vision alignment are present,
        "partial" if either is present,
        "none" if neither is present.
    """
    has_intent = any(o.startswith("intent: ") for o in observations)
    has_vision = any(o.startswith("vision_alignment: ") for o in observations)

    if has_intent and has_vision:
        return "full"
    if has_intent or has_vision:
        return "partial"
    return "none"


def build_intent_observations(
    intent: str = "",
    metrics: Optional[list[dict]] = None,
    vision_alignments: Optional[list[dict]] = None,
) -> list[str]:
    """Build structured observations from intent metadata.

    Args:
        intent: Why this architectural decision exists.
        metrics: Optional list of dicts with keys: name, criteria, baseline.
        vision_alignments: List of dicts with keys: vision_entity, explanation.

    Returns:
        List of observation strings ready to add to an entity.
    """
    obs: list[str] = []

    if intent:
        obs.append(f"intent: {intent}")

    for m in (metrics or []):
        baseline = m.get("baseline", "not measured")
        obs.append(f"outcome_metric: {m['name']}|{m['criteria']}|{baseline}")

    for va in (vision_alignments or []):
        explanation = va.get("explanation", "")
        obs.append(f"vision_alignment: {va['vision_entity']}|{explanation}")

    # Compute and append completeness
    completeness = "full" if (intent and vision_alignments) else (
        "partial" if (intent or vision_alignments) else "none"
    )
    obs.append(f"metadata_completeness: {completeness}")

    return obs


def strip_metadata_observations(observations: list[str]) -> list[str]:
    """Remove all structured metadata observations from a list.

    Useful when replacing metadata: strip the old, then append the new.
    """
    prefixes = (
        "intent: ",
        "outcome_metric: ",
        "vision_alignment: ",
        "metadata_completeness: ",
    )
    return [o for o in observations if not any(o.startswith(p) for p in prefixes)]
