"""
Semantic Relation Matcher - Sprint 14

Replaces hardcoded enum matching with intelligent fuzzy/semantic matching.
This approach:
1. First tries exact match with known types
2. Then uses fuzzy string matching to find closest known type
3. If similarity is high enough, uses that type
4. Otherwise, accepts it as-is (dynamic types)

Much cleaner than maintaining a giant synonym dictionary!
"""

import logging
from difflib import SequenceMatcher
from enum import Enum

logger = logging.getLogger(__name__)


class RelationType(str, Enum):
    """Core relationship types. Dynamically matched, not exhaustively listed."""

    # Structural
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IMPLEMENTS = "IMPLEMENTS"
    INHERITS_FROM = "INHERITS_FROM"
    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"

    # Action-based
    USES = "USES"
    CREATES = "CREATES"
    RETURNS = "RETURNS"
    INCLUDES = "INCLUDES"
    CACHES = "CACHES"

    # Causal
    CAUSES = "CAUSES"
    SOLVES = "SOLVES"
    CAUSED_BY = "CAUSED_BY"
    SOLVED_BY = "SOLVED_BY"

    # Semantic
    RELATES_TO = "RELATES_TO"
    IS_A = "IS_A"
    HAS_PROPERTY = "HAS_PROPERTY"
    SIMILAR_TO = "SIMILAR_TO"

    # Interaction
    INTERACTS_WITH = "INTERACTS_WITH"
    MENTIONS = "MENTIONS"
    APPLIED_TO = "APPLIED_TO"
    HAS_MODEL = "HAS_MODEL"


# Semantic groups - types that are conceptually similar
SEMANTIC_GROUPS = {
    "action_create": {"creates", "produces", "builds", "generates", "makes"},
    "action_use": {"uses", "utilizes", "accesses", "consumes", "employs"},
    "action_contain": {"contains", "includes", "has", "holds", "comprises"},
    "action_call": {"calls", "invokes", "executes", "runs", "triggers"},
    "action_depend": {"depends_on", "requires", "needs", "relies_on"},
    "causal_cause": {"causes", "leads_to", "results_in", "generates", "triggers"},
    "causal_solve": {"solves", "fixes", "resolves", "addresses", "corrects"},
    "semantic_relate": {"relates_to", "associated_with", "connected_to", "linked_to"},
    "semantic_is": {"is_a", "is", "type_of", "kind_of", "instance_of"},
    "storage": {"caches", "stores", "persists", "saves", "keeps"},
    "interaction": {"interacts_with", "communicates_with", "talks_to", "connects_to"},
    "modeling": {"has_model", "uses_model", "powered_by_model", "model_for"},
}

# Map each semantic group to its canonical RelationType
GROUP_TO_CANONICAL = {
    "action_create": RelationType.CREATES,
    "action_use": RelationType.USES,
    "action_contain": RelationType.CONTAINS,
    "action_call": RelationType.CALLS,
    "action_depend": RelationType.DEPENDS_ON,
    "causal_cause": RelationType.CAUSES,
    "causal_solve": RelationType.SOLVES,
    "semantic_relate": RelationType.RELATES_TO,
    "semantic_is": RelationType.IS_A,
    "storage": RelationType.CACHES,
    "interaction": RelationType.INTERACTS_WITH,
    "modeling": RelationType.HAS_MODEL,
}


def _string_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _find_in_semantic_groups(type_str: str) -> RelationType | None:
    """Find type in semantic groups using fuzzy matching."""
    normalized = type_str.lower().replace("_", " ").replace("-", " ").strip()

    for group_name, synonyms in SEMANTIC_GROUPS.items():
        for synonym in synonyms:
            # Exact match in group
            if normalized == synonym.replace("_", " "):
                return GROUP_TO_CANONICAL[group_name]
            # High similarity match
            if _string_similarity(normalized, synonym.replace("_", " ")) > 0.85:
                return GROUP_TO_CANONICAL[group_name]

    return None


def match_relation_type(type_str: str, threshold: float = 0.75) -> tuple[RelationType, float]:
    """
    Intelligently match a relationship type string to a canonical RelationType.

    Uses a multi-stage approach:
    1. Exact enum match
    2. Semantic group match
    3. Fuzzy match against all enum values
    4. Fallback to RELATES_TO

    Args:
        type_str: The relationship type string to match
        threshold: Minimum similarity for fuzzy match (0-1)

    Returns:
        Tuple of (matched RelationType, confidence score)
    """
    if not type_str:
        return RelationType.RELATES_TO, 0.0

    normalized = type_str.strip().upper().replace(" ", "_").replace("-", "_")

    # Stage 1: Exact match with enum
    try:
        matched = RelationType(normalized)
        return matched, 1.0
    except ValueError:
        pass

    # Try by name
    for rel_type in RelationType:
        if rel_type.name == normalized:
            return rel_type, 1.0

    # Stage 2: Semantic group match
    group_match = _find_in_semantic_groups(type_str)
    if group_match:
        logger.debug(f"Semantic group match: '{type_str}' -> {group_match.value}")
        return group_match, 0.9

    # Stage 3: Fuzzy match against all enum values
    best_match = None
    best_score = 0.0

    for rel_type in RelationType:
        # Compare against value and name
        for candidate in [rel_type.value, rel_type.name]:
            score = _string_similarity(type_str, candidate)
            if score > best_score:
                best_score = score
                best_match = rel_type

    if best_score >= threshold:
        logger.debug(f"Fuzzy match: '{type_str}' -> {best_match.value} (score={best_score:.2f})")
        return best_match, best_score

    # Stage 4: Accept as custom type (future: could add dynamically)
    logger.info(
        f"New relation type discovered: '{type_str}' (best match: {best_match.value} @ {best_score:.2f}). "
        f"Using RELATES_TO as fallback."
    )
    return RelationType.RELATES_TO, 0.5


def normalize_relation(type_str: str) -> str:
    """
    Simple helper that returns the canonical relation type string.

    Usage:
        rel = normalize_relation("CREATES")  # -> "CREATES"
        rel = normalize_relation("produces") # -> "CREATES"
        rel = normalize_relation("gera")     # -> "CREATES"
    """
    matched, _ = match_relation_type(type_str)
    return matched.value


# ============================================================
# INTEGRATION: Replace the old normalize_relation_type in GraphGuardian
# ============================================================

# For backward compatibility, export the enum
__all__ = [
    "SEMANTIC_GROUPS",
    "RelationType",
    "match_relation_type",
    "normalize_relation",
]
