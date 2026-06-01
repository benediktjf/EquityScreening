# Euro Equity Intelligence

Euro Equity Intelligence is a Python 3.11 screening tool for a small universe of European equities. It fetches market and financial data from `yfinance`, calculates a set of valuation and quality metrics, applies a transparent 0-100 heuristic score for non-financial companies, and exposes the results through a CLI and FastAPI API.

The project is intended for financial data exploration and code review. It is not an investment engine, trading system, or recommendation service.

## Project Overview

The current universe contains 20 large European companies across Germany, France, Switzerland, the Netherlands, Spain, Italy, and the UK. For each company, the screener attempts to retrieve:

- market price data
- market capitalization and enterprise value
- income statement data
- balance sheet data
- cash flow data

Each response includes company metadata, a market snapshot, calculated metrics, a score, and data quality information.

Banks and insurers are identified by sector and are not scored by the default model. They can still be returned by company endpoints and optional screen output with `score_status = "not_scored_financials"`.

## Architecture

```text
euro_equity_intelligence/
  universe.py       Static 20-stock European universe
  data_provider.py  yfinance access layer with defensive fallbacks
  metrics.py        Financial metric calculations
  scoring.py        Heuristic 0-100 scoring model
  screener.py       Orchestration layer used by CLI and API
  api.py            FastAPI application
run_screen.py       CLI entry point
tests/              unittest suite with mocked financial data
docs/               Screenshot guide and example API response
```

The code separates data retrieval, metric calculation, scoring, and delivery. The financial calculations and scoring logic can be tested without live `yfinance` calls.

## API Documentation

![FastAPI Docs](docs/api_docs.png)

## Metrics

The screener calculates:

- revenue growth
- EBITDA margin
- net debt / EBITDA
- P/E
- EV/EBITDA
- ROE
- free cash flow yield

If a metric cannot be calculated from available data, the value is returned as `null`.

## Scoring Methodology

For non-financial companies, each metric is converted into a 0-100 component score and combined with fixed weights:

| Metric | Weight | Direction | Heuristic Range |
| --- | ---: | --- | --- |
| Revenue growth | 15% | Higher is better | -10% to 20% |
| EBITDA margin | 15% | Higher is better | 0% to 30% |
| Net debt / EBITDA | 15% | Lower is better | 0x to 5x |
| P/E | 15% | Lower is better | 8x to 35x |
| EV/EBITDA | 15% | Lower is better | 6x to 20x |
| ROE | 15% | Higher is better | 0% to 25% |
| Free cash flow yield | 10% | Higher is better | 0% to 10% |

The ranges are heuristic demo ranges chosen to make companies comparable inside this small universe. They are not investment-grade valuation bands and should not be interpreted as buy/sell thresholds.

Missing metrics receive a neutral component score of `50`. The response includes `data_completeness`, so users can separate complete results from sparse data.

Financial companies are not scored by this model because bank and insurance analysis requires sector-specific metrics.

Example score block:

```json
{
  "score": {
    "score": 76.45,
    "data_completeness": 1.0
  },
  "score_status": "scored",
  "data_quality": {
    "missing_metrics": [],
    "warnings": []
  }
}
```

Financial company score block:

```json
{
  "score": null,
  "score_status": "not_scored_financials",
  "data_quality": {
    "warnings": [
      "Financial companies are not scored by the default model because bank/insurance analysis requires sector-specific metrics."
    ]
  }
}
```

## Data Handling

`yfinance` data can be incomplete, delayed, renamed, or unavailable for some tickers. The project handles common failure modes defensively:

- missing `info` fields become empty dictionaries
- missing statements become empty data frames
- missing financial rows become `null` metrics
- duplicate statement rows and non-numeric cells are tolerated
- provider failures return a stable response with neutral scoring and `data_quality.warnings`

## How To Run

```bash
cd euro-equity-intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
python3 -m unittest discover
```

Run the CLI:

```bash
python3 run_screen.py
```

Analyze one company:

```bash
python3 run_screen.py --ticker ASML.AS --json
```

Filter screen results:

```bash
python3 run_screen.py --min-score 70 --limit 10
```

Include unscored financial companies in CLI output:

```bash
python3 run_screen.py --include-unscored
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
| `include_unscored` | boolean | Include financial companies that are not scored by the default model |

Example:

```bash
curl "http://127.0.0.1:8000/screen?limit=5&min_score=60"
```

Include unscored financial companies:

```bash
curl "http://127.0.0.1:8000/screen?include_unscored=true"
```

## Example Output

CLI table shape:

```text
ticker  name          country      score  status  data revenue_growth ebitda_margin net_debt_ebitda    pe ev_ebitda    roe fcf_yield error
ASML.AS ASML Holding  Netherlands  76.45  scored  1.00          14.0%         33.0%            -0.40 38.20     25.10  51.0%      2.5%  None
SAP.DE  SAP           Germany      68.20  scored  0.86           9.0%         28.0%             0.70 31.10     18.40  19.0%      None  None
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
  "score_status": "scored",
  "data_quality": {
    "missing_metrics": [],
    "warnings": []
  }
}
```

Live values will differ because they depend on the current `yfinance` response.

## Screenshots

Screenshot instructions live in [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md).

Recommended captures:

- CLI table from `python3 run_screen.py --limit 10`
- FastAPI docs at `http://127.0.0.1:8000/docs`
- JSON response from `/companies/ASML.AS`

Store fresh captures in `docs/screenshots/`.

## Limitations

- `yfinance` data quality and availability vary by ticker, exchange, and statement field.
- The scoring model is a simplified heuristic for non-financial companies, not a valuation model.
- The universe is fixed at 20 European companies.
- The project does not include backtesting.
- Scores are not sector-relative yet.
- Financial companies are not scored by default. Bank and insurer analysis requires metrics such as capital ratios, net interest margin, combined ratio, or book-value-based valuation, which are not implemented yet.

## Roadmap

- Add configurable ticker universes from CSV
- Add sector-relative scoring
- Add cached data snapshots for reproducible demos
- Add financial-sector-specific metrics
- Add CI workflow for tests

## Disclaimer

This project is for software engineering demonstration and financial data exploration. It is not investment advice.
