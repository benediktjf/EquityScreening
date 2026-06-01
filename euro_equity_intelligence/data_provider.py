"""Data access layer for market and financial statement data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import pandas as pd


@dataclass(frozen=True)
class FinancialData:
    """Raw market and statement data for one company."""

    ticker: str
    info: dict[str, Any]
    financials: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    price_history: pd.DataFrame = field(default_factory=pd.DataFrame)


class DataProvider(Protocol):
    def get_company_data(self, ticker: str) -> FinancialData:
        """Return market data and financial statements for a ticker."""


class YFinanceDataProvider:
    """Fetch company data from yfinance with a small in-memory cache."""

    def __init__(self, history_period: str = "2y") -> None:
        import yfinance as yf

        self._yf = yf
        self._history_period = history_period
        self._cache: dict[str, FinancialData] = {}

    def get_company_data(self, ticker: str) -> FinancialData:
        """Fetch market, income statement, balance sheet, and cash flow data."""
        normalized = ticker.upper()
        if normalized in self._cache:
            return self._cache[normalized]

        yf_ticker = self._yf.Ticker(normalized)
        data = FinancialData(
            ticker=normalized,
            info=self._safe_info(yf_ticker),
            financials=self._safe_frame(lambda: yf_ticker.financials),
            balance_sheet=self._safe_frame(lambda: yf_ticker.balance_sheet),
            cash_flow=self._safe_frame(lambda: yf_ticker.cashflow),
            price_history=self._safe_frame(lambda: yf_ticker.history(period=self._history_period)),
        )
        self._cache[normalized] = data
        return data

    @staticmethod
    def _safe_info(yf_ticker: Any) -> dict[str, Any]:
        try:
            return dict(yf_ticker.info or {})
        except Exception:
            return {}

    @staticmethod
    def _safe_frame(loader: Callable[[], Any]) -> pd.DataFrame:
        try:
            frame = loader()
        except Exception:
            return pd.DataFrame()
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
