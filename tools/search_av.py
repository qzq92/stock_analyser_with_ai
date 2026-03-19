"""LangChain tools for querying Alpha Vantage stock data."""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from langchain_core.tools import tool

from stock_utility_handler import StockAPI

load_dotenv()


@tool
def search_av(stock: str, market: str) -> str:
    """Fetch Alpha Vantage daily stock information for a ticker and market.

    Args:
        stock: Stock ticker symbol, such as AAPL or MSFT.
        market: Exchange identifier, such as NASDAQ, DOW_JONES, or S&P500.

    Returns:
        JSON string containing the Alpha Vantage stock information payload.
    """
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise ValueError("ALPHAVANTAGE_API_KEY environment variable is not set.")

    stock_api = StockAPI(api_key)
    stock_info = stock_api.get_stock_info(stock, market)
    return json.dumps(stock_info)
