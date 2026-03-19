"""Prompt templates for stock analysis."""

from langchain_core.prompts import PromptTemplate

ANALYST_PROMPT_TEMPLATE = PromptTemplate.from_template(
    """Return ONLY valid JSON with exactly two top-level fields:
{{"answer": "<plain text analysis>", "citations": ["https://..."]}}.
Analyze stock '{stock}' over the last 100 days on market '{market}'.
Base your answer on volume traded, closing prices, and 50-day/200-day moving averages
(or 50-day only when 200-day is unavailable).
State whether the stock appears worth purchasing or not.
The 'answer' field must be plain text only with no markdown or special formatting.
The 'citations' field must be a JSON array of source URL strings only, and it must
include every source referenced or relied on in the answer.
Do not return only a partial subset of the sources.
If you have no citations, return an empty list.
"""
)
