"""LLM configuration: Perplexity base URL and OpenAI model keys for ai_insights_handler."""

from typing import Final

PERPLEXITY_OPENAI_BASE_URL: Final[str] = "https://api.perplexity.ai"

# Map friendly keys to OpenAI model IDs routed through Perplexity's OpenAI-compatible API.
# Edit these model IDs as needed.
OPENAI_MODELS: Final[dict[str, str]] = {
    "fast": "gpt-5.1-mini",
    "balanced": "gpt-5.1-mini",
    "quality": "gpt-5.1",
}

DEFAULT_OPENAI_MODEL_KEY: Final[str] = "balanced"
