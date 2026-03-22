"""Vector-based context route matching for context reinforcement.

Replaces Jaccard keyword similarity with cosine vector similarity.
Designed to be called from the context-reinforcement.py hook when
AVT_STORAGE_BACKEND=surreal is set.

The hook calls `find_best_route_vector()` instead of the Jaccard-based
`find_best_match()`. Pre-computed embeddings must exist on context_route
records (run `python -m avt_db.embeddings --routes` first).

If embeddings aren't available (model not installed or routes have no
embeddings), falls back to returning None so the hook can use Jaccard.
"""

from __future__ import annotations

from typing import Optional

from .vectors import get_embedding_safe


def find_best_route_vector(
    db,
    input_text: str,
    threshold: float = 0.3,
) -> Optional[dict]:
    """Find the best context route by vector similarity.

    Args:
        db: Connected sync Surreal instance.
        input_text: The tool input text to match against.
        threshold: Minimum cosine similarity score.

    Returns:
        Best matching route dict with 'score' field, or None.
    """
    embedding = get_embedding_safe(input_text)
    if embedding is None:
        return None

    results = db.query(
        "SELECT route_id, context, "
        "vector::similarity::cosine(embedding, $emb) AS score "
        "FROM context_route "
        "WHERE embedding != NONE AND embedding != [] "
        "ORDER BY score DESC LIMIT 1",
        {"emb": embedding},
    )

    if not results:
        return None

    best = results[0]
    if best.get("score", 0) >= threshold:
        return {
            "id": best.get("route_id", ""),
            "context": best.get("context", ""),
            "score": best.get("score", 0),
        }
    return None


def find_similar_entities(
    db,
    input_text: str,
    limit: int = 5,
    threshold: float = 0.3,
) -> list[dict]:
    """Find KG entities semantically similar to the input text.

    Useful for context reinforcement to inject relevant KG knowledge
    based on what the agent is currently working on.

    Args:
        db: Connected sync Surreal instance.
        input_text: Text to match against entity embeddings.
        limit: Max results.
        threshold: Minimum cosine similarity.

    Returns:
        List of entity dicts with 'score' field.
    """
    embedding = get_embedding_safe(input_text)
    if embedding is None:
        return []

    results = db.query(
        "SELECT name, entity_type, protection_tier, observations, "
        "vector::similarity::cosine(embedding, $emb) AS score "
        "FROM entity "
        "WHERE embedding != NONE AND embedding != [] "
        "ORDER BY score DESC LIMIT $limit",
        {"emb": embedding, "limit": limit},
    )

    if not results:
        return []

    return [r for r in results if r.get("score", 0) >= threshold]
