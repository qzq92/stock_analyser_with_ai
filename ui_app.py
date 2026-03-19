"""Streamlit UI for the US Stock AI Agent: multi-symbol analysis and results."""

import json
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

# Set page layout to wide to allow for wider charts
st.set_page_config(layout="wide")


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

    return {
        "stock": stock,
        "image_path": image_path,
        "market_data_json": json.dumps(market_data),
    }


def page1() -> None:
    """Render the input page: 1–3 individual symbol fields and market selection."""
    st.title("US Stock AI Agent")

    col1, col2 = st.columns(2)
    with col1:
        num_tickers = st.selectbox("Number of stocks to analyse", [1, 2, 3], key="num_tickers")
    with col2:
        markets = ["NASDAQ", "DOW_JONES", "S&P500"]
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
    st.sidebar.caption(
        "Disclaimer: This app analyzes stock ticker symbols only. "
        "It does not support other asset types."
    )

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
        if st.button("Back to main", key="back_during_analysis"):
            st.session_state.page = "page1"
            st.session_state.internal_results_available = False
            st.session_state.results = []
            st.rerun()

        ai_insights_obj = AIInsights()
        run_results = []
        for stock in symbols:
            with st.spinner(f"Preparing chart for {stock}..."):
                try:
                    prepared = _prepare_symbol_analysis(stock, market)
                except TickerNotFoundError:
                    prepared = {
                        "stock": stock,
                        "image_path": "",
                        "market_data_json": "",
                        "error": f"Ticker '{stock}' was not found. Please check the symbol and try again.",
                    }
                except ValueError as exc:
                    prepared = {
                        "stock": stock,
                        "image_path": "",
                        "market_data_json": "",
                        "error": str(exc),
                    }

            if prepared.get("error"):
                left_col, right_col = st.columns(2)
                with left_col:
                    st.subheader(f"Chart Analysis - {stock}")
                    if prepared.get("image_path"):
                        st.image(
                            prepared["image_path"],
                            caption=f"{stock} Chart",
                            width='stretch,
                        )
                    else:
                        st.write("Chart unavailable due to preparation error.")

                with right_col:
                    st.subheader(f"Analysis Results - {stock}")
                    st.error(prepared["error"])

                st.markdown("---")
                run_results.append(
                    {
                        "stock": stock,
                        "image_path": "",
                        "answer": f"Preparation failed for {stock}: {prepared['error']}",
                        "citations": [],
                    }
                )
                continue

            image_path = prepared["image_path"]
            stock_data = prepared["market_data_json"]

            left_col, right_col = st.columns(2)
            with left_col:
                st.subheader(f"Chart Analysis - {stock}")
                st.image(image_path, caption=f"{stock} Chart", width='stretch)
            with right_col:
                st.subheader(f"Analysis Results - {stock}")
                streaming_output = st.empty()
                stream_buffer: list[str] = []
                for chunk in ai_insights_obj.get_ai_insights_stream(stock, market, stock_data):
                    stream_buffer.append(chunk)
                    streaming_output.markdown("".join(stream_buffer))

                structured_response = ai_insights_obj.get_latest_response()
                answer = structured_response.answer or "".join(stream_buffer)
                citations = structured_response.citations
                streaming_output.text(answer)
                if citations:
                    st.markdown("**Sources**")
                    for i, url in enumerate(citations, start=1):
                        st.markdown(f"{i}. [{url}]({url})")

            st.markdown("---")

            run_results.append(
                {
                    "stock": stock,
                    "image_path": image_path,
                    "answer": structured_response.answer or "".join(stream_buffer),
                    "citations": structured_response.citations,
                }
            )

        st.session_state.results = run_results
        st.session_state.internal_results_available = True
        st.rerun()

    else:
        for result in st.session_state.results:
            stock = result["stock"]
            citations = result.get("citations") or []
            left_col, right_col = st.columns(2)
            with left_col:
                st.subheader(f"Chart Analysis - {stock}")
                if result["image_path"]:
                    st.image(result["image_path"], caption=f"{stock} Chart", width='stretch)
            with right_col:
                st.subheader(f"Analysis Results - {stock}")
                st.text(result["answer"])
                if citations:
                    st.markdown("**Sources**")
                    for i, url in enumerate(citations, start=1):
                        st.markdown(f"{i}. [{url}]({url})")
            st.markdown("---")

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
