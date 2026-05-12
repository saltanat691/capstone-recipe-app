"""
Script to check LLM and LangSmith configuration.
"""

from app.core.llm_config import check_llm_configuration, get_langsmith_url
from app.core.config import settings


def check_configuration():
    """
    Check and display LLM configuration status.
    """
    print("Recipe AI System - LLM Configuration Check")
    print("=" * 60)

    # Check overall configuration
    print("\nConfiguration Status:")
    print("-" * 60)

    status = check_llm_configuration()

    providers = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "langsmith": "LangSmith",
    }

    for key, name in providers.items():
        icon = "✓" if status[key] else "✗"
        status_text = "Configured" if status[key] else "Not configured"
        print(f"{icon} {name}: {status_text}")

    # LangSmith details
    print("\n" + "-" * 60)
    print("LangSmith Configuration:")
    print(f"  Tracing enabled: {settings.LANGSMITH_TRACING}")
    print(f"  Project: {settings.LANGSMITH_PROJECT}")
    print(f"  Endpoint: {settings.LANGSMITH_ENDPOINT}")

    if status["langsmith"]:
        print(f"  Dashboard: {get_langsmith_url()}")
    else:
        print("  API key not configured")

    # API Keys status (without showing the keys)
    print("\n" + "-" * 60)
    print("API Keys:")

    if settings.OPENAI_API_KEY:
        key_preview = f"{settings.OPENAI_API_KEY[:7]}...{settings.OPENAI_API_KEY[-4:]}"
        print(f"  OpenAI: {key_preview}")
    else:
        print("  OpenAI: Not set")

    if settings.ANTHROPIC_API_KEY:
        key_preview = f"{settings.ANTHROPIC_API_KEY[:7]}...{settings.ANTHROPIC_API_KEY[-4:]}"
        print(f"  Anthropic: {key_preview}")
    else:
        print("  Anthropic: Not set")

    if settings.LANGSMITH_API_KEY:
        key_preview = f"{settings.LANGSMITH_API_KEY[:7]}...{settings.LANGSMITH_API_KEY[-4:]}"
        print(f"  LangSmith: {key_preview}")
    else:
        print("  LangSmith: Not set")

    # Recommendations
    print("\n" + "=" * 60)
    print("Recommendations:")

    if not status["openai"] and not status["anthropic"]:
        print("⚠️  No LLM provider configured. Add OPENAI_API_KEY or ANTHROPIC_API_KEY")
        print("   Get OpenAI key: https://platform.openai.com/api-keys")
        print("   Get Anthropic key: https://console.anthropic.com/")

    if not status["langsmith"]:
        print("⚠️  LangSmith not configured for LLM observability")
        print("   Get API key: https://smith.langchain.com → Settings → API Keys")
        print("   Set LANGSMITH_API_KEY in .env")
    else:
        print("✓ LangSmith is ready for LLM tracing!")

    if not settings.LANGSMITH_TRACING:
        print("ℹ️  LangSmith tracing is disabled (LANGSMITH_TRACING=false)")

    print("\nFor more information, see LANGSMITH.md")


if __name__ == "__main__":
    check_configuration()