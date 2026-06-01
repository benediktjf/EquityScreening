# Euro Equity Intelligence

Euro Equity Intelligence is a Python 3.11 equity screening project for European large-cap stocks. It fetches market and financial data, calculates valuation and quality metrics, ranks companies with a transparent 0-100 score, and exposes the result through both a CLI and a FastAPI service.

## 60-Second Recruiter Summary

- **What it is:** A modular stock screener for a starter universe of 20 European equities.
- **Why it matters:** It turns messy market and financial statement data into comparable investment signals.
- **What it demonstrates:** Python service design, data wrangling with pandas/numpy, API development with FastAPI, yfinance integration, scoring logic, CLI ergonomics, and unit-tested financial calculations.
- **How it behaves in the real world:** Missing or partial financial data does not crash the screen. Unavailable metrics are returned as `null`, scored neutrally, and reflected in `data_completeness`.
- **Main entry points:** `python run_screen.py` for analysts, `GET /screen` for applications.

## Core Capabilities

- Starts with 20 European tickers across major markets and sectors
- Fetches price history, market data, income statement, balance sheet, and cash flow data from `yfinance`
- Calculates:
  - Revenue growth
  - EBITDA margin
  - Net debt / EBITDA
  - P/E
  - EV/EBITDA
  - ROE
  - Free cash flow yield
- Scores each company from 0-100 using explicit metric weights
- Provides CLI output for quick screening and JSON output for downstream use
- Provides FastAPI endpoints for integration
- Includes unit tests with mocked data, including missing-data cases

## Architecture

```text
euro_equity_intelligence/
  universe.py       20-stock European starter universe
  data_provider.py  yfinance access layer and FinancialData model
  metrics.py        pure financial metric calculations
  scoring.py        0-100 scoring model
  screener.py       orchestration service used by CLI and API
  api.py            FastAPI application
run_screen.py       command-line interface
tests/              unittest test suite with mocked financial data
```

The project keeps data fetching, financial calculations, scoring, and delivery layers separate so each piece can be tested or replaced independently.

## Setup

```bash
cd euro-equity-intelligence
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI Usage

Run the full screen:

```bash
python run_screen.py
```

Analyze one ticker:

```bash
python run_screen.py --ticker ASML.AS --json
```

Filter and limit output:

```bash
python run_screen.py --min-score 70 --limit 10
```

## API Usage

Start the API:

```bash
uvicorn euro_equity_intelligence.api:app --reload
```

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/companies` | List the 20-stock universe |
| `GET` | `/companies/{ticker}` | Return company metadata, market snapshot, metrics, and score |
| `GET` | `/screen` | Rank the universe by score |

Example:

```bash
curl "http://127.0.0.1:8000/screen?limit=10&min_score=60"
```

## Scoring Model

Each metric is converted into a 0-100 component score and combined with fixed weights:

| Metric | Weight | Direction |
| --- | ---: | --- |
| Revenue growth | 15% | Higher is better |
| EBITDA margin | 15% | Higher is better |
| Net debt / EBITDA | 15% | Lower is better |
| P/E | 15% | Lower is better |
| EV/EBITDA | 15% | Lower is better |
| ROE | 15% | Higher is better |
| Free cash flow yield | 10% | Higher is better |

Missing metrics receive a neutral component score of 50. The response also includes `data_completeness`, so consumers can distinguish a genuinely average company from a company with sparse data.

## Tests

```bash
python -m unittest discover
```

The tests use mocked statements and market data, so they do not require live yfinance calls.

## Notes

This is an engineering portfolio project, not investment advice. Live results depend on the availability and quality of yfinance data for each ticker.
