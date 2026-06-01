# Euro Equity Intelligence

Euro Equity Intelligence is a Python 3.11 equity screening tool for European stocks. It fetches market and financial data from `yfinance`, calculates common valuation and quality metrics, scores each company from 0-100, and exposes the results through both a command-line interface and a FastAPI API.

This is a portfolio-ready MVP focused on clean architecture, transparent financial logic, and graceful handling of imperfect market data.

## Project Overview

The screener starts with a fixed universe of 20 large European companies across Germany, France, Switzerland, the Netherlands, Spain, Italy, and the UK. For each company it attempts to fetch price, market capitalization, enterprise value, income statement, balance sheet, and cash flow data.

The output is designed for quick comparison:

- company metadata
- latest market snapshot
- calculated financial metrics
- weighted 0-100 score
- data quality warnings when `yfinance` data is missing or incomplete

## Architecture

```text
euro_equity_intelligence/
  universe.py       Static 20-stock European universe
  data_provider.py  yfinance access layer with defensive fallbacks
  metrics.py        Pure financial metric calculations
  scoring.py        Weighted 0-100 scoring model
  screener.py       Orchestration layer used by CLI and API
  api.py            FastAPI application
run_screen.py       CLI entry point
tests/              unittest suite with mocked financial data
docs/               Screenshot guide and example API response
```

The design keeps data retrieval, metric calculation, scoring, and delivery separate. That makes the core logic easy to test without live market data and keeps the API/CLI layers thin.

## Metrics

The project calculates:

- revenue growth
- EBITDA margin
- net debt / EBITDA
- P/E
- EV/EBITDA
- ROE
- free cash flow yield

When a metric cannot be calculated because external data is missing, the value is returned as `null` rather than raising an exception.

## Scoring Methodology

Each metric is converted into a 0-100 component score and combined with explicit weights:

| Metric | Weight | Direction | Range Used |
| --- | ---: | --- | --- |
| Revenue growth | 15% | Higher is better | -10% to 20% |
| EBITDA margin | 15% | Higher is better | 0% to 30% |
| Net debt / EBITDA | 15% | Lower is better | 0x to 5x |
| P/E | 15% | Lower is better | 8x to 35x |
| EV/EBITDA | 15% | Lower is better | 6x to 20x |
| ROE | 15% | Higher is better | 0% to 25% |
| Free cash flow yield | 10% | Higher is better | 0% to 10% |

Missing metrics receive a neutral component score of `50`. The response includes `data_completeness`, so users can distinguish a genuinely average company from a company with sparse data.

Example:

```json
{
  "score": {
    "score": 76.45,
    "data_completeness": 1.0
  },
  "data_quality": {
    "missing_metrics": [],
    "warnings": []
  }
}
```

## Graceful Data Handling

`yfinance` data can be incomplete, delayed, renamed, or unavailable for some tickers. The project handles this defensively:

- missing `info` fields become empty dictionaries
- missing statements become empty data frames
- missing financial rows become `null` metrics
- duplicate statement rows and non-numeric cells are tolerated
- provider failures return a stable response with neutral scoring and `data_quality.warnings`

This keeps the API and CLI usable even when one company has poor source data.

## How To Run

```bash
cd euro-equity-intelligence
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
python -m unittest discover
```

Run the CLI:

```bash
python run_screen.py
```

Analyze one company:

```bash
python run_screen.py --ticker ASML.AS --json
```

Filter screen results:

```bash
python run_screen.py --min-score 70 --limit 10
```

## API

Start the API:

```bash
uvicorn euro_equity_intelligence.api:app --reload
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

### Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/companies` | List the 20-stock universe |
| `GET` | `/companies/{ticker}` | Analyze one company |
| `GET` | `/screen` | Rank companies by score |

Optional `/screen` query parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `limit` | integer | Number of results, default `20`, max `50` |
| `min_score` | float | Only return companies with score >= this value |

Example:

```bash
curl "http://127.0.0.1:8000/screen?limit=5&min_score=60"
```

## Example Output

CLI table shape:

```text
ticker  name          country      score  data revenue_growth ebitda_margin net_debt_ebitda    pe ev_ebitda    roe fcf_yield error
ASML.AS ASML Holding  Netherlands  76.45  1.00          14.0%         33.0%            -0.40 38.20     25.10  51.0%      2.5%  None
SAP.DE  SAP           Germany      68.20  0.86           9.0%         28.0%             0.70 31.10     18.40  19.0%      None  None
```

Single company API response shape:

```json
{
  "company": {
    "ticker": "ASML.AS",
    "name": "ASML Holding",
    "country": "Netherlands",
    "exchange": "Euronext Amsterdam",
    "sector": "Technology"
  },
  "market": {
    "currency": "EUR",
    "market_cap": 350000000000,
    "enterprise_value": 345000000000,
    "last_close": 900.12
  },
  "metrics": {
    "revenue_growth": 0.14,
    "ebitda_margin": 0.33,
    "net_debt_to_ebitda": -0.4,
    "pe_ratio": 38.2,
    "ev_to_ebitda": 25.1,
    "roe": 0.51,
    "free_cash_flow_yield": 0.025
  },
  "score": {
    "score": 76.45,
    "data_completeness": 1.0
  },
  "data_quality": {
    "missing_metrics": [],
    "warnings": []
  }
}
```

Live values will differ because they depend on the current `yfinance` response.

## Screenshots

Screenshot instructions live in [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md).

Recommended portfolio captures:

- CLI table from `python run_screen.py --limit 10`
- FastAPI docs at `http://127.0.0.1:8000/docs`
- JSON response from `/companies/ASML.AS`

Store fresh captures in `docs/screenshots/`.

## Roadmap

- Add configurable ticker universes from CSV
- Add sector-relative scoring
- Add simple historical trend charts
- Add cached data snapshots for reproducible demos
- Add Dockerfile for one-command local setup
- Add CI workflow for tests and linting

## Disclaimer

This project is for software engineering demonstration and financial data exploration. It is not investment advice.
