"""Command line entry point for Euro Equity Intelligence."""

from __future__ import annotations

import argparse
import json

import pandas as pd

from euro_equity_intelligence.screener import EquityScreener


def main() -> None:
    """Parse CLI arguments and run either a single-company analysis or screen."""
    parser = argparse.ArgumentParser(description="Run a European equity screen.")
    parser.add_argument("--ticker", help="Analyze one ticker from the universe, e.g. ASML.AS")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of rows to display")
    parser.add_argument("--min-score", type=float, default=None, help="Only show companies at or above this score")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a compact table")
    args = parser.parse_args()

    screener = EquityScreener()
    if args.ticker:
        result = screener.get_company_analysis(args.ticker)
        print(json.dumps(result, indent=2))
        return

    results = screener.screen(limit=args.limit, min_score=args.min_score)
    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(_format_results(results))


def _format_results(results: list[dict]) -> str:
    """Format screen results as a compact terminal table."""
    rows: list[dict[str, object]] = []
    for result in results:
        company = result["company"]
        metrics = result.get("metrics") or {}
        score = result.get("score") or {}
        data_quality = result.get("data_quality") or {}
        rows.append(
            {
                "ticker": company["ticker"],
                "name": company["name"],
                "country": company["country"],
                "score": score.get("score"),
                "data": data_quality.get("data_completeness"),
                "revenue_growth": _pct(metrics.get("revenue_growth")),
                "ebitda_margin": _pct(metrics.get("ebitda_margin")),
                "net_debt_ebitda": _num(metrics.get("net_debt_to_ebitda")),
                "pe": _num(metrics.get("pe_ratio")),
                "ev_ebitda": _num(metrics.get("ev_to_ebitda")),
                "roe": _pct(metrics.get("roe")),
                "fcf_yield": _pct(metrics.get("free_cash_flow_yield")),
                "error": result.get("error"),
            }
        )
    return pd.DataFrame(rows).to_string(index=False)


def _pct(value: float | None) -> str | None:
    return None if value is None else f"{value * 100:.1f}%"


def _num(value: float | None) -> str | None:
    return None if value is None else f"{value:.2f}"


if __name__ == "__main__":
    main()
