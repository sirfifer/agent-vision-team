#!/usr/bin/env python3
"""Generate context router from KG entities and project rules.

Reads:
  - .avt/knowledge-graph.jsonl (KG entities with protection tiers)
  - .avt/project-config.json (project rules, if present)

Writes:
  - .avt/context-router.json (atomic: write to .tmp, rename)

Each route is a compact injection snippet for context drift prevention.
The hook scripts (context-reinforcement.py, post-compaction-reinject.sh)
consume this file at runtime.

Usage:
  python3 scripts/generate-context-router.py
  # or with explicit project dir:
  CLAUDE_PROJECT_DIR=/path/to/project python3 scripts/generate-context-router.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

# Paths
KG_JSONL_PATH = Path(PROJECT_DIR) / ".avt" / "knowledge-graph.jsonl"
PROJECT_CONFIG_PATH = Path(PROJECT_DIR) / ".avt" / "project-config.json"
OUTPUT_PATH = Path(PROJECT_DIR) / ".avt" / "context-router.json"

# Default max tokens per injection (~4 tokens per word)
DEFAULT_MAX_TOKENS = 400
DEFAULT_MAX_WORDS = DEFAULT_MAX_TOKENS // 4  # 100 words

# Stopwords for keyword extraction
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "not",
        "no",
        "nor",
        "so",
        "if",
        "then",
        "than",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "about",
        "above",
        "after",
        "again",
        "also",
        "any",
        "as",
        "because",
        "before",
        "between",
        "during",
        "into",
        "over",
        "through",
        "under",
        "until",
        "up",
        "while",
        "use",
        "used",
        "using",
    }
)


def tokenize(text: str) -> set[str]:
    """Extract keywords from text: lowercase, split on non-alphanumeric, filter stopwords."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def truncate_context(text: str, max_words: int) -> str:
    """Truncate text to max_words, appending '...' if truncated."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def extract_observation(observations: list[str], key: str) -> str | None:
    """Extract first observation matching 'key: value' prefix."""
    prefix = f"{key}: "
    for obs in observations:
        if obs.startswith(prefix):
            return obs[len(prefix) :]
    return None


def get_tier(observations: list[str]) -> str | None:
    """Extract protection tier from observations."""
    return extract_observation(observations, "protection_tier")


def get_statement(observations: list[str]) -> str:
    """Get the best statement/description from observations."""
    # Try statement first, then description, then first non-metadata observation
    for key in ("statement", "description", "rationale"):
        value = extract_observation(observations, key)
        if value:
            return value

    # Fall back to first observation that looks like content
    metadata_prefixes = (
        "protection_tier:",
        "source_file:",
        "title:",
        "document_type:",
        "entity_type:",
    )
    for obs in observations:
        if not any(obs.startswith(p) for p in metadata_prefixes):
            return obs
    return observations[0] if observations else ""


def build_kg_routes(max_words: int) -> list[dict]:
    """Build routes from KG JSONL entities."""
    routes = []

    if not KG_JSONL_PATH.exists():
        print(f"  KG JSONL not found at {KG_JSONL_PATH}", file=sys.stderr)
        return routes

    with open(KG_JSONL_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("type") != "entity":
                continue

            name = record.get("name", "")
            observations = record.get("observations", [])

            tier = get_tier(observations)
            if tier not in ("vision", "architecture"):
                continue

            statement = get_statement(observations)
            if not statement:
                continue

            # Build route
            tier_label = "VISION" if tier == "vision" else "ARCHITECTURE"
            context = f"{tier_label}: {statement}"
            context = truncate_context(context, max_words)

            # Keywords from entity name + statement
            keywords = tokenize(name) | tokenize(statement)

            # Scope based on tier
            scope = ["worker", "architect"] if tier == "vision" else ["worker"]

            route = {
                "id": f"kg-{name}",
                "keywords": sorted(keywords),
                "context": context,
                "tier": tier,
                "source": f"kg:{name}",
                "scope": scope,
            }
            routes.append(route)

    return routes


def build_rule_routes(max_words: int) -> list[dict]:
    """Build routes from project rules in project-config.json."""
    routes = []

    if not PROJECT_CONFIG_PATH.exists():
        return routes

    try:
        config = json.loads(PROJECT_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return routes

    rules_config = config.get("rules", {})
    entries = rules_config.get("entries", [])

    for rule in entries:
        if not rule.get("enabled", False):
            continue

        rule_id = rule.get("id", "")
        statement = rule.get("statement", "")
        enforcement = rule.get("enforcement", "enforce")
        scope = rule.get("scope", ["all"])

        if not statement:
            continue

        context = f"RULE [{enforcement}]: {statement}"
        context = truncate_context(context, max_words)

        keywords = tokenize(statement)

        route = {
            "id": f"rule-{rule_id}",
            "keywords": sorted(keywords),
            "context": context,
            "tier": "rule",
            "source": f"rule:{rule_id}",
            "scope": scope,
        }
        routes.append(route)

    return routes


def main() -> int:
    # Load settings for max token budget
    max_tokens = DEFAULT_MAX_TOKENS
    if PROJECT_CONFIG_PATH.exists():
        try:
            config = json.loads(PROJECT_CONFIG_PATH.read_text())
            cr = config.get("settings", {}).get("contextReinforcement", {})
            max_tokens = cr.get("maxTokensPerInjection", DEFAULT_MAX_TOKENS)
        except (json.JSONDecodeError, OSError):
            pass

    max_words = max_tokens // 4

    print(f"Generating context router from {KG_JSONL_PATH}", file=sys.stderr)

    # Build routes
    kg_routes = build_kg_routes(max_words)
    rule_routes = build_rule_routes(max_words)
    all_routes = kg_routes + rule_routes

    # Count by tier
    vision_count = sum(1 for r in all_routes if r["tier"] == "vision")
    arch_count = sum(1 for r in all_routes if r["tier"] == "architecture")
    rule_count = sum(1 for r in all_routes if r["tier"] == "rule")

    router = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "routeCount": len(all_routes),
        "routes": all_routes,
    }

    # Atomic write
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = OUTPUT_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(router, indent=2))
    tmp_path.rename(OUTPUT_PATH)

    print(
        f"Generated {len(all_routes)} routes "
        f"({vision_count} vision, {arch_count} architecture, {rule_count} rules) "
        f"-> {OUTPUT_PATH}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
