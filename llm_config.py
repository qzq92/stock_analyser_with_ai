"""LLM configuration: Perplexity base URL and model settings."""

from typing import Final

PERPLEXITY_OPENAI_BASE_URL: Final[str] = "https://api.perplexity.ai"
MODEL: Final[str] = "sonar-pro"
MODEL_PROVIDER: Final[str] = "openai"
SUPPORTED_PERPLEXITY_MODELS: Final[tuple[str, ...]] = ("sonar", "sonar-pro")
