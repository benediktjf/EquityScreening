"""Financial metric calculations for equity screening."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable

import numpy as np
import pandas as pd

from .data_provider import FinancialData


@dataclass(frozen=True)
class EquityMetrics:
    """Normalized financial metrics used by the scoring model."""

    revenue_growth: float | None
    ebitda_margin: float | None
    net_debt_to_ebitda: float | None
    pe_ratio: float | None
    ev_to_ebitda: float | None
    roe: float | None
    free_cash_flow_yield: float | None

    def to_dict(self) -> dict[str, float | None]:
        return asdict(self)


FINANCIAL_ALIASES = {
    "revenue": ("Total Revenue", "Operating Revenue"),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "total_debt": ("Total Debt", "Long Term Debt And Capital Lease Obligation"),
    "cash": ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
    "equity": ("Stockholders Equity", "Total Equity Gross Minority Interest"),
    "free_cash_flow": ("Free Cash Flow",),
}


def calculate_metrics(data: FinancialData) -> EquityMetrics:
    """Calculate valuation and quality metrics from yfinance-style company data.

    Missing statements, missing rows, non-numeric values, and divide-by-zero
    cases are returned as ``None`` instead of raising.
    """
    info = data.info or {}

    revenue_latest = _statement_value(data.financials, FINANCIAL_ALIASES["revenue"], offset=0)
    revenue_previous = _statement_value(data.financials, FINANCIAL_ALIASES["revenue"], offset=1)
    ebitda = _statement_value(data.financials, FINANCIAL_ALIASES["ebitda"], offset=0)
    net_income = _statement_value(data.financials, FINANCIAL_ALIASES["net_income"], offset=0)
    total_debt = _statement_value(data.balance_sheet, FINANCIAL_ALIASES["total_debt"], offset=0)
    cash = _statement_value(data.balance_sheet, FINANCIAL_ALIASES["cash"], offset=0)
    equity = _statement_value(data.balance_sheet, FINANCIAL_ALIASES["equity"], offset=0)
    free_cash_flow = _statement_value(data.cash_flow, FINANCIAL_ALIASES["free_cash_flow"], offset=0)

    market_cap = _number(info.get("marketCap"))
    enterprise_value = _number(info.get("enterpriseValue"))

    revenue_growth = _first_valid(
        _number(info.get("revenueGrowth")),
        _safe_divide(_difference(revenue_latest, revenue_previous), abs(revenue_previous) if revenue_previous else None),
    )
    ebitda_margin = _first_valid(
        _number(info.get("ebitdaMargins")),
        _safe_divide(ebitda, revenue_latest),
    )
    net_debt_to_ebitda = _safe_divide(
        _difference(total_debt, cash),
        ebitda,
    )
    pe_ratio = _first_valid(
        _number(info.get("trailingPE")),
        _safe_divide(market_cap, net_income),
    )
    ev_to_ebitda = _first_valid(
        _number(info.get("enterpriseToEbitda")),
        _safe_divide(enterprise_value, ebitda),
    )
    roe = _first_valid(
        _number(info.get("returnOnEquity")),
        _safe_divide(net_income, equity),
    )
    free_cash_flow_yield = _first_valid(
        _safe_divide(_number(info.get("freeCashflow")), market_cap),
        _safe_divide(free_cash_flow, market_cap),
    )

    return EquityMetrics(
        revenue_growth=_clean(revenue_growth),
        ebitda_margin=_clean(ebitda_margin),
        net_debt_to_ebitda=_clean(net_debt_to_ebitda),
        pe_ratio=_clean(pe_ratio),
        ev_to_ebitda=_clean(ev_to_ebitda),
        roe=_clean(roe),
        free_cash_flow_yield=_clean(free_cash_flow_yield),
    )


def missing_metric_names(metrics: EquityMetrics) -> list[str]:
    """Return metric keys whose values could not be calculated."""
    return [name for name, value in metrics.to_dict().items() if value is None]


def _statement_value(frame: pd.DataFrame | None, aliases: Iterable[str], offset: int = 0) -> float | None:
    if frame is None or frame.empty:
        return None

    alias_lookup = {str(index).strip().lower(): index for index in frame.index}
    for alias in aliases:
        index = alias_lookup.get(alias.lower())
        if index is None:
            continue
        values = _ordered_numeric_values(frame.loc[index])
        if len(values) > offset:
            return values[offset]
    return None


def _ordered_numeric_values(values: pd.Series | pd.DataFrame) -> list[float]:
    if isinstance(values, pd.DataFrame):
        return _ordered_values_from_duplicate_rows(values)

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return []

    sortable_index = pd.to_datetime(numeric.index, errors="coerce")
    if sortable_index.notna().all():
        ordered = numeric.iloc[np.argsort(sortable_index)[::-1]]
    else:
        ordered = numeric
    return [float(value) for value in ordered if _clean(value) is not None]


def _ordered_values_from_duplicate_rows(frame: pd.DataFrame) -> list[float]:
    values_by_period = {}
    for column in frame.columns:
        numeric = pd.to_numeric(frame[column], errors="coerce").dropna()
        if not numeric.empty:
            values_by_period[column] = numeric.iloc[0]
    return _ordered_numeric_values(pd.Series(values_by_period))


def _first_valid(*values: float | None) -> float | None:
    for value in values:
        if _clean(value) is not None:
            return float(value)
    return None


def _difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _number(value) -> float | None:
    try:
        return _clean(float(value))
    except (TypeError, ValueError):
        return None


def _clean(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) if isfinite(float(value)) else None
