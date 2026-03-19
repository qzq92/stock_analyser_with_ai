"""Stock data fetching (Alpha Vantage) and analysis/plotting utilities."""

from __future__ import annotations

import json
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import pandas as pd
import pytz
import requests


class TickerNotFoundError(ValueError):
    """Raised when Alpha Vantage does not recognize the requested ticker symbol."""


class StockAPI:
    """Fetches daily time series stock data from the Alpha Vantage API."""

    def __init__(self, api_key: str) -> None:
        """Store the Alpha Vantage API key.

        Args:
            api_key: Alpha Vantage API key for authenticated requests.
        """
        self.api_key = api_key

    def get_stock_info(self, stock: str, market: str) -> dict[str, Any]:
        """Request daily time series for a symbol on the given market.

        Args:
            stock: Stock ticker symbol (e.g. 'AAPL', 'DBS').
            market: Exchange identifier; US markets (NASDAQ, DOW_JONES, S&P500) use symbol as-is, others use symbol.suffix.

        Returns:
            JSON response from Alpha Vantage (e.g. under 'Time Series (Daily)').
        """
        us_markets = ("NASDAQ", "DOW_JONES", "S&P500")
        if market in us_markets:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock}&outputsize=compact&apikey={self.api_key}"
        else:
            market_suffix_map = {
                "SINGAPORE": "SI",
            }
            market_suffix = market_suffix_map.get(market, market)
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock}.{market_suffix}&outputsize=compact&apikey={self.api_key}"
        r = requests.get(url)
        data: dict[str, Any] = r.json()

        if "Time Series (Daily)" in data:
            return data

        if "Error Message" in data:
            raise TickerNotFoundError(
                f"Ticker '{stock}' was not found for market '{market}'."
            )

        if "Note" in data:
            raise ValueError(
                "Alpha Vantage API rate limit reached. Please wait and try again."
            )

        if "Information" in data:
            raise ValueError(str(data["Information"]))

        raise ValueError(
            "Unexpected response from Alpha Vantage. Please verify the symbol and try again."
        )


class StockAnalyzer:
    """Converts API time series to DataFrames and plots performance charts."""

    def __init__(self) -> None:
        """Initialize the analyzer (no configuration required)."""
        pass

    def _get_market_timezone(self, market: str) -> str:
        """Return the IANA timezone name for the given exchange.

        Args:
            market: Exchange identifier (e.g. 'NASDAQ', 'DOW_JONES', 'S&P500', 'SINGAPORE').

        Returns:
            IANA timezone string (e.g. 'US/Eastern', 'Asia/Singapore'), or 'UTC' if unknown.
        """
        market_timezone_map = {
            "NASDAQ": "US/Eastern",
            "DOW_JONES": "US/Eastern",
            "S&P500": "US/Eastern",
            "SINGAPORE": "Asia/Singapore",
        }
        return market_timezone_map.get(market, "UTC")

    def json_to_dataframe(
        self, json_data: dict[str, Any], stock_symbol: str, market: str
    ) -> pd.DataFrame:
        """Build a DataFrame from Alpha Vantage daily time series, with exchange timezone.

        Args:
            json_data: Raw API response containing 'Time Series (Daily)'.
            stock_symbol: Ticker symbol (stored in the DataFrame).
            market: Exchange identifier used for timezone and labelling.

        Returns:
            DataFrame with date index and columns for open/high/low/close/volume, plus stock/market.
        """
        print(json_data)
        time_series_data = json_data["Time Series (Daily)"]
        df_data = []

        for date_str, values in time_series_data.items():
            data_row: dict[str, Any] = {"date": date_str}
            for key, value in values.items():
                new_key = key.split(". ")[1]
                data_row[new_key] = float(value)
            df_data.append(data_row)

        df = pd.DataFrame(df_data)
        df["date"] = pd.to_datetime(df["date"])

        exchange_timezone = pytz.timezone(self._get_market_timezone(market))
        df["date"] = df["date"].dt.tz_localize(exchange_timezone)
        df["date"] = df["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["stock"] = stock_symbol
        df["market"] = market

        df = df.set_index("date")
        return df

    def plot_stock_data(
        self, df: pd.DataFrame, stock_symbol: str, market: str, image_path: str
    ) -> None:
        """Plot volume and moving averages; save figure to disk.

        Args:
            df: DataFrame with date index and 'close', 'volume' columns.
            stock_symbol: Ticker symbol for plot titles and labels.
            market: Exchange identifier for labels and timezone display.
            image_path: File path to save the figure (e.g. PNG).
        """
        exchange_timezone = self._get_market_timezone(market)
        dates = pd.to_datetime(df.index)
        plt.figure(figsize=(16, 10))

        # Plotting Volume
        plt.subplot(2, 1, 1)
        plt.bar(
            dates,
            df["volume"],
            label=f"{stock_symbol} Volume ({market})",
            color="green",
            width=2,
        )
        plt.xlabel(f'Date ({exchange_timezone})')
        plt.ylabel('Volume')
        plt.legend()
        plt.grid(True)

        # Plotting Moving Averages: 50-day always, 200-day only if enough history.
        plt.subplot(2, 1, 2)
        df["MA_50"] = df["close"].rolling(window=50).mean()
        has_ma_200 = len(df) >= 200
        if has_ma_200:
            df["MA_200"] = df["close"].rolling(window=200).mean()
        plt.plot(
            dates,
            df["close"],
            label=f"{stock_symbol} Closing Price ({market})",
            color="blue",
            alpha=0.7,
        )
        plt.plot(dates, df["MA_50"], label="50-Day MA", color="orange")
        if has_ma_200:
            plt.plot(dates, df["MA_200"], label="200-Day MA", color="red")
        plt.title(f"{stock_symbol} Stock Performance ({market})")
        plt.xlabel(f"Date ({exchange_timezone})")
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)

        # Enhanced Date Formatting for All Subplots
        for ax in plt.gcf().axes:
            # Major ticks every month, minor ticks every week
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=[0]))  # Monday

            # Formatter for major ticks
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

            # Formatter for minor ticks (hover tooltip will provide more detail)
            #ax.xaxis.set_minor_formatter(mdates.DateFormatter('%Y-%m-%d'))

            # Auto-rotate labels if needed
            plt.gcf().autofmt_xdate()

        # Add hover tooltip
        cursor = widgets.Cursor(plt.gca(), color='red', linewidth=1)

        plt.tight_layout()
        plt.savefig(image_path)
        plt.close()