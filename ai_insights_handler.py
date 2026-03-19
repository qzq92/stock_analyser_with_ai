"""AI-powered stock insights via OpenAI-compatible API (e.g. Perplexity)."""

import asyncio
import json
from collections.abc import Iterator
from typing import Any

from agent.stock_analysis_agent import create_stock_analysis_agent
from pydantic import BaseModel, Field
from prompts.analyst_prompt import ANALYST_PROMPT_TEMPLATE

INVALID_API_KEY_RESPONSE = "Sorry, I am unable to provide response due to invalid API key"


class StructuredResponse(BaseModel):
    """Structured LLM payload with plain-text answer and citation URLs."""

    answer: str = ""
    citations: list[str] = Field(default_factory=list)


class AIInsights:
    """Generates stock analysis and suggestions using the configured stock agent."""

    def __init__(self) -> None:
        """Initialize the stock analysis agent from environment-based config."""
        self.analysis_agent = create_stock_analysis_agent()
        self._latest_response = StructuredResponse()

    def get_ai_insights_stream(self, stock: str, market: str) -> Iterator[str]:
        """Stream LLM output chunks for the given stock and market prompt.

        Args:
            stock: Stock ticker symbol.
            market: Exchange identifier (e.g. 'NASDAQ', 'SINGAPORE').

        Yields:
            Incremental text chunks from the model response stream.
        """
        prompt = self._build_prompt(stock, market)
        self._latest_response = StructuredResponse()
        loop = asyncio.new_event_loop()
        iterator = self._astream_answer(prompt)
        try:
            while True:
                try:
                    chunk = loop.run_until_complete(iterator.__anext__())
                except StopAsyncIteration:
                    break
                yield chunk
        finally:
            loop.run_until_complete(iterator.aclose())
            loop.close()

    def get_latest_response(self) -> StructuredResponse:
        """Structured result populated after streaming completes."""
        return self._latest_response

    async def _astream_answer(self, prompt: str) -> Any:
        """Stream only the answer field from a JSON response via astream_events."""
        raw_buffer = ""
        streamed_answer = ""

        try:
            async for event in self.analysis_agent.astream_events(prompt, version="v2"):
                print(f"Event: {event}")
                if event.get("event") != "on_chat_model_stream":
                    continue

                chunk = event.get("data", {}).get("chunk")
                print(f"Chunk: {chunk}")
                chunk_text = self._chunk_to_text(chunk)
                if not chunk_text:
                    continue

                raw_buffer += chunk_text
                current_answer = self._extract_partial_answer(raw_buffer)
                if current_answer is None:
                    continue

                new_text = current_answer[len(streamed_answer):]
                if new_text:
                    streamed_answer = current_answer
                    yield new_text

            self._latest_response = self._parse_structured_response(
                raw_buffer,
                fallback_answer=streamed_answer,
            )
        except Exception as exc:
            if self._is_invalid_api_key_error(exc):
                self._latest_response = StructuredResponse(
                    answer=INVALID_API_KEY_RESPONSE,
                    citations=[],
                )
                yield INVALID_API_KEY_RESPONSE
                return
            raise

    def _chunk_to_text(self, chunk: Any) -> str:
        """Extract streamed text from a LangChain chunk object."""
        if chunk is None:
            return ""

        chunk_text = chunk.content if hasattr(chunk, "content") else str(chunk)
        if isinstance(chunk_text, str):
            return chunk_text
        if isinstance(chunk_text, list):
            return "".join(part for part in chunk_text if isinstance(part, str))
        return ""

    def _extract_partial_answer(self, raw_buffer: str) -> str | None:
        """Extract the current value of the JSON answer field from a partial buffer."""
        key_index = raw_buffer.find('"answer"')
        if key_index == -1:
            return None

        colon_index = raw_buffer.find(":", key_index)
        if colon_index == -1:
            return None

        quote_index = raw_buffer.find('"', colon_index)
        if quote_index == -1:
            return None

        answer_chars: list[str] = []
        index = quote_index + 1
        while index < len(raw_buffer):
            char = raw_buffer[index]
            if char == "\\":
                if index + 1 >= len(raw_buffer):
                    break
                escaped = raw_buffer[index + 1]
                if escaped == "u":
                    if index + 5 >= len(raw_buffer):
                        break
                    unicode_text = raw_buffer[index + 2:index + 6]
                    try:
                        answer_chars.append(chr(int(unicode_text, 16)))
                    except ValueError:
                        break
                    index += 6
                    continue

                escape_map = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                answer_chars.append(escape_map.get(escaped, escaped))
                index += 2
                continue

            if char == '"':
                return "".join(answer_chars)

            answer_chars.append(char)
            index += 1

        return "".join(answer_chars)

    def _parse_structured_response(
        self,
        raw_text: str,
        fallback_answer: str = "",
    ) -> StructuredResponse:
        """Parse the model response into answer/citations JSON."""
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
            if cleaned_text.startswith("json"):
                cleaned_text = cleaned_text[4:].strip()

        if "{" in cleaned_text and "}" in cleaned_text:
            cleaned_text = cleaned_text[cleaned_text.find("{"):cleaned_text.rfind("}") + 1]

        try:
            payload = json.loads(cleaned_text)
        except json.JSONDecodeError:
            return StructuredResponse(
                answer=fallback_answer or raw_text.strip(),
                citations=[],
            )

        answer = payload.get("answer")
        citations = payload.get("citations")
        return StructuredResponse(
            answer=answer if isinstance(answer, str) else fallback_answer,
            citations=self._normalize_citations(citations),
        )

    def _normalize_citations(self, citations: Any) -> list[str]:
        """Normalize citation list to deduplicated URL strings."""
        if not isinstance(citations, list):
            return []

        normalized: list[str] = []
        seen_urls: set[str] = set()
        for item in citations:
            if not isinstance(item, str):
                continue
            url = item.strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            normalized.append(url)
        return normalized

    def _build_prompt(self, stock: str, market: str) -> str:
        """Build the stock analysis prompt for the model."""
        return ANALYST_PROMPT_TEMPLATE.format(stock=stock, market=market)

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