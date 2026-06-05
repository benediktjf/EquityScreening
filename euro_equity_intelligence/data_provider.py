"""Data access layer for market and financial statement data."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import io
import logging
from typing import Any, Callable, Protocol
import warnings

import pandas as pd


PROVIDER_DATA_UNAVAILABLE = "Provider data unavailable"
_USABLE_INFO_FIELDS = {
    "currency",
    "marketCap",
    "enterpriseValue",
    "revenueGrowth",
    "ebitdaMargins",
    "operatingMargins",
    "profitMargins",
    "trailingPE",
    "enterpriseToEbitda",
    "enterpriseToRevenue",
    "returnOnEquity",
    "returnOnCapital",
    "freeCashflow",
}


class ProviderDataUnavailable(RuntimeError):
    """Raised when the provider returns no usable market or financial data."""


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

    def __init__(self, history_period: str = "2y", yf_module: Any | None = None) -> None:
        if yf_module is None:
            import yfinance as yf
        else:
            yf = yf_module

        self._yf = yf
        self._history_period = history_period
        self._cache: dict[str, FinancialData] = {}

    def get_company_data(self, ticker: str) -> FinancialData:
        """Fetch market, income statement, balance sheet, and cash flow data."""
        normalized = ticker.upper()
        if normalized in self._cache:
            return self._cache[normalized]

        with _suppress_provider_output():
            yf_ticker = self._yf.Ticker(normalized)
            data = FinancialData(
                ticker=normalized,
                info=self._safe_info(yf_ticker),
                financials=self._safe_frame(lambda: yf_ticker.financials),
                balance_sheet=self._safe_frame(lambda: yf_ticker.balance_sheet),
                cash_flow=self._safe_frame(lambda: yf_ticker.cashflow),
                price_history=self._safe_frame(lambda: yf_ticker.history(period=self._history_period)),
            )
        if not _has_usable_data(data):
            raise ProviderDataUnavailable(PROVIDER_DATA_UNAVAILABLE)

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


def _has_usable_data(data: FinancialData) -> bool:
    info = data.info or {}
    if any(info.get(field) is not None for field in _USABLE_INFO_FIELDS):
        return True
    return any(
        not frame.empty
        for frame in (
            data.financials,
            data.balance_sheet,
            data.cash_flow,
            data.price_history,
        )
    )


@contextlib.contextmanager
def _suppress_provider_output():
    logger = logging.getLogger("yfinance")
    previous_disabled = logger.disabled
    previous_level = logger.level
    with (
        warnings.catch_warnings(),
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        warnings.simplefilter("ignore")
        logger.disabled = True
        logger.setLevel(logging.CRITICAL + 1)
        try:
            yield
        finally:
            logger.disabled = previous_disabled
            logger.setLevel(previous_level)
