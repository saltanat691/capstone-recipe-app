"""
Basic RAG recipe retrieval using OpenAI embeddings + pgvector similarity.

Pipeline:
    query -> embed -> pgvector cosine search -> Python re-ranking -> RetrievedRecipe[]

Hard filters (applied in SQL or Python before scoring):
    - meal_type (SQL equality)
    - max_cooking_time_minutes (SQL: recipes.total_time <= N)
    - excluded_ingredients (Python: drop if any match)
    - dietary_restrictions (Python: drop only if a recipe ingredient matches
      a blocklist for that restriction — permissive by default; downstream
      safety agents should perform deeper validation)

Soft signals (added to score after vector similarity):
    - cuisine match bonus
    - available-ingredient overlap bonus

If filtering drops all candidates but the vector search did return rows,
the service falls back to similarity-only ranking (still honoring
excluded_ingredients) so it never serves an empty result for a populated DB.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.recipe import Recipe
from app.observability import get_logger

logger = get_logger(__name__)


class RecipeSearchFilters(BaseModel):
    """Filters and signals for RAG retrieval."""

    dietary_restrictions: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    cuisine_preferences: list[str] = Field(default_factory=list)
    available_ingredients: list[str] = Field(default_factory=list)
    max_cooking_time_minutes: Optional[int] = None
    meal_type: Optional[str] = None


class RetrievedRecipe(BaseModel):
    """A single recipe returned from the RAG pipeline."""

    id: int
    name: str
    cuisine: Optional[str] = None
    ingredients: list[str] = Field(default_factory=list)
    instructions: Optional[list[str]] = None
    score: float
    match_reason: str


# Score weights — tuned for cosine similarity in [0, 1].
_CUISINE_BONUS = 0.20
_INGREDIENT_OVERLAP_BONUS = 0.05  # per matched ingredient
_CANDIDATE_MULTIPLIER = 4  # fetch 4x `limit` candidates for re-ranking


async def retrieve_recipes(
    query: str,
    filters: RecipeSearchFilters,
    limit: int = 5,
) -> list[RetrievedRecipe]:
    """
    Embed `query`, fetch top-N similar recipes from pgvector, then re-rank in
    Python using `filters`. Returns up to `limit` RetrievedRecipe objects
    sorted by descending score.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")

    query_embedding = await _embed_query(query)

    logger.info(
        "RAG retrieval starting",
        extra={
            "query": query,
            "query_len": len(query),
            "filters": filters.model_dump(),
            "sql_conditions": _describe_sql_conditions(filters),
            "limit": limit,
        },
    )

    async with AsyncSessionLocal() as session:
        candidates = await _fetch_candidates(
            session,
            query_embedding,
            meal_type=filters.meal_type,
            max_cooking_time_minutes=filters.max_cooking_time_minutes,
            limit=limit * _CANDIDATE_MULTIPLIER,
        )

    logger.info(
        "RAG vector search complete",
        extra={"candidates_before_filter": len(candidates)},
    )

    excluded_lower = _lower_set(filters.excluded_ingredients)
    cuisine_pref_lower = _lower_set(filters.cuisine_preferences)
    diet_keys = {_normalize_tag(r) for r in filters.dietary_restrictions if r.strip()}
    available_lower = _lower_set(filters.available_ingredients)

    scored: list[RetrievedRecipe] = []
    dropped_excluded = 0
    dropped_diet = 0
    for recipe, distance in candidates:
        ingredient_names = [ing.name for ing in recipe.ingredients]
        ingredient_names_lower = {n.lower() for n in ingredient_names}

        # Hard filter: explicit excluded ingredients.
        if excluded_lower and _has_excluded(ingredient_names_lower, excluded_lower):
            dropped_excluded += 1
            continue

        # Hard filter: dietary restrictions — exclude only on positive evidence
        # of a violating ingredient. Recipes without explicit diet tags are
        # allowed through if no blocklist ingredient is detected.
        if diet_keys and _violates_diet(ingredient_names_lower, diet_keys):
            dropped_diet += 1
            continue

        similarity = 1.0 - float(distance)
        score = similarity
        reasons = [f"similarity={similarity:.3f}"]

        if cuisine_pref_lower and recipe.cuisine and recipe.cuisine.lower() in cuisine_pref_lower:
            score += _CUISINE_BONUS
            reasons.append("cuisine_match")

        if available_lower:
            overlap = _count_overlap(ingredient_names_lower, available_lower)
            if overlap > 0:
                score += _INGREDIENT_OVERLAP_BONUS * overlap
                reasons.append(f"ingredient_overlap={overlap}")

        scored.append(
            RetrievedRecipe(
                id=recipe.id,
                name=recipe.name,
                cuisine=recipe.cuisine,
                ingredients=ingredient_names,
                instructions=_normalize_instructions(recipe.instructions),
                score=round(score, 4),
                match_reason=", ".join(reasons),
            )
        )

    logger.info(
        "RAG Python filtering complete",
        extra={
            "candidates_before_filter": len(candidates),
            "dropped_excluded_ingredients": dropped_excluded,
            "dropped_dietary_restriction": dropped_diet,
            "kept_after_filter": len(scored),
        },
    )

    # Fallback: if filtering removed everything but the vector search did
    # find candidates, return the top similarity-ranked candidates so we
    # never serve an empty list when the DB has relevant data. Still
    # respects explicit excluded_ingredients (safety) but bypasses the
    # dietary filter, which may have been too strict.
    if not scored and candidates:
        logger.warning(
            "RAG fallback engaged: returning top similarity candidates "
            "without re-ranking filters"
        )
        for recipe, distance in candidates:
            ingredient_names = [ing.name for ing in recipe.ingredients]
            ingredient_names_lower = {n.lower() for n in ingredient_names}
            if excluded_lower and _has_excluded(ingredient_names_lower, excluded_lower):
                continue
            similarity = 1.0 - float(distance)
            scored.append(
                RetrievedRecipe(
                    id=recipe.id,
                    name=recipe.name,
                    cuisine=recipe.cuisine,
                    ingredients=ingredient_names,
                    instructions=_normalize_instructions(recipe.instructions),
                    score=round(similarity, 4),
                    match_reason=f"fallback_similarity={similarity:.3f}",
                )
            )

    scored.sort(key=lambda r: r.score, reverse=True)
    top = scored[:limit]

    logger.info(
        "RAG retrieval complete",
        extra={
            "query_len": len(query),
            "candidates": len(candidates),
            "kept": len(scored),
            "returned": len(top),
        },
    )
    return top


