from __future__ import annotations

from math import isclose
import unittest

import pandas as pd

from euro_equity_intelligence.data_provider import FinancialData
from euro_equity_intelligence.metrics import calculate_metrics


class MetricsTest(unittest.TestCase):
    def test_calculate_metrics_from_financial_statements(self) -> None:
        data = FinancialData(
            ticker="TEST.DE",
            info={"marketCap": 2_000.0, "enterpriseValue": 2_400.0},
            financials=pd.DataFrame(
                {
                    "2025-12-31": [1_200.0, 300.0, 100.0],
                    "2024-12-31": [1_000.0, 200.0, 80.0],
                },
                index=["Total Revenue", "EBITDA", "Net Income"],
            ),
            balance_sheet=pd.DataFrame(
                {"2025-12-31": [500.0, 100.0, 800.0]},
                index=["Total Debt", "Cash And Cash Equivalents", "Stockholders Equity"],
            ),
            cash_flow=pd.DataFrame(
                {"2025-12-31": [120.0]},
                index=["Free Cash Flow"],
            ),
        )

        metrics = calculate_metrics(data)

        self.assertTrue(isclose(metrics.revenue_growth, 0.20))
        self.assertTrue(isclose(metrics.ebitda_margin, 0.25))
        self.assertTrue(isclose(metrics.net_debt_to_ebitda, 1.333333, rel_tol=1e-5))
        self.assertTrue(isclose(metrics.pe_ratio, 20.0))
        self.assertTrue(isclose(metrics.ev_to_ebitda, 8.0))
        self.assertTrue(isclose(metrics.roe, 0.125))
        self.assertTrue(isclose(metrics.free_cash_flow_yield, 0.06))

    def test_info_values_take_precedence_over_statement_fallbacks(self) -> None:
        data = FinancialData(
            ticker="TEST.DE",
            info={
                "marketCap": 2_000.0,
                "revenueGrowth": 0.05,
                "ebitdaMargins": 0.18,
                "trailingPE": 15.0,
                "enterpriseToEbitda": 9.0,
                "returnOnEquity": 0.20,
                "freeCashflow": 150.0,
            },
            financials=pd.DataFrame(
                {
                    "2025-12-31": [1_200.0, 300.0, 100.0],
                    "2024-12-31": [1_000.0, 200.0, 80.0],
                },
                index=["Total Revenue", "EBITDA", "Net Income"],
            ),
            balance_sheet=pd.DataFrame(),
            cash_flow=pd.DataFrame(),
        )

        metrics = calculate_metrics(data)

        self.assertTrue(isclose(metrics.revenue_growth, 0.05))
        self.assertTrue(isclose(metrics.ebitda_margin, 0.18))
        self.assertTrue(isclose(metrics.pe_ratio, 15.0))
        self.assertTrue(isclose(metrics.ev_to_ebitda, 9.0))
        self.assertTrue(isclose(metrics.roe, 0.20))
        self.assertTrue(isclose(metrics.free_cash_flow_yield, 0.075))

    def test_missing_financial_data_returns_empty_metrics_instead_of_crashing(self) -> None:
        data = FinancialData(
            ticker="MISSING.DE",
            info={},
            financials=pd.DataFrame(),
            balance_sheet=pd.DataFrame(),
            cash_flow=pd.DataFrame(),
        )

        metrics = calculate_metrics(data)

        self.assertEqual(
            metrics.to_dict(),
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

    def test_duplicate_statement_rows_and_non_numeric_cells_are_tolerated(self) -> None:
        data = FinancialData(
            ticker="DUP.DE",
            info={"marketCap": 1_000.0, "enterpriseValue": 1_200.0},
            financials=pd.DataFrame(
                {
                    "2025-12-31": ["not available", 1_100.0, 250.0, 90.0],
                    "2024-12-31": [900.0, None, 200.0, 75.0],
                },
                index=["Total Revenue", "Total Revenue", "EBITDA", "Net Income"],
            ),
            balance_sheet=pd.DataFrame(
                {"2025-12-31": [300.0, 50.0, 600.0]},
                index=["Total Debt", "Cash And Cash Equivalents", "Stockholders Equity"],
            ),
            cash_flow=pd.DataFrame({"2025-12-31": [100.0]}, index=["Free Cash Flow"]),
        )

        metrics = calculate_metrics(data)

        self.assertTrue(isclose(metrics.revenue_growth, 2 / 9))
        self.assertTrue(isclose(metrics.ebitda_margin, 250 / 1_100))
        self.assertTrue(isclose(metrics.free_cash_flow_yield, 0.10))


if __name__ == "__main__":
    unittest.main()
