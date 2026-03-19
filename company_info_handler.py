"""Company information lookup via the configured LLM."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from agent.company_info_agent import create_company_info_agent
from prompts.company_info_prompt import COMPANY_INFO_PROMPT_TEMPLATE


class CompanyInfo(BaseModel):
    """Structured company metadata returned by the LLM."""

    full_name: str = ""
    description: str = ""
    website: str = ""


class CompanyInfoHandler:
    """Fetches company name, description, and website for a given ticker."""

    def __init__(self) -> None:
        self._agent = create_company_info_agent()

    def get_company_info(self, stock: str, market: str) -> CompanyInfo:
        """Query the LLM for company metadata.

        Args:
            stock: Stock ticker symbol (e.g. 'AAPL').
            market: Exchange identifier (e.g. 'NASDAQ').

        Returns:
            Parsed CompanyInfo with full_name, description, and website.
        """
        prompt = COMPANY_INFO_PROMPT_TEMPLATE.format(stock=stock, market=market)
        try:
            response = self._agent.invoke(prompt)
            return self._parse_response(response)
        except Exception:
            return CompanyInfo(
                full_name=stock,
                description="Company information unavailable.",
                website="",
            )

    def _parse_response(self, response: Any) -> CompanyInfo:
        """Extract structured fields from the LLM response."""
        raw_text = response.content if hasattr(response, "content") else str(response)
        cleaned = raw_text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        if "{" in cleaned and "}" in cleaned:
            cleaned = cleaned[cleaned.find("{"):cleaned.rfind("}") + 1]

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return CompanyInfo(
                full_name="",
                description=raw_text.strip(),
                website="",
            )

        return CompanyInfo(
            full_name=payload.get("full_name", ""),
            description=payload.get("description", ""),
            website=payload.get("website", ""),
        )