async def _embed_query(query: str) -> list[float]:
    # TODO: optional Redis cache — key = SHA-256(query), TTL ~24 h; skip the
    # OpenAI call on a hit and store the returned embedding on a miss.  Use a
    # connection pool (e.g. redis.asyncio) configured via settings.REDIS_URL so
    # the cache is a no-op when REDIS_URL is unset.
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set; rag_recipe_service cannot embed the query."
        )

    try:
        from openai import AsyncOpenAI
    except ImportError as e:
        raise RuntimeError(
            "openai package not installed; run `pip install -r requirements.txt`."
        ) from e

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    resp = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[query],
    )
    return resp.data[0].embedding


async def _fetch_candidates(
    session,
    query_embedding: list[float],
    *,
    meal_type: Optional[str],
    max_cooking_time_minutes: Optional[int],
    limit: int,
) -> list[tuple[Recipe, float]]:
    distance_expr = Recipe.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(Recipe, distance_expr)
        .where(Recipe.embedding.is_not(None))
        .options(selectinload(Recipe.ingredients))
        .order_by(distance_expr)
        .limit(limit)
    )
    if meal_type:
        stmt = stmt.where(Recipe.meal_type == meal_type)
    if max_cooking_time_minutes is not None:
        stmt = stmt.where(Recipe.total_time <= max_cooking_time_minutes)

    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


def _lower_set(values: list[str]) -> set[str]:
    return {v.strip().lower() for v in values if v and v.strip()}


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace("-", "_").replace(" ", "_")


def _has_excluded(ingredient_names_lower: set[str], excluded_lower: set[str]) -> bool:
    for ex in excluded_lower:
        for name in ingredient_names_lower:
            if ex in name or name in ex:
                return True
    return False


# Map normalized dietary-restriction keys to ingredient keywords that imply
# a violation. Recipes whose ingredient names contain any of these keywords
# are excluded for that restriction. Unknown restrictions are not enforced
# at the retrieval layer (a downstream safety agent should validate).
_DIET_INGREDIENT_BLOCKLIST: dict[str, set[str]] = {
    "no_pork": {"pork", "bacon", "ham", "prosciutto", "pancetta"},
    "halal": {"pork", "bacon", "ham", "prosciutto", "pancetta", "alcohol", "wine", "beer"},
    "kosher": {"pork", "bacon", "ham", "shellfish", "shrimp", "lobster", "crab"},
    "no_beef": {"beef", "steak"},
    "no_alcohol": {"alcohol", "wine", "beer", "rum", "vodka"},
    "vegetarian": {
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "fish",
        "salmon", "tuna", "shrimp", "bacon", "ham", "meat",
    },
    "vegan": {
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "fish",
        "salmon", "tuna", "shrimp", "bacon", "ham", "meat",
        "milk", "cheese", "butter", "cream", "yogurt", "egg", "honey",
    },
    "gluten_free": {"wheat", "flour", "bread", "pasta", "noodle"},
    "dairy_free": {"milk", "cheese", "butter", "cream", "yogurt"},
}


def _violates_diet(ingredient_names_lower: set[str], required_keys: set[str]) -> bool:
    """
    Return True only when a recipe ingredient clearly violates one of the
    requested restrictions. Unknown restriction keys are ignored (permissive
    by design — see module docstring).
    """
    for restriction in required_keys:
        blocklist = _DIET_INGREDIENT_BLOCKLIST.get(restriction)
        if not blocklist:
            continue
        for blocked in blocklist:
            for name in ingredient_names_lower:
                if blocked in name:
                    return True
    return False


def _describe_sql_conditions(filters: RecipeSearchFilters) -> dict[str, Any]:
    """Human-readable summary of which WHERE clauses were added to the query."""
    conditions: dict[str, Any] = {"embedding_not_null": True}
    if filters.meal_type:
        conditions["meal_type_eq"] = filters.meal_type
    if filters.max_cooking_time_minutes is not None:
        conditions["total_time_lte"] = filters.max_cooking_time_minutes
    return conditions


def _count_overlap(ingredient_names_lower: set[str], available_lower: set[str]) -> int:
    matched = 0
    for avail in available_lower:
        for name in ingredient_names_lower:
            if avail in name or name in avail:
                matched += 1
                break
    return matched


def _normalize_instructions(raw: Any) -> Optional[list[str]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        steps = [str(s).strip() for s in raw if str(s).strip()]
        return steps or None
    if isinstance(raw, dict):
        steps_field = raw.get("steps")
        if isinstance(steps_field, list):
            steps = [str(s).strip() for s in steps_field if str(s).strip()]
            return steps or None
        return None
    text = str(raw).strip()
    return [text] if text else None