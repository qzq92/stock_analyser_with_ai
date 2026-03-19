# US Stock Analyser with AI

A Streamlit app that fetches US stock data from Alpha Vantage, plots volume and moving-average charts, and generates AI-powered analysis with structured output (`answer` + `citations`). Before each analysis, a separate company-info agent retrieves the full company name, a brief business description, and the official website.

## Landing page

![Landing page screenshot](img/Sample_landing_page.jpg)

## Sample response

![Sample response screenshot](img/sample_response.jpg)
Example output showing company information header, side-by-side chart and plain-text analysis, with citation links listed under the analysis.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **pandas / matplotlib** - Data processing and charting
- **LangChain + OpenAI** - LLM integration (Perplexity Sonar API)
- **Alpha Vantage** - Stock market data

## Project Structure

```
├── ui_app.py                       # Streamlit UI orchestration and rendering
├── stock_utility_handler.py        # Alpha Vantage fetch + dataframe/chart generation
├── ai_insights_handler.py          # LLM streaming + structured JSON parsing
├── company_info_handler.py         # Company name/description/website lookup via LLM
├── agent/
│   ├── stock_analysis_agent.py     # LLM instance for stock analysis
│   └── company_info_agent.py       # LLM instance for company info lookups
├── prompts/
│   ├── analyst_prompt.py           # Stock analysis prompt template
│   └── company_info_prompt.py      # Company info prompt template
├── config/
│   └── llm_config.py              # Model provider, model name, and base URL
├── tools/
│   └── search_av.py               # LangChain tool wrapping Alpha Vantage API
├── img/                            # Generated chart PNGs (created at runtime)
└── pyproject.toml                  # Dependencies
```

## File Purposes

- `ui_app.py`
  - Main Streamlit app entrypoint.
  - Handles user inputs (ticker count, market, symbols), app state, and page flow.
  - For each symbol: fetches company info, renders the chart, then streams AI analysis side by side.
  - Citation links are displayed under the analysis results for each stock.

- `stock_utility_handler.py`
  - Calls Alpha Vantage `TIME_SERIES_DAILY` for market/ticker data.
  - Converts API JSON into pandas DataFrame with exchange timezone handling.
  - Sorts data chronologically before computing moving averages.
  - Generates chart images in `img/`:
    - volume subplot
    - price + moving averages subplot (50-day always, 200-day when enough history exists)

- `ai_insights_handler.py`
  - Builds prompts with pre-fetched stock data and sends them to the configured LLM.
  - Streams model output via `astream_events` for live UI updates.
  - Enforces structured JSON response format with fields:
    - `answer` (plain text analysis)
    - `citations` (URL list)
  - Parses and normalizes citations for frontend rendering.

- `company_info_handler.py`
  - Queries the LLM for company metadata given a ticker symbol and market.
  - Returns structured `CompanyInfo` with `full_name`, `description`, and `website`.
  - Gracefully falls back to ticker-only display if the lookup fails.

- `agent/stock_analysis_agent.py` / `agent/company_info_agent.py`
  - Each creates an LLM instance from the shared config in `config/llm_config.py`.
  - The stock analysis agent handles financial analysis; the company info agent handles metadata lookups.

- `config/llm_config.py`
  - Central configuration for LLM provider, model name, and base URL.
  - Defaults to Perplexity Sonar (`sonar-pro`) via the OpenAI-compatible endpoint.

## Getting Started

### 1. Install uv (if not installed)

```bash
pip install uv
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```
ALPHAVANTAGE_API_KEY=your_alpha_vantage_key
MODEL_API_KEY=your_model_provider_key
```

`MODEL_API_KEY` should be the API key for the provider configured in `config/llm_config.py` (for example, Perplexity when using `sonar-pro`).

Get your API keys:
- Alpha Vantage: https://www.alphavantage.co/
- Perplexity: https://www.perplexity.ai/
- OpenAI: https://platform.openai.com/api-keys
- DeepSeek: https://platform.deepseek.com/api_keys

### 3. Install dependencies and run

```bash
uv sync
uv run ui_app.py
```

The app will open at `http://localhost:8501`.

## How It Works

### Company Information

For each ticker, the company info agent queries the LLM to retrieve:
- **Full company name** (e.g. "Apple Inc." for AAPL)
- **Business description** (1-2 sentence summary)
- **Official website** (clickable link)

This is displayed as a header above the chart and analysis columns.

### Chart Generation

Charts are built from Alpha Vantage `TIME_SERIES_DAILY` data (requested with `outputsize=compact`, ~100 rows) and saved as PNGs in the `img/` folder.

1. **Data** -- For each symbol and market, the app requests daily time series from Alpha Vantage, converts it to a pandas DataFrame, sorts it chronologically, and applies the exchange timezone for labels.

2. **Plot layout** -- Each chart is a single figure with two stacked subplots (matplotlib):
   - **Volume** -- Bar chart of daily trading volume (green).
   - **Moving averages** -- Closing price (blue) with 50-day MA (orange). 200-day MA (red) is shown only when enough historical data is available.

3. **Axes** -- Dates use the exchange timezone; major ticks are monthly and minor ticks weekly. The figure is saved with `plt.savefig()`.

4. **Output** -- One PNG per symbol and market, e.g. `img/NASDAQ_AAPL.png`. The `img/` directory is created automatically.

### AI Analysis

- Stock data (OHLCV) is pre-fetched and injected directly into the prompt, avoiding tool-calling limitations of certain LLM providers.
- The app requests a strict JSON response with:
  - `answer` (plain text)
  - `citations` (list of URLs)
- Streaming is live on the frontend while the response is generated.
- Citation links appear under each stock's analysis in the right column.

## Supported Markets

| Market | Symbol Format |
|--------|---------------|
| NASDAQ, Dow Jones, S&P 500 | `AAPL`, `MSFT` |

## Alpha Vantage Rate Limits

The free tier has strict limitations:

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 25 | 25 |

- Exceeding limits returns `Note` or `Error` in JSON response instead of data
- Consider adding caching/backoff logic for production use
- Premium tiers available for higher limits

## Notes

- **Data**: Uses `TIME_SERIES_DAILY` with `outputsize=compact` by default (~100 days, depending on market/trading days).
- **Model**: Defaults to Perplexity Sonar config in `config/llm_config.py`, but supports provider/model changes via configuration. The Perplexity Sonar API does not support custom tool/function calling, so stock data is pre-fetched and included in the prompt.
