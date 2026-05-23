"""
API key management and user data endpoints.

POST  /auth/api-keys         — create a key (returns plaintext once)
DELETE /users/me/data        — GDPR erasure of all data for the calling key's owner
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import generate_api_key, hash_key, require_api_key
from app.db.session import get_db
from app.models.agent_run import AgentRun
from app.models.api_key import ApiKey
from app.models.user_preference import UserPreference
from app.observability import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Auth"])


# ---- Request / Response schemas ----------------------------------------


class CreateApiKeyRequest(BaseModel):
    owner_id: str = Field(..., description="Email or username of the key owner")
    name: str = Field(..., description="Friendly label for this key")
    tracing_consent: bool = Field(
        default=True,
        description=(
            "Whether LLM calls may be traced to LangSmith. "
            "Set false to opt out of external tracing."
        ),
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=3650,
        description="Key lifetime in days. Omit for a non-expiring key.",
    )


class CreateApiKeyResponse(BaseModel):
    key: str = Field(..., description="Plaintext API key — shown only once, store it now.")
    owner_id: str
    name: str
    tracing_consent: bool
    expires_at: Optional[datetime]


class DeleteDataResponse(BaseModel):
    deleted_agent_runs: int
    deleted_user_preferences: int
    message: str


# ---- Endpoints ---------------------------------------------------------


@router.post(
    "/auth/api-keys",
    response_model=CreateApiKeyResponse,
    status_code=201,
    summary="Create API key",
    description=(
        "Generate a new API key. The plaintext key is returned **once** and "
        "never stored — save it immediately. Subsequent requests must supply "
        "the key in the X-API-Key header."
    ),
)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateApiKeyResponse:
    plaintext = generate_api_key()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        if body.expires_in_days
        else None
    )
    record = ApiKey(
        key_hash=hash_key(plaintext),
        owner_id=body.owner_id,
        name=body.name,
        tracing_consent=body.tracing_consent,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()

    logger.info(
        "api_key_created",
        extra={"owner_id": body.owner_id, "key_name": body.name},
    )
    return CreateApiKeyResponse(
        key=plaintext,
        owner_id=record.owner_id,
        name=record.name,
        tracing_consent=record.tracing_consent,
        expires_at=record.expires_at,
    )


@router.delete(
    "/users/me/data",
    response_model=DeleteDataResponse,
    summary="Delete all my data (GDPR erasure)",
    description=(
        "Permanently delete all agent runs and user preferences associated "
        "with the authenticated key's owner. The API key itself is also "
        "deactivated. This action cannot be undone."
    ),
)
async def delete_my_data(
    api_key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> DeleteDataResponse:
    owner_id = api_key.owner_id

    runs_result = await db.execute(
        delete(AgentRun)
        .where(AgentRun.user_id == owner_id)
        .returning(AgentRun.id)
    )
    deleted_runs = len(runs_result.fetchall())

    prefs_result = await db.execute(
        delete(UserPreference)
        .where(UserPreference.user_id == owner_id)
        .returning(UserPreference.id)
    )
    deleted_prefs = len(prefs_result.fetchall())

    # Deactivate all keys for this owner.
    await db.execute(
        delete(ApiKey).where(ApiKey.owner_id == owner_id)
    )

    logger.info(
        "gdpr_erasure",
        extra={
            "owner_id": owner_id,
            "deleted_runs": deleted_runs,
            "deleted_prefs": deleted_prefs,
        },
    )
    return DeleteDataResponse(
        deleted_agent_runs=deleted_runs,
        deleted_user_preferences=deleted_prefs,
        message=f"All data for owner '{owner_id}' has been permanently deleted.",
    )
