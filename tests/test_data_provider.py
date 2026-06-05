from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

import pandas as pd

from euro_equity_intelligence.data_provider import (
    PROVIDER_DATA_UNAVAILABLE,
    ProviderDataUnavailable,
    YFinanceDataProvider,
)


class NoisyUnavailableTicker:
    @property
    def info(self) -> dict:
        print("HTTP Error 404: raw yahoo message")
        print("$ROG.SW: possibly delisted; no price data found", file=sys.stderr)
        raise RuntimeError("raw provider exception")

    @property
    def financials(self) -> pd.DataFrame:
        print("financials unavailable", file=sys.stderr)
        return pd.DataFrame()

    @property
    def balance_sheet(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def cashflow(self) -> pd.DataFrame:
        return pd.DataFrame()

    def history(self, period: str) -> pd.DataFrame:
        print("history unavailable", file=sys.stderr)
        return pd.DataFrame()


class NoisyPriceOnlyFailureTicker:
    @property
    def info(self) -> dict:
        return {"marketCap": 1_000.0, "enterpriseValue": 1_200.0}

    @property
    def financials(self) -> pd.DataFrame:
        return pd.DataFrame({"2025-12-31": [1_000.0]}, index=["Total Revenue"])

    @property
    def balance_sheet(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def cashflow(self) -> pd.DataFrame:
        return pd.DataFrame()

    def history(self, period: str) -> pd.DataFrame:
        print("$ROG.SW: possibly delisted; no price data found", file=sys.stderr)
        return pd.DataFrame()


class FakeUnavailableYFinance:
    @staticmethod
    def Ticker(ticker: str) -> NoisyUnavailableTicker:
        print(f"creating ticker {ticker}", file=sys.stderr)
        return NoisyUnavailableTicker()


class FakePartialYFinance:
    @staticmethod
    def Ticker(ticker: str) -> NoisyPriceOnlyFailureTicker:
        return NoisyPriceOnlyFailureTicker()


class YFinanceDataProviderTest(unittest.TestCase):
    def test_suppresses_raw_yfinance_output_when_provider_data_is_unavailable(self) -> None:
        provider = YFinanceDataProvider(yf_module=FakeUnavailableYFinance)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(ProviderDataUnavailable) as exc:
                provider.get_company_data("ROG.SW")

        self.assertEqual(str(exc.exception), PROVIDER_DATA_UNAVAILABLE)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_missing_price_history_does_not_make_other_usable_data_unavailable(self) -> None:
        provider = YFinanceDataProvider(yf_module=FakePartialYFinance)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            data = provider.get_company_data("ROG.SW")

        self.assertEqual(data.info["marketCap"], 1_000.0)
        self.assertFalse(data.financials.empty)
        self.assertTrue(data.price_history.empty)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
