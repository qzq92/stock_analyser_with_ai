"""Prompt template for company information lookup."""

from langchain_core.prompts import PromptTemplate

COMPANY_INFO_PROMPT_TEMPLATE = PromptTemplate.from_template(
    """Return ONLY valid JSON with exactly three top-level fields:
{{"full_name": "<official company name>", "description": "<1-2 sentence business description>", "website": "<official website URL>"}}.
Given the stock ticker symbol '{stock}' on market '{market}', provide:
1. The full official company name.
2. A concise 1-2 sentence description of what the company does.
3. The official company website URL.
All fields must be plain text strings. Do not include any markdown or extra formatting.
"""
)
