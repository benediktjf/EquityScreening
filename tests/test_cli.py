from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from typing import Any

from run_screen import main


def _analysis(
    ticker: str,
    name: str,
    sector: str,
    score: float | None,
    score_status: str,
    data_completeness: float,
    missing_metrics: list[str] | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company": {
            "ticker": ticker,
            "name": name,
            "country": "Netherlands",
            "exchange": "Example Exchange",
            "sector": sector,
        },
        "market": {"currency": "EUR", "last_close": 100.0},
        "metrics": {"revenue_growth": 0.08},
        "score": None
        if score is None
        else {
            "score": score,
            "components": {"revenue_growth": 60.0},
            "score_breakdown": {
                "revenue_growth": {
                    "raw_value": 0.08,
                    "component_score": 60.0,
                    "weight": 0.15,
                    "weighted_contribution": 9.0,
                    "direction": "higher_is_better",
                }
            },
            "data_completeness": data_completeness,
        },
        "score_status": score_status,
        "data_quality": {
            "missing_metrics": missing_metrics or [],
            "data_completeness": data_completeness,
            "warnings": warnings or [],
        },
    }
    if error:
        payload["error"] = error
    return payload


class FakeCliScreener:
    def __init__(self) -> None:
        self.screen_calls: list[dict[str, Any]] = []
        self.results = [
            _analysis("ASML.AS", "ASML Holding", "Technology", 82.5, "scored", 0.90),
            _analysis("SAP.DE", "SAP", "Technology", 64.0, "scored", 1.00),
            _analysis(
                "ALV.DE",
                "Allianz",
                "Financials",
                None,
                "not_scored_financials",
                0.86,
                warnings=["Financial companies are not scored by the default model."],
            ),
            _analysis(
                "THIN.DE",
                "Thin Data AG",
                "Industrials",
                None,
                "insufficient_data",
                0.29,
                missing_metrics=["pe_ratio", "ev_to_ebitda"],
                warnings=["Data completeness is below 0.40."],
                error="Provider data unavailable",
            ),
        ]

    def get_company_analysis(self, ticker: str) -> dict[str, Any]:
        if ticker == "FAIL.DE":
            raise RuntimeError("ticker failed")
        for result in self.results:
            if result["company"]["ticker"] == ticker:
                return result
        raise KeyError(f"Ticker not found in universe: {ticker}")

    def screen(
        self,
        limit: int | None = None,
        min_score: float | None = None,
        include_unscored: bool = False,
        sort_by: str = "score",
    ) -> list[dict[str, Any]]:
        self.screen_calls.append(
            {
                "limit": limit,
                "min_score": min_score,
                "include_unscored": include_unscored,
                "sort_by": sort_by,
            }
        )
        rows = []
        for result in self.results:
            score_value = result["score"]["score"] if result.get("score") else None
            has_provider_error = result.get("error") == "Provider data unavailable"
            if score_value is None and not include_unscored:
                if not (has_provider_error and min_score is None):
                    continue
            if score_value is not None and min_score is not None and score_value < min_score:
                continue
            rows.append(result)

        if sort_by == "data_completeness":
            rows.sort(key=lambda item: item["data_quality"]["data_completeness"], reverse=True)
        else:
            rows.sort(key=lambda item: item["score"]["score"] if item.get("score") else -1, reverse=True)

        return rows[:limit] if limit is not None else rows


class CliTest(unittest.TestCase):
    def test_default_cli_run_prints_screen_table(self) -> None:
        output = self._run([])

        self.assertIn("ticker", output)
        self.assertIn("score_status", output)
        self.assertIn("data_completeness", output)
        self.assertIn("ASML.AS", output)
        self.assertNotIn("ALV.DE", output)

    def test_single_ticker_json_output_preserves_score_details(self) -> None:
        output = self._run(["--ticker", "ASML.AS", "--json"])

        payload = json.loads(output)
        self.assertEqual(payload["company"]["ticker"], "ASML.AS")
        self.assertIn("score_breakdown", payload["score"])
        self.assertIn("data_quality", payload)

    def test_limit_is_passed_to_screener(self) -> None:
        fake = FakeCliScreener()
        output = self._run(["--limit", "1"], fake)

        self.assertEqual(fake.screen_calls[-1]["limit"], 1)
        self.assertIn("ASML.AS", output)
        self.assertNotIn("SAP.DE", output)

    def test_min_score_is_passed_to_screener(self) -> None:
        fake = FakeCliScreener()
        output = self._run(["--min-score", "70"], fake)

        self.assertEqual(fake.screen_calls[-1]["min_score"], 70.0)
        self.assertIn("ASML.AS", output)
        self.assertNotIn("SAP.DE", output)

    def test_sort_by_data_completeness_is_passed_to_screener(self) -> None:
        fake = FakeCliScreener()
        output = self._run(["--sort", "data_completeness"], fake)

        self.assertEqual(fake.screen_calls[-1]["sort_by"], "data_completeness")
        self.assertLess(output.index("SAP.DE"), output.index("ASML.AS"))

    def test_include_unscored_shows_unscored_companies_clearly(self) -> None:
        fake = FakeCliScreener()
        output = self._run(["--include-unscored"], fake)

        self.assertTrue(fake.screen_calls[-1]["include_unscored"])
        self.assertIn("ALV.DE", output)
        self.assertIn("THIN.DE", output)
        self.assertIn("not_scored_financials", output)
        self.assertIn("insufficient_data", output)
        self.assertIn("unscored", output)
        self.assertIn("Warning: THIN.DE: Provider data unavailable", output)

    def test_failed_single_ticker_does_not_crash(self) -> None:
        output = self._run(["--ticker", "FAIL.DE"])

        self.assertIn("Error: FAIL.DE: ticker failed", output)

    def test_failed_single_ticker_json_is_valid_json(self) -> None:
        output = self._run(["--ticker", "FAIL.DE", "--json"])

        payload = json.loads(output)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["ticker"], "FAIL.DE")
        self.assertIn("ticker failed", payload["error"])

    def _run(self, args: list[str], screener: FakeCliScreener | None = None) -> str:
        stream = io.StringIO()
        with redirect_stdout(stream):
            main(args, screener=screener or FakeCliScreener())
        return stream.getvalue()


if __name__ == "__main__":
    unittest.main()
