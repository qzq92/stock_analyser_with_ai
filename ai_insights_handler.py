"""AI-powered stock insights via OpenAI-compatible API (e.g. Perplexity)."""

from collections.abc import Iterator
from typing import Any
from langchain.chat_models import init_chat_model

from llm_config import (
    MODEL,
    MODEL_PROVIDER,
    PERPLEXITY_OPENAI_BASE_URL,
    SUPPORTED_PERPLEXITY_MODELS,
)

INVALID_API_KEY_RESPONSE = "Sorry, I am unable to provide response due to invalid API key"
Source = dict[str, str]


class AIInsights:
    """Generates stock analysis and suggestions using an LLM via Perplexity base URL."""

    def __init__(self, api_key: str) -> None:
        """Initialize the LLM client with API key.

        Args:
            api_key: API key for the OpenAI-compatible endpoint (e.g. Perplexity).
        """
        if MODEL not in SUPPORTED_PERPLEXITY_MODELS:
            supported_models = ", ".join(SUPPORTED_PERPLEXITY_MODELS)
            raise ValueError(
                f"Unsupported model '{MODEL}' for Perplexity endpoint. "
                f"Supported models: {supported_models}"
            )

        self.model = init_chat_model(
            model=MODEL,
            model_provider=MODEL_PROVIDER,
            api_key=api_key,
            base_url=PERPLEXITY_OPENAI_BASE_URL,
            temperature=0,
        )
        self._latest_sources: list[Source] = []

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
        self._latest_sources = []

        try:
            for chunk in self.model.stream(prompt):
                chunk_sources = self._extract_sources_from_obj(chunk)
                if chunk_sources:
                    self._latest_sources = chunk_sources
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

    def get_latest_sources(self, stock: str, market: str) -> list[Source]:
        """Return latest sources, or fetch once via non-streaming fallback."""
        if self._latest_sources:
            return self._latest_sources

        prompt = self._build_prompt(stock, market)
        try:
            response = self.model.invoke(prompt)
        except Exception as exc:
            if self._is_invalid_api_key_error(exc):
                return []
            raise

        self._latest_sources = self._extract_sources_from_obj(response)
        return self._latest_sources

    def _extract_sources_from_obj(self, obj: Any) -> list[Source]:
        """Extract and normalize citation/search-result metadata from responses/chunks."""
        search_results = self._safe_get(obj, "search_results")
        citations = self._safe_get(obj, "citations")
        response_metadata = self._safe_get(obj, "response_metadata")
        additional_kwargs = self._safe_get(obj, "additional_kwargs")

        if isinstance(response_metadata, dict):
            search_results = search_results or response_metadata.get("search_results")
            citations = citations or response_metadata.get("citations")

        if isinstance(additional_kwargs, dict):
            search_results = search_results or additional_kwargs.get("search_results")
            citations = citations or additional_kwargs.get("citations")

        return self._normalize_sources(search_results, citations)

    def _normalize_sources(self, search_results: Any, citations: Any) -> list[Source]:
        """Normalize raw metadata to ordered, deduplicated source objects."""
        ordered_sources: list[Source] = []
        seen_urls: set[str] = set()

        if isinstance(search_results, list):
            for item in search_results:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                title = item.get("title")
                display_title = title if isinstance(title, str) and title else url
                seen_urls.add(url)
                ordered_sources.append({"title": display_title, "url": url})

        if isinstance(citations, list):
            for item in citations:
                if isinstance(item, str):
                    url = item
                    title = item
                elif isinstance(item, dict):
                    url = item.get("url")
                    title = item.get("title") or url
                else:
                    continue

                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                ordered_sources.append({"title": str(title), "url": url})

        indexed_sources: list[Source] = []
        for idx, source in enumerate(ordered_sources, start=1):
            indexed_sources.append(
                {
                    "index": str(idx),
                    "title": source["title"],
                    "url": source["url"],
                }
            )
        return indexed_sources

    def _safe_get(self, obj: Any, field: str) -> Any:
        """Safely fetch an attribute from SDK/model objects."""
        try:
            return getattr(obj, field, None)
        except Exception:
            return None

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