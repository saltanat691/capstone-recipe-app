"""
Cuisine diversity checker for recommendation results.

A small or geographically skewed recipe database naturally produces
recommendations concentrated in one or two cuisines.  This module detects
that concentration and surfaces a warning so the caller can pass it through
to the API response, alerting users and operators alike.

Threshold: if a single cuisine accounts for ≥ 60 % of the returned
recommendations the result set is considered skewed.
"""

from app.observability import get_logger
from app.observability.metrics import record_diversity_warning

logger = get_logger(__name__)

_SKEW_THRESHOLD = 0.60  # fraction of results from one cuisine to trigger warning


def cuisine_diversity_warning(
    cuisines: list[str | None],
) -> str | None:
    """
    Return a warning string if one cuisine dominates *cuisines*, else None.

    Args:
        cuisines: Cuisine label per recommendation (None = unknown).
    """
    if not cuisines:
        return None

    counts: dict[str, int] = {}
    for c in cuisines:
        label = (c or "unknown").strip().lower()
        counts[label] = counts.get(label, 0) + 1

    dominant = max(counts, key=lambda k: counts[k])
    fraction = counts[dominant] / len(cuisines)

    if fraction >= _SKEW_THRESHOLD:
        logger.info(
            "cuisine_skew_detected",
            extra={
                "dominant_cuisine": dominant,
                "fraction": round(fraction, 2),
                "total": len(cuisines),
            },
        )
        record_diversity_warning(dominant)
        return (
            f"Recommendations are weighted toward '{dominant}' cuisine "
            f"({counts[dominant]}/{len(cuisines)} results). "
            "Your recipe database may benefit from more diverse cuisine coverage."
        )

    return None
