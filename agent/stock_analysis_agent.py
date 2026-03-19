"""Configured stock analysis agent built from the project LLM config and tools."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from config.llm_config import (
    MODEL,
    MODEL_PROVIDER,
    PERPLEXITY_OPENAI_BASE_URL,
    SUPPORTED_PERPLEXITY_MODELS,
)
from tools.search_av import search_av

load_dotenv()

STOCK_ANALYSIS_TOOLS: Sequence[Any] = (search_av,)


def create_stock_analysis_agent() -> Any:
    """Create a tool-enabled stock analysis agent using configured LLM settings."""
    resolved_api_key = os.getenv("MODEL_API_KEY")
    if not resolved_api_key:
        raise ValueError("MODEL_API_KEY environment variable is not set.")

    model_kwargs: dict[str, Any] = {
        "model": MODEL,
        "model_provider": MODEL_PROVIDER,
        "api_key": resolved_api_key,
        "temperature": 0,
    }

    # Use Perplexity's OpenAI-compatible endpoint when configured that way.
    if MODEL in SUPPORTED_PERPLEXITY_MODELS:
        model_kwargs["base_url"] = PERPLEXITY_OPENAI_BASE_URL

    model = init_chat_model(**model_kwargs)
    try:
        return model.bind_tools(STOCK_ANALYSIS_TOOLS)
    except NotImplementedError:
        # Some provider integrations (including current Perplexity integration)
        # do not implement LangChain tool binding. Fall back to the OpenAI-
        # compatible endpoint for tool use when available.
        if MODEL in SUPPORTED_PERPLEXITY_MODELS:
            fallback_model = init_chat_model(
                model=MODEL,
                model_provider="openai",
                api_key=resolved_api_key,
                base_url=PERPLEXITY_OPENAI_BASE_URL,
                temperature=0,
            )
            return fallback_model.bind_tools(STOCK_ANALYSIS_TOOLS)
        raise
