"""AI-powered stock insights via OpenAI-compatible API (e.g. Perplexity)."""

from collections.abc import Iterator
from langchain.chat_models import init_chat_model

from llm_config import (
    DEFAULT_OPENAI_MODEL_KEY,
    OPENAI_MODELS,
    PERPLEXITY_OPENAI_BASE_URL,
)

INVALID_API_KEY_RESPONSE = "Sorry, I am unable to provide response due to invalid API key"


class AIInsights:
    """Generates stock analysis and suggestions using an LLM via Perplexity base URL."""

    def __init__(self, api_key: str, model_key: str = DEFAULT_OPENAI_MODEL_KEY) -> None:
        """Initialize the LLM client with API key and model from config.

        Args:
            api_key: API key for the OpenAI-compatible endpoint (e.g. Perplexity).
            model_key: Key into OPENAI_MODELS in llm_config (e.g. 'fast', 'balanced', 'quality').

        Raises:
            ValueError: If model_key is not present in OPENAI_MODELS.
        """
        if model_key not in OPENAI_MODELS:
            valid_keys = ", ".join(sorted(OPENAI_MODELS.keys()))
            raise ValueError(f"Invalid model_key '{model_key}'. Choose one of: {valid_keys}")

        model_name = OPENAI_MODELS[model_key]
        self.model = init_chat_model(
            model=model_name,
            model_provider="openai",
            api_key=api_key,
            base_url=PERPLEXITY_OPENAI_BASE_URL,
            temperature=0,
        )

    def get_ai_insights(self, image_path: str, stock: str, market: str) -> str:
        """Request LLM analysis and a buy/skip suggestion for the given stock and market.

        Args:
            image_path: Path to the chart image (currently used for context only).
            stock: Stock ticker symbol.
            market: Exchange identifier (e.g. 'NASDAQ', 'SINGAPORE').

        Returns:
            The model's analysis and recommendation as a string.
        """
        prompt = self._build_prompt(stock, market)
        try:
            response = self.model.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            if self._is_invalid_api_key_error(exc):
                return INVALID_API_KEY_RESPONSE
            raise

    def get_ai_insights_stream(
        self, image_path: str, stock: str, market: str
    ) -> Iterator[str]:
        """Stream LLM output chunks for the given stock and market prompt.

        Args:
            image_path: Path to the chart image (currently used for context only).
            stock: Stock ticker symbol.
            market: Exchange identifier (e.g. 'NASDAQ', 'SINGAPORE').

        Yields:
            Incremental text chunks from the model response stream.
        """
        prompt = self._build_prompt(stock, market)

        try:
            for chunk in self.model.stream(prompt):
                chunk_text = chunk.content if hasattr(chunk, "content") else str(chunk)
                if isinstance(chunk_text, str):
                    if chunk_text:
                        yield chunk_text
                elif isinstance(chunk_text, list):
                    for part in chunk_text:
                        if isinstance(part, str) and part:
                            yield part
        except Exception as exc:
            if self._is_invalid_api_key_error(exc):
                yield INVALID_API_KEY_RESPONSE
                return
            raise

    def _build_prompt(self, stock: str, market: str) -> str:
        """Build the stock analysis prompt for the model."""
        return (
            f"This is a description of stock performance for stock '{stock}' over the last "
            f"100 days on market '{market}'. On the basis of volume traded, closing prices, "
            f"and 7- and 20-day moving averages, provide some analysis and a suggestion "
            f"about this stock. Should this stock be purchased or not?"
        )

    def _is_invalid_api_key_error(self, exc: Exception) -> bool:
        """Check whether an exception indicates invalid API-key authentication."""
        message = str(exc).lower()
        auth_error_tokens = [
            "invalid api key",
            "incorrect api key",
            "authentication",
            "unauthorized",
            "401",
        ]
        return any(token in message for token in auth_error_tokens)