## stock_analyser_with_ai

This repository contains a small Streamlit application that:
- **Fetches historical daily stock data** from the Alpha Vantage API for supported markets: NASDAQ, Dow Jones, S&P 500 (US symbol as-is), and Singapore (symbol suffix `SI`).
- **Builds time-series charts and moving-average overlays** via `pandas` and `matplotlib`.
- **Generates natural-language insights and buy/skip suggestions** using an OpenAI-compatible LLM endpoint (e.g. Perplexity) constrained to GPT‑5–series models.

The main components are:
- `stock_utility_handler.py`: Alpha Vantage client (`StockAPI`) and data/plotting utilities (`StockAnalyzer`).
- `ai_insights_handler.py`: LLM wrapper (`AIInsights`) that calls `init_chat_model` with configuration from `llm_config.py`.
- `ui_app.py`: Streamlit UI for entering a ticker/market and viewing charts plus AI insights.

---

## Prerequisites

- **Python**: 3.10 or newer (as specified in `pyproject.toml`).
- **uv**: For dependency and virtual-environment management.
- **Alpha Vantage API key**:
  - Obtain a free key from the official site: [`https://www.alphavantage.co/`](https://www.alphavantage.co/).
  - Configure it where `StockAPI` is instantiated (or via environment/config of your choice).
- **Perplexity (or other OpenAI-compatible) API key**:
  - The app assumes an OpenAI-compatible HTTP interface exposed at `https://api.perplexity.ai`.
  - The key is passed into `AIInsights` (or can be wired from environment variables).

To set up the environment with `uv`:

```bash
uv sync
uv run streamlit run ui_app.py
```

---

## Alpha Vantage API limitations

This project relies on the free Alpha Vantage stock APIs. Key constraints to be aware of (see the official Alpha Vantage documentation for current details: [`https://www.alphavantage.co/`](https://www.alphavantage.co/)):

- **Rate limits**:
  - Free-tier keys are subject to strict rate limits (historically on the order of *dozens of requests per minute* and *a few hundred per day*). Exceeding this can result in throttling or `Note`/`Error` messages in the JSON response instead of full time-series data.
  - When integrating this app into automated workflows, you should add backoff/retry logic or caching to avoid hitting limits.
- **Data scope and latency**:
  - The app currently uses the **`TIME_SERIES_DAILY`** function and `outputsize=compact`, which returns the most recent ~100 trading days only.
  - Intraday and extended history data would require different API functions and often higher tiers.
- **Exchange coverage**:
  - Not all symbols or exchanges are supported. This app supports:
    - **NASDAQ**, **Dow Jones**, **S&P 500**: US symbols requested as `SYMBOL` (no suffix).
    - **Singapore**: symbols requested as `SYMBOL.SI`.
  - If a symbol is not recognized, Alpha Vantage may return an error or empty payload; the app does not yet do extensive validation beyond basic JSON handling.

---

## Model restrictions and LLM configuration

The LLM used for natural-language insights is configured via `llm_config.py` and `ai_insights_handler.py`:

- **Perplexity base URL**:
  - `PERPLEXITY_OPENAI_BASE_URL` is set to `https://api.perplexity.ai`, treating Perplexity as an **OpenAI-compatible** endpoint.
- **GPT‑5–only restriction**:
  - `OPENAI_MODELS` in `llm_config.py` maps friendly keys to **GPT‑5–series models only**:
    - `fast` → `gpt-5.1-mini`
    - `balanced` → `gpt-5.1-mini`
    - `quality` → `gpt-5.1`
  - `DEFAULT_OPENAI_MODEL_KEY` is set to `"balanced"`.
  - `AIInsights` accepts a `model_key` and validates it against `OPENAI_MODELS`. Passing any other key raises a `ValueError`. As a result, **no non–GPT‑5 model IDs can be used unless you explicitly edit `llm_config.py`**.
- **Provider behavior**:
  - Although the client side is OpenAI-compatible, the actual behavior (latency, pricing, context length, and quality) depends on the provider backing `https://api.perplexity.ai`.

When modifying models, always update:
- `OPENAI_MODELS` in `llm_config.py`.
- Any documentation or operational runbooks that depend on specific model behavior or cost.

