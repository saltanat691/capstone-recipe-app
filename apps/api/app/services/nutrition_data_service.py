"""
Thin async client for the USDA FoodData Central API.

Not yet wired into the agent graph — call sites can use this to look up
authoritative per-100g nutrient values to ground the LLM's nutrition
estimates. Optional: when USDA_API_KEY is unset, methods raise
RuntimeError so callers can decide whether to fall back.
"""

from typing import Any, Optional

import httpx

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)


class USDAConfigError(RuntimeError):
    """Raised when USDA_API_KEY is not configured."""


class USDAApiError(RuntimeError):
    """Raised when the USDA API returns an error or unexpected payload."""


_DEFAULT_TIMEOUT_S = 10.0


class NutritionDataService:
    """
    Async wrapper around USDA FoodData Central.

    Construct once per request scope; the underlying httpx.AsyncClient is
    created lazily and closed via `aclose()` or `async with`.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.USDA_API_KEY
        self._base_url = (base_url or settings.USDA_API_BASE_URL).rstrip("/")
        self._timeout_s = timeout_s
        self._client: Optional[httpx.AsyncClient] = None

    # ---- lifecycle -----------------------------------------------------

    async def __aenter__(self) -> "NutritionDataService":
        self._ensure_configured()
        self._client = httpx.AsyncClient(timeout=self._timeout_s)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- public methods ------------------------------------------------

    async def search_food(
        self, query: str, *, page_size: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search for foods by free-text query. Returns a (possibly empty) list
        of result dicts (`fdcId`, `description`, `dataType`, `foodCategory`,
        etc.) — the USDA payload's `foods` array, trimmed to `page_size`.
        """
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        params = {
            "api_key": self._key(),
            "query": query.strip(),
            "pageSize": page_size,
        }
        data = await self._get("/foods/search", params=params)
        foods = data.get("foods")
        if not isinstance(foods, list):
            raise USDAApiError(
                f"Unexpected USDA payload for search; missing 'foods' list: {data!r}"
            )
        return foods

    async def get_food_details(self, fdc_id: str) -> dict[str, Any]:
        """
        Fetch the full food record for an `fdcId`. Returns the raw USDA dict
        (`description`, `foodNutrients`, `foodPortions`, ...).
        """
        fdc_id_clean = str(fdc_id).strip()
        if not fdc_id_clean:
            raise ValueError("fdc_id must be a non-empty string")

        params = {"api_key": self._key()}
        return await self._get(f"/food/{fdc_id_clean}", params=params)

    # ---- internals -----------------------------------------------------

    def _key(self) -> str:
        self._ensure_configured()
        return self._api_key

    def _ensure_configured(self) -> None:
        if not self._api_key:
            raise USDAConfigError(
                "USDA_API_KEY is not set. USDA integration is optional; set "
                "USDA_API_KEY in apps/api/.env to enable it. Get a free key "
                "at https://fdc.nal.usda.gov/api-key-signup.html."
            )

    async def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        client = self._client or httpx.AsyncClient(timeout=self._timeout_s)
        own_client = self._client is None
        try:
            try:
                response = await client.get(url, params=params)
            except httpx.HTTPError as e:
                raise USDAApiError(f"USDA request failed: {e}") from e

            if response.status_code == 401 or response.status_code == 403:
                raise USDAConfigError(
                    f"USDA rejected the API key ({response.status_code}). "
                    "Verify USDA_API_KEY."
                )
            if response.status_code >= 400:
                raise USDAApiError(
                    f"USDA returned {response.status_code}: {response.text[:200]}"
                )

            try:
                return response.json()
            except ValueError as e:
                raise USDAApiError(f"USDA returned non-JSON: {e}") from e
        finally:
            if own_client:
                await client.aclose()


# ---- convenience functions -------------------------------------------------


async def search_food(query: str, *, page_size: int = 5) -> list[dict[str, Any]]:
    """One-shot search; opens and closes its own httpx client."""
    async with NutritionDataService() as svc:
        return await svc.search_food(query, page_size=page_size)


async def get_food_details(fdc_id: str) -> dict[str, Any]:
    """One-shot detail lookup; opens and closes its own httpx client."""
    async with NutritionDataService() as svc:
        return await svc.get_food_details(fdc_id)