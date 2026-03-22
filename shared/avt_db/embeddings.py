"""Batch embedding generation and storage for KG entities and context routes.

This module pre-computes embeddings and stores them in SurrealDB. It's
designed to be run as a batch job (not in the hot path of hooks), since
model loading takes ~2s and each embedding ~5ms.

Usage:
    python -m avt_db.embeddings          # Embed all entities + context routes
    python -m avt_db.embeddings --entity AuthService  # Single entity
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from .vectors import get_embedding, get_embedding_safe, get_dimension


def embed_all_entities(db, batch_size: int = 50) -> dict:
    """Generate and store embeddings for all entities without one.

    Args:
        db: A connected sync Surreal instance.
        batch_size: Process this many entities per query batch.

    Returns:
        {"embedded": int, "skipped": int, "errors": int}
    """
    # Get entities missing embeddings
    results = db.query(
        "SELECT id, name, entity_type, observations FROM entity "
        "WHERE embedding = NONE OR embedding = []"
    )
    if not results:
        return {"embedded": 0, "skipped": 0, "errors": 0}

    embedded = 0
    errors = 0

    for row in results:
        name = row.get("name", "")
        entity_type = row.get("entity_type", "")
        observations = row.get("observations", [])

        # Build text representation for embedding
        text_parts = [name, entity_type]
        for obs in observations:
            # Skip metadata observations
            if not obs.startswith(("protection_tier:", "source_file:")):
                text_parts.append(obs)
        text = " ".join(text_parts)

        embedding = get_embedding_safe(text)
        if embedding is None:
            errors += 1
            continue

        # Store embedding
        record_id = str(row.get("id", ""))
        db.query(
            f"UPDATE {record_id} SET embedding = $emb",
            {"emb": embedding},
        )
        embedded += 1

    skipped = len(results) - embedded - errors
    return {"embedded": embedded, "skipped": skipped, "errors": errors}


def embed_single_entity(db, entity_name: str) -> bool:
    """Generate and store embedding for a single entity by name.

    Returns True if successful, False otherwise.
    """
    results = db.query(
        "SELECT id, name, entity_type, observations FROM entity WHERE name = $name",
        {"name": entity_name},
    )
    if not results:
        return False

    row = results[0]
    text_parts = [row.get("name", ""), row.get("entity_type", "")]
    for obs in row.get("observations", []):
        if not obs.startswith(("protection_tier:", "source_file:")):
            text_parts.append(obs)

    embedding = get_embedding_safe(" ".join(text_parts))
    if embedding is None:
        return False

    record_id = str(row.get("id", ""))
    db.query(f"UPDATE {record_id} SET embedding = $emb", {"emb": embedding})
    return True


def embed_context_routes(db) -> dict:
    """Generate and store embeddings for all context routes.

    Returns:
        {"embedded": int, "errors": int}
    """
    results = db.query(
        "SELECT id, route_id, keywords, context FROM context_route "
        "WHERE embedding = NONE OR embedding = []"
    )
    if not results:
        return {"embedded": 0, "errors": 0}

    embedded = 0
    errors = 0

    for row in results:
        keywords = row.get("keywords", [])
        context = row.get("context", "")
        route_id = row.get("route_id", "")

        text = f"{route_id} {' '.join(keywords)} {context[:200]}"
        embedding = get_embedding_safe(text)
        if embedding is None:
            errors += 1
            continue

        record_id = str(row.get("id", ""))
        db.query(f"UPDATE {record_id} SET embedding = $emb", {"emb": embedding})
        embedded += 1

    return {"embedded": embedded, "errors": errors}


def semantic_search(db, query: str, limit: int = 10, min_score: float = 0.3) -> list[dict]:
    """Search entities by semantic similarity.

    Args:
        db: Connected sync Surreal instance.
        query: Natural language search query.
        limit: Max results to return.
        min_score: Minimum cosine similarity threshold.

    Returns:
        List of entity dicts with 'score' field added.
    """
    embedding = get_embedding_safe(query)
    if embedding is None:
        # Fall back to text search if embeddings unavailable
        return db.query(
            "SELECT * FROM entity WHERE "
            "string::lowercase(name) CONTAINS string::lowercase($q) "
            "LIMIT $limit",
            {"q": query, "limit": limit},
        ) or []

    # Vector similarity search
    results = db.query(
        "SELECT *, vector::similarity::cosine(embedding, $emb) AS score "
        "FROM entity WHERE embedding != NONE AND embedding != [] "
        "ORDER BY score DESC LIMIT $limit",
        {"emb": embedding, "limit": limit},
    )
    if not results:
        return []

    # Filter by minimum score
    return [r for r in results if r.get("score", 0) >= min_score]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for AVT knowledge graph")
    parser.add_argument("--entity", help="Embed a single entity by name")
    parser.add_argument("--routes", action="store_true", help="Embed context routes only")
    args = parser.parse_args()

    from .connection import get_sync_connection

    db = get_sync_connection()

    if args.entity:
        ok = embed_single_entity(db, args.entity)
        print(f"{'OK' if ok else 'FAILED'}: {args.entity}")
    elif args.routes:
        result = embed_context_routes(db)
        print(f"Context routes: {result}")
    else:
        start = time.monotonic()
        entity_result = embed_all_entities(db)
        route_result = embed_context_routes(db)
        elapsed = time.monotonic() - start
        print(f"Entities: {entity_result}")
        print(f"Routes: {route_result}")
        print(f"Done in {elapsed:.1f}s")
