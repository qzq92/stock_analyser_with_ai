"""Configured company info model built from the project LLM config."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from config.llm_config import (
    MODEL,
    MODEL_PROVIDER,
    LLM_BASE_URL,
)

load_dotenv()


def create_company_info_agent() -> Any:
    """Create an LLM instance for company information lookups."""
    resolved_api_key = os.getenv("MODEL_API_KEY")
    if not resolved_api_key:
        raise ValueError("MODEL_API_KEY environment variable is not set.")

    return init_chat_model(
        model=MODEL,
        model_provider=MODEL_PROVIDER,
        api_key=resolved_api_key,
        temperature=0,
        base_url=LLM_BASE_URL,
    )
