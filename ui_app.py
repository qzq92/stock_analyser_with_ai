"""Streamlit UI for the Stock AI Agent: multi-symbol analysis and results."""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")

import concurrent.futures
import os

from ai_insights_handler import AIInsights
from stock_utility_handler import StockAPI, StockAnalyzer, TickerNotFoundError
import streamlit as st


def _parse_symbols(raw_symbols: str) -> list[str]:
    """Parse comma-separated symbols and keep at most 3 unique entries."""
    symbols = [symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()]
    return list(dict.fromkeys(symbols))[:3]


def _prepare_symbol_analysis(stock: str, market: str) -> dict[str, str]:
    """Fetch data and generate chart for one symbol without Streamlit calls."""
    image_path = f"<your_image_path>/{market}_{stock}.png"
    stock_api_obj = StockAPI(os.getenv("ALPHAVANTAGE_API_KEY"))
    stock_analyzer_obj = StockAnalyzer()

    market_data = stock_api_obj.get_stock_info(stock, market)
    df = stock_analyzer_obj.json_to_dataframe(market_data, stock, market)
    stock_analyzer_obj.plot_stock_data(df, stock, market, image_path)

    return {"stock": stock, "image_path": image_path}


if "page" not in st.session_state:
    st.session_state.page = "page1"
    st.session_state.ticker_input = "RELIANCE"
    st.session_state.market = "NASDAQ"
    st.session_state.symbols = ["RELIANCE"]
    st.session_state.results = []
    st.session_state.internal_results_available = False


def page1() -> None:
    """Render the input page: up to 3 symbols and market selection."""
    st.title("Stock AI Agent")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.ticker_input = st.text_input(
            "Enter up to 3 Stock Symbols (comma-separated)",
            value=st.session_state.ticker_input,
            key="ticker_input",
        )
    with col2:
        markets = ["NASDAQ", "DOW_JONES", "S&P500", "SINGAPORE"]
        selected_market = st.session_state.market if st.session_state.market in markets else "NASDAQ"
        st.session_state.market = st.selectbox(
            "Select Market",
            markets,
            index=markets.index(selected_market),
            key="market_input",
        )

    st.sidebar.header("About")
    st.sidebar.write("This is a stock analysis platform.")

    st.markdown("---")

    if st.button("Submit"):
        raw_symbols = [s.strip() for s in st.session_state.ticker_input.split(",") if s.strip()]
        if len(raw_symbols) > 3:
            st.error("Please limit input to at most 3 symbols.")
            return

        parsed_symbols = _parse_symbols(st.session_state.ticker_input)
        if not parsed_symbols:
            st.error("Please enter at least one stock symbol.")
            return

        st.session_state.symbols = parsed_symbols
        st.session_state.results = []
        st.session_state.page = "page2"
        st.session_state.internal_results_available = False
        st.rerun()


def page2() -> None:
    """Render chart and streamed analysis results for each selected symbol."""
    symbols = st.session_state.symbols
    market = st.session_state.market
    st.title(f"Analysis for {', '.join(symbols)} ({market})")

    if not st.session_state.internal_results_available:
        with st.spinner("Analyzing... Please wait..."):
            ai_insights_obj = AIInsights(os.getenv("PPLX_API_KEY"))
            prepared_by_symbol = {}
            max_workers = min(3, len(symbols))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_symbol = {
                    executor.submit(_prepare_symbol_analysis, stock, market): stock for stock in symbols
                }
                for future in concurrent.futures.as_completed(future_to_symbol):
                    stock = future_to_symbol[future]
                    try:
                        prepared_by_symbol[stock] = future.result()
                    except TickerNotFoundError:
                        prepared_by_symbol[stock] = {
                            "stock": stock,
                            "error": f"Ticker '{stock}' was not found. Please check the symbol and try again.",
                        }
                    except ValueError as exc:
                        prepared_by_symbol[stock] = {"stock": stock, "error": str(exc)}

            run_results = []
            for stock in symbols:
                prepared = prepared_by_symbol.get(stock, {"stock": stock, "error": "Unknown preparation failure"})
                if "error" in prepared:
                    run_results.append(
                        {
                            "stock": stock,
                            "image_path": "",
                            "ai_insights": f"Preparation failed for {stock}: {prepared['error']}",
                        }
                    )
                    continue

                st.subheader(f"Streaming Analysis: {stock}")
                image_path = prepared["image_path"]

                streaming_output = st.empty()
                stream_buffer = []
                for chunk in ai_insights_obj.get_ai_insights_stream(image_path, stock, market):
                    stream_buffer.append(chunk)
                    streaming_output.markdown("".join(stream_buffer))

                run_results.append(
                    {
                        "stock": stock,
                        "image_path": image_path,
                        "ai_insights": "".join(stream_buffer),
                    }
                )

            st.session_state.results = run_results
            st.session_state.internal_results_available = True

    if st.session_state.internal_results_available:
        for result in st.session_state.results:
            stock = result["stock"]
            st.subheader(f"Chart Analysis - {stock}")
            if result["image_path"]:
                st.image(result["image_path"], caption=f"{stock} Chart", use_column_width=True)
            st.subheader(f"Analysis Results - {stock}")
            st.write(result["ai_insights"])

        if st.button("Back"):
            st.session_state.page = "page1"
            st.session_state.internal_results_available = False
            st.session_state.results = []
            st.rerun()


if st.session_state.page == "page1":
    page1()
elif st.session_state.page == "page2":
    page2()