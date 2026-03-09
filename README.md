# Stock Analyser with AI

A Streamlit app that fetches stock data from Alpha Vantage, displays charts with moving averages, and generates AI-powered insights using an OpenAI-compatible LLM.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **pandas / matplotlib** - Data processing and charting
- **LangChain + OpenAI** - LLM integration (Perplexity API)
- **Alpha Vantage** - Stock market data

## Project Structure

```
├── ui_app.py                 # Streamlit UI entry point
├── stock_utility_handler.py  # Alpha Vantage client & data utilities
├── ai_insights_handler.py    # LLM wrapper for insights
├── llm_config.py             # Model configuration
└── pyproject.toml            # Dependencies
```

## Getting Started

### 1. Install uv (if not installed)

```bash
pip install uv
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
PERPLEXITY_API_KEY=your_perplexity_key
```

Get your API keys:
- Alpha Vantage: https://www.alphavantage.co/
- Perplexity: https://www.perplexity.ai/

### 3. Install dependencies and run

```bash
uv sync
uv run streamlit run ui_app.py
```

The app will open at `http://localhost:8501`.

## Supported Markets

| Market | Symbol Format |
|--------|---------------|
| NASDAQ, Dow Jones, S&P 500 | `AAPL`, `MSFT` |
| Singapore | `D05.SI`, `U11.SI` |

## Alpha Vantage Rate Limits

The free tier has strict limitations:

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 25 | 25 |

- Exceeding limits returns `Note` or `Error` in JSON response instead of data
- Consider adding caching/backoff logic for production use
- Premium tiers available for higher limits

## Notes

- **Data**: Uses `TIME_SERIES_DAILY` with ~100 days of history.
- **Model**: Uses `gpt-5.1-mini` via Perplexity. Edit `llm_config.py` to change.
