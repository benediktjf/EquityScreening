from __future__ import annotations

import unittest

import pandas as pd

from euro_equity_intelligence.data_provider import FinancialData
from euro_equity_intelligence.screener import EquityScreener
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
        self.assertEqual(result["data_quality"]["missing_metrics"], [])
        self.assertEqual(result["data_quality"]["data_completeness"], 1.0)

    def test_screen_continues_when_one_company_has_no_data(self) -> None:
        universe = (Company("BROKEN.DE", "Broken AG", "Germany", "Xetra", "Industrials"),)
        screener = EquityScreener(data_provider=BrokenProvider(), universe=universe)

        results = screener.screen()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["company"]["ticker"], "BROKEN.DE")
        self.assertEqual(results[0]["market"], {})
        self.assertEqual(
            results[0]["metrics"],
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
        self.assertEqual(results[0]["score"]["score"], 50.0)
        self.assertEqual(results[0]["data_quality"]["data_completeness"], 0.0)
        self.assertEqual(len(results[0]["data_quality"]["missing_metrics"]), 7)
        self.assertIn("financial statements unavailable", results[0]["error"])
        self.assertIn("Data provider error", results[0]["data_quality"]["warnings"][0])


if __name__ == "__main__":
    unittest.main()
