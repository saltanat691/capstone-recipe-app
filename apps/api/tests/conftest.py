"""
Shared pytest configuration.

- Loads apps/api/.env so tests see the same environment as the running app
  (OPENAI_API_KEY, DATABASE_URL, etc.). Real shell env vars take precedence.
- Registers the `integration` marker (used by tests that hit external services
  like OpenAI or the live Postgres database).
- Provides a skip helper for tests that require OPENAI_API_KEY.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure DATABASE_URL is always set so Settings() doesn't fail during
# collection in environments without a .env file (CI, remote containers).
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

# Load env files before tests collect, so module-level imports that read
# settings see the values. Root .env is primary (monorepo-wide); the
# legacy apps/api/.env is loaded second with override=True so local
# values can shadow root.
_THIS_FILE = Path(__file__).resolve()
_ROOT_ENV = _THIS_FILE.parents[3] / ".env"
_LOCAL_ENV = _THIS_FILE.parents[1] / ".env"
load_dotenv(_ROOT_ENV, override=False)
load_dotenv(_LOCAL_ENV, override=True)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require external services (OpenAI, Postgres).",
    )


@pytest.fixture
def require_openai_key() -> None:
    """Skip the test if OPENAI_API_KEY is not configured."""
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set; skipping integration test.")
