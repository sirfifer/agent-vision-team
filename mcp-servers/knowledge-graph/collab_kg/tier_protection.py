"""Tier-based access control enforcement."""

from typing import Optional, Tuple

from .models import ProtectionTier


def get_entity_tier(observations: list[str]) -> Optional[ProtectionTier]:
    """Extract protection tier from an entity's observations (JSONL backend)."""
    for obs in observations:
        if obs.startswith("protection_tier: "):
            tier_value = obs.split("protection_tier: ", 1)[1].strip()
            try:
                return ProtectionTier(tier_value)
            except ValueError:
                return None
    return None


def get_entity_tier_from_field(tier_value: Optional[str]) -> Optional[ProtectionTier]:
    """Get protection tier from a stored field value (SurrealDB backend).

    Unlike get_entity_tier() which parses observations strings, this reads
    the protection_tier directly from a dedicated database field.
    """
    if tier_value is None:
        return None
    try:
        return ProtectionTier(tier_value)
    except ValueError:
        return None


def validate_write_access(
    tier: Optional[ProtectionTier],
    caller_role: str,
    change_approved: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Check if a write operation is allowed given the entity's tier and caller's role.

    Returns (allowed, reason_if_denied).
    """
    if tier is None:
        return True, None

    if tier == ProtectionTier.VISION:
        if caller_role == "human":
            return True, None
        return False, "Vision-tier entities are immutable by agents. Only humans can modify vision standards."

    if tier == ProtectionTier.ARCHITECTURE:
        if caller_role == "human":
            return True, None
        if change_approved:
            return True, None
        return False, "Architecture-tier entities require human-approved changes. Submit a change_proposal first."

    # Quality tier — freely writable
    return True, None
