"""Streamlit UI for the Stock AI Agent: multi-symbol analysis and results."""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__" and not os.environ.get("_STREAMLIT_RUN"):
    import subprocess
    env = {**os.environ, "_STREAMLIT_RUN": "1"}
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__], env=env)
    sys.exit(0)

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")

import concurrent.futures

from ai_insights_handler import AIInsights
from stock_utility_handler import StockAPI, StockAnalyzer, TickerNotFoundError
import streamlit as st


def _prepare_symbol_analysis(stock: str, market: str) -> dict[str, str]:
    """Fetch data and generate chart for one symbol without Streamlit calls."""
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
    os.makedirs(img_dir, exist_ok=True)
    image_path = os.path.join(img_dir, f"{market}_{stock}.png")
    stock_api_obj = StockAPI(os.getenv("ALPHAVANTAGE_API_KEY"))
    stock_analyzer_obj = StockAnalyzer()

    market_data = stock_api_obj.get_stock_info(stock, market)
    df = stock_analyzer_obj.json_to_dataframe(market_data, stock, market)
    stock_analyzer_obj.plot_stock_data(df, stock, market, image_path)

    return {"stock": stock, "image_path": image_path}


def page1() -> None:
    """Render the input page: 1–3 individual symbol fields and market selection."""
    st.title("Stock AI Agent")

    col1, col2 = st.columns(2)
    with col1:
        num_tickers = st.selectbox("Number of stocks to analyse", [1, 2, 3], key="num_tickers")
    with col2:
        markets = ["NASDAQ", "DOW_JONES", "S&P500", "SINGAPORE"]
        selected_market = st.session_state.market if st.session_state.market in markets else "NASDAQ"
        st.session_state.market = st.selectbox(
            "Select Market",
            markets,
            index=markets.index(selected_market),
            key="market_input",
        )

    st.markdown("---")

    ticker_cols = st.columns(num_tickers)
    for i, col in enumerate(ticker_cols):
        with col:
            st.text_input(f"Symbol {i + 1}", key=f"ticker_{i}", placeholder="e.g. AAPL")

    st.sidebar.header("About")
    st.sidebar.write("This is a stock analysis platform.")

    st.markdown("---")

    if st.button("Submit"):
        entered = [
            st.session_state.get(f"ticker_{i}", "").strip().upper()
            for i in range(num_tickers)
        ]
        parsed_symbols = list(dict.fromkeys(s for s in entered if s))
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


if "page" not in st.session_state:
    st.session_state.page = "page1"
    st.session_state.market = "NASDAQ"
    st.session_state.symbols = []
    st.session_state.results = []
    st.session_state.internal_results_available = False

if st.session_state.page == "page1":
    page1()
elif st.session_state.page == "page2":
    page2()
