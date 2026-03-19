# US Stock Analyser with AI

A Streamlit app that fetches US stock data from Alpha Vantage, plots volume and moving-average charts, and generates AI-powered analysis with structured output (`answer` + `citations`).

## Landing page

![Landing page screenshot](img/Sample_landing_page.jpg)

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **pandas / matplotlib** - Data processing and charting
- **LangChain + OpenAI** - LLM integration (Perplexity API)
- **Alpha Vantage** - Stock market data

## Project Structure

```
├── ui_app.py                 # Streamlit UI orchestration and rendering
├── stock_utility_handler.py  # Alpha Vantage fetch + dataframe/chart generation
├── ai_insights_handler.py    # LLM streaming + structured JSON parsing
├── llm_config.py             # Model configuration
├── img/                      # Generated chart PNGs (created at runtime)
└── pyproject.toml            # Dependencies
```

## File Purposes

- `ui_app.py`
  - Main Streamlit app entrypoint.
  - Handles user inputs (ticker count, market, symbols), app state, and page flow.
  - Runs chart preparation and LLM analysis, then renders chart/analysis side by side.
  - Aggregates all citation links and displays them in one `Sources` section at the bottom.

- `stock_utility_handler.py`
  - Calls Alpha Vantage `TIME_SERIES_DAILY` for market/ticker data.
  - Converts API JSON into pandas DataFrame with exchange timezone handling.
  - Generates chart images in `img/`:
    - volume subplot
    - price + moving averages subplot (50-day always, 200-day when enough history exists)

- `ai_insights_handler.py`
  - Builds and sends prompts to the configured LLM provider via LangChain.
  - Streams model output via `astream_events` for live UI updates.
  - Enforces structured JSON response format with fields:
    - `answer` (plain text analysis)
    - `citations` (URL list)
  - Parses and normalizes citations for frontend rendering.

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

`MODEL_API_KEY` should be the API key for the provider configured in `llm_config.py` (for example, Perplexity when using `sonar` / `sonar-pro`).

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

## How Graphs Are Generated

Charts are built from Alpha Vantage `TIME_SERIES_DAILY` data (currently requested with `outputsize=compact`, usually ~100 rows) and saved as PNGs in the project’s `img/` folder.

1. **Data** – For each symbol and market, the app requests `TIME_SERIES_DAILY` from Alpha Vantage, converts it to a pandas DataFrame (date index, `close`, `volume`), and applies the exchange timezone for labels.

2. **Plot layout** - Each chart is a single figure with two stacked subplots (matplotlib):
   - **Volume** – Bar chart of daily trading volume (green).
   - **Moving averages** – Closing price (blue) with 50-day MA (orange). 200-day MA (red) is shown only when enough historical data is available.

3. **Axes** – Dates use the exchange timezone; major ticks are monthly and minor ticks weekly. The figure is saved with `plt.savefig()`.

4. **Output** - One PNG per symbol and market, e.g. `img/NASDAQ_AAPL.png`. The `img/` directory is created automatically if it doesn’t exist. These paths are then used when requesting AI analysis.

## LLM Output and Citations

- The app requests a strict JSON response with:
  - `answer` (plain text)
  - `citations` (list of URLs)
- Streaming is still live on the frontend while the response is generated.
- All citations from analyzed symbols are consolidated into a single `Sources` section at the bottom of the page.

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
- **Model**: Defaults to Perplexity Sonar config in `llm_config.py`, but supports provider/model changes via configuration.
