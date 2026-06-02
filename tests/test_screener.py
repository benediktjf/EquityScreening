from __future__ import annotations

import unittest

import pandas as pd

from euro_equity_intelligence.data_provider import FinancialData
from euro_equity_intelligence.screener import (
    FINANCIAL_MODEL_WARNING,
    INSUFFICIENT_DATA_WARNING,
    PARTIAL_DATA_WARNING,
    EquityScreener,
)
from euro_equity_intelligence.universe import Company


class FakeProvider:
    def get_company_data(self, ticker: str) -> FinancialData:
        revenue = 1_200.0 if ticker == "GOOD.DE" else 900.0
        return FinancialData(
            ticker=ticker,
            info={"marketCap": 2_000.0, "enterpriseValue": 2_400.0},
            financials=pd.DataFrame(
                {
                    "2025-12-31": [revenue, 300.0, 100.0],
                    "2024-12-31": [1_000.0, 200.0, 80.0],
                },
                index=["Total Revenue", "EBITDA", "Net Income"],
            ),
            balance_sheet=pd.DataFrame(
                {"2025-12-31": [500.0, 100.0, 800.0]},
                index=["Total Debt", "Cash And Cash Equivalents", "Stockholders Equity"],
            ),
            cash_flow=pd.DataFrame({"2025-12-31": [120.0]}, index=["Free Cash Flow"]),
            price_history=pd.DataFrame({"Close": [10.0, 11.5]}),
        )


class BrokenProvider:
    def get_company_data(self, ticker: str) -> FinancialData:
        raise RuntimeError("financial statements unavailable")


class PartialProvider:
    def get_company_data(self, ticker: str) -> FinancialData:
        return FinancialData(
            ticker=ticker,
            info={
                "revenueGrowth": 0.05,
                "ebitdaMargins": 0.20,
                "trailingPE": 18.0,
            },
            financials=pd.DataFrame(),
            balance_sheet=pd.DataFrame(),
            cash_flow=pd.DataFrame(),
            price_history=pd.DataFrame({"Close": [20.0]}),
        )


class InsufficientProvider:
    def get_company_data(self, ticker: str) -> FinancialData:
        return FinancialData(
            ticker=ticker,
            info={"revenueGrowth": 0.05},
            financials=pd.DataFrame(),
            balance_sheet=pd.DataFrame(),
            cash_flow=pd.DataFrame(),
            price_history=pd.DataFrame({"Close": [20.0]}),
        )


