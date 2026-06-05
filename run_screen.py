"""Command line entry point for Euro Equity Intelligence."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from numbers import Integral, Real
from typing import Any

from euro_equity_intelligence.screener import EquityScreener


SORT_OPTIONS = ("score", "data_completeness")


def main(argv: Sequence[str] | None = None, screener: EquityScreener | None = None) -> None:
    """Parse CLI arguments and run either a single-company analysis or screen."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    active_screener = screener or EquityScreener()
    if args.ticker:
        try:
            result = active_screener.get_company_analysis(args.ticker)
        except Exception as exc:
            _print_failure(args.ticker, exc, as_json=args.json)
            return

        if args.json:
            print(_to_json(result))
        else:
            print(_format_results([result]))
        return

    try:
        results = active_screener.screen(
            limit=args.limit,
            min_score=args.min_score,
            include_unscored=args.include_unscored,
            sort_by=args.sort,
        )
    except Exception as exc:
        _print_failure("screen", exc, as_json=args.json)
        return

    if args.json:
        print(_to_json(results))
        return

    print(_format_results(results))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a transparent European equity screen from the command line.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ticker",
        metavar="TICKER",
        help="Analyze one ticker from the configured universe, for example ASML.AS.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="Maximum number of companies to display for a screen.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Only include scored companies with a final score at or above this threshold.",
    )
    parser.add_argument(
        "--sort",
        choices=SORT_OPTIONS,
        default="score",
        help="Sort screen output descending by final score or data completeness.",
    )
    parser.add_argument(
        "--include-unscored",
        action="store_true",
        help="Include companies marked insufficient_data or not_scored_financials.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON instead of a compact table.",
    )
    return parser


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _format_results(results: list[dict]) -> str:
    """Format screen results as a compact terminal table."""
    if not results:
        return "No companies matched the screen."

    headers = [
        "ticker",
        "name",
        "sector",
        "score",
        "score_status",
        "data_completeness",
        "missing_metrics_count",
        "warning_count",
    ]
    rows: list[list[str]] = []
    for result in results:
        company = result.get("company") or {}
        data_quality = result.get("data_quality") or {}
        rows.append(
            [
                _text(company.get("ticker")),
                _text(company.get("name")),
                _text(company.get("sector")),
                _score_text(result),
                _text(result.get("score_status")),
                _number_text(data_quality.get("data_completeness")),
                str(len(data_quality.get("missing_metrics") or [])),
                str(len(data_quality.get("warnings") or [])),
            ]
        )

    output = [_format_table(headers, rows)]
    warnings = _failure_lines(results)
    if warnings:
        output.append("")
        output.extend(warnings)
    return "\n".join(output)


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    header_line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _failure_lines(results: list[dict]) -> list[str]:
    lines = []
    for result in results:
        if not result.get("error"):
            continue
        company = result.get("company") or {}
        lines.append(f"Warning: {_text(company.get('ticker'))}: {result['error']}")
    return lines


def _score_text(result: dict) -> str:
    score = result.get("score")
    if not score or score.get("score") is None:
        return "unscored"
    return _number_text(score.get("score"))


def _number_text(value: Any) -> str:
    if value is None:
        return "--"
    if isinstance(value, Real) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return "--"
        return f"{float(value):.2f}"
    return str(value)


def _text(value: Any) -> str:
    return "--" if value is None else str(value)


def _print_failure(label: str, exc: Exception, as_json: bool) -> None:
    if as_json:
        print(_to_json({"status": "error", "ticker": label, "error": str(exc)}))
        return
    print(f"Error: {label}: {exc}")


def _to_json(payload: Any) -> str:
    return json.dumps(_json_safe(payload), indent=2, allow_nan=False)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence):
        return [_json_safe(item) for item in value]
    return str(value)


if __name__ == "__main__":
    main()