class ScreenerTest(unittest.TestCase):
    def test_screener_lists_and_sorts_results(self) -> None:
        universe = (
            Company("GOOD.DE", "Good AG", "Germany", "Xetra", "Industrials"),
            Company("WEAK.DE", "Weak AG", "Germany", "Xetra", "Industrials"),
        )
        screener = EquityScreener(data_provider=FakeProvider(), universe=universe)

        results = screener.screen()

        self.assertEqual([result["company"]["ticker"] for result in results], ["GOOD.DE", "WEAK.DE"])
        self.assertGreater(results[0]["score"]["score"], results[1]["score"]["score"])

    def test_screener_can_analyze_single_company(self) -> None:
        universe = (Company("GOOD.DE", "Good AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=FakeProvider(), universe=universe)

        result = screener.get_company_analysis("good.de")

        self.assertEqual(result["company"]["ticker"], "GOOD.DE")
        self.assertEqual(result["market"]["last_close"], 11.5)
        self.assertEqual(result["metrics"]["revenue_growth"], 0.2)
        self.assertGreaterEqual(result["score"]["score"], 0)
        self.assertEqual(result["score_status"], "scored")
        self.assertEqual(result["data_quality"]["missing_metrics"], [])
        self.assertEqual(result["data_quality"]["data_completeness"], 1.0)

    def test_company_with_provider_error_is_insufficient_data(self) -> None:
        universe = (Company("BROKEN.DE", "Broken AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=BrokenProvider(), universe=universe)

        result = screener.get_company_analysis("BROKEN.DE")

        self.assertEqual(result["company"]["ticker"], "BROKEN.DE")
        self.assertEqual(result["market"], {})
        self.assertEqual(
            result["metrics"],
            {
                "revenue_growth": None,
                "ebitda_margin": None,
                "net_debt_to_ebitda": None,
                "pe_ratio": None,
                "ev_to_ebitda": None,
                "roe": None,
                "free_cash_flow_yield": None,
            },
        )
        self.assertIsNone(result["score"])
        self.assertEqual(result["score_status"], "insufficient_data")
        self.assertEqual(result["data_quality"]["data_completeness"], 0.0)
        self.assertEqual(len(result["data_quality"]["missing_metrics"]), 7)
        self.assertIn("financial statements unavailable", result["error"])
        self.assertIn(INSUFFICIENT_DATA_WARNING, result["data_quality"]["warnings"])
        self.assertTrue(any("Data provider error" in warning for warning in result["data_quality"]["warnings"]))

    def test_partial_data_company_is_estimated_but_visible(self) -> None:
        universe = (Company("PART.DE", "Partial AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=PartialProvider(), universe=universe)

        result = screener.get_company_analysis("PART.DE")

        self.assertEqual(result["score_status"], "estimated_partial_data")
        self.assertIsNotNone(result["score"])
        self.assertEqual(result["score"]["data_completeness"], 0.43)
        self.assertEqual(result["data_quality"]["data_completeness"], 0.43)
        self.assertIn("net_debt_to_ebitda", result["data_quality"]["missing_metrics"])
        self.assertIn(PARTIAL_DATA_WARNING, result["data_quality"]["warnings"])

    def test_insufficient_data_company_is_unscored(self) -> None:
        universe = (Company("THIN.DE", "Thin AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=InsufficientProvider(), universe=universe)

        result = screener.get_company_analysis("THIN.DE")

        self.assertEqual(result["score_status"], "insufficient_data")
        self.assertIsNone(result["score"])
        self.assertEqual(result["data_quality"]["data_completeness"], 0.14)
        self.assertIn(INSUFFICIENT_DATA_WARNING, result["data_quality"]["warnings"])

    def test_financial_company_endpoint_is_marked_unscored(self) -> None:
        universe = (Company("BANK.DE", "Bank AG", "Germany", "Xetra", "Financials"),)
        screener = EquityScreener(data_provider=FakeProvider(), universe=universe)

        result = screener.get_company_analysis("BANK.DE")

        self.assertEqual(result["company"]["sector"], "Financials")
        self.assertEqual(result["market"]["last_close"], 11.5)
        self.assertIsNone(result["score"])
        self.assertEqual(result["score_status"], "not_scored_financials")
        self.assertIn(FINANCIAL_MODEL_WARNING, result["data_quality"]["warnings"])

    def test_screen_excludes_financial_companies_by_default(self) -> None:
        universe = (
            Company("GOOD.DE", "Good AG", "Germany", "Xetra", "Industrials"),
            Company("BANK.DE", "Bank AG", "Germany", "Xetra", "Financials"),
        )
        screener = EquityScreener(data_provider=FakeProvider(), universe=universe)

        results = screener.screen()

        self.assertEqual([result["company"]["ticker"] for result in results], ["GOOD.DE"])

    def test_screen_can_include_unscored_financial_companies(self) -> None:
        universe = (
            Company("GOOD.DE", "Good AG", "Germany", "Xetra", "Industrials"),
            Company("BANK.DE", "Bank AG", "Germany", "Xetra", "Financials"),
        )
        screener = EquityScreener(data_provider=FakeProvider(), universe=universe)

        results = screener.screen(include_unscored=True, min_score=90)

        self.assertEqual([result["company"]["ticker"] for result in results], ["BANK.DE"])
        self.assertEqual(results[0]["score_status"], "not_scored_financials")
        self.assertIsNone(results[0]["score"])

    def test_screen_excludes_insufficient_data_by_default(self) -> None:
        universe = (
            Company("GOOD.DE", "Good AG", "Germany", "Xetra", "Industrials"),
            Company("THIN.DE", "Thin AG", "Germany", "Xetra", "Industrials"),
        )

        class MixedProvider:
            def get_company_data(self, ticker: str) -> FinancialData:
                if ticker == "THIN.DE":
                    return InsufficientProvider().get_company_data(ticker)
                return FakeProvider().get_company_data(ticker)

        screener = EquityScreener(data_provider=MixedProvider(), universe=universe)

        results = screener.screen()

        self.assertEqual([result["company"]["ticker"] for result in results], ["GOOD.DE"])

    def test_screen_can_include_insufficient_data_when_requested(self) -> None:
        universe = (Company("THIN.DE", "Thin AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=InsufficientProvider(), universe=universe)

        results = screener.screen(include_unscored=True)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["company"]["ticker"], "THIN.DE")
        self.assertEqual(results[0]["score_status"], "insufficient_data")
        self.assertIsNone(results[0]["score"])


if __name__ == "__main__":
    unittest.main()
