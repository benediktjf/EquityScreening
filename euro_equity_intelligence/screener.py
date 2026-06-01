"""Application service for screening the equity universe."""

from __future__ import annotations

from typing import Any

from .data_provider import DataProvider, YFinanceDataProvider
from .metrics import EquityMetrics, calculate_metrics, missing_metric_names
from .scoring import score_metrics
from .universe import EUROPEAN_UNIVERSE, Company, get_company, list_companies


class EquityScreener:
    """Coordinate data retrieval, metric calculation, scoring, and ranking."""

    def __init__(
        self,
        data_provider: DataProvider | None = None,
        universe: tuple[Company, ...] = EUROPEAN_UNIVERSE,
    ) -> None:
        self._data_provider = data_provider or YFinanceDataProvider()
        self._universe = universe

    def list_companies(self) -> list[dict[str, str]]:
        """Return metadata for the configured equity universe."""
        return [company.to_dict() for company in self._universe]

    def get_company_analysis(self, ticker: str) -> dict[str, Any]:
        """Analyze one ticker and return a stable API/CLI response shape."""
        company = self._find_company(ticker)

        try:
            data = self._data_provider.get_company_data(company.ticker)
        except Exception as exc:
            return _unavailable_analysis(company, str(exc))

        metrics = calculate_metrics(data)
        score = score_metrics(metrics)
        return {
            "company": company.to_dict(),
            "market": _market_snapshot(data),
            "metrics": metrics.to_dict(),
            "score": score.to_dict(),
            "data_quality": _data_quality(metrics, source_error=None),
        }

    def screen(self, limit: int | None = None, min_score: float | None = None) -> list[dict[str, Any]]:
        """Rank the universe by score, optionally filtering by a minimum score."""
        results = []
        for company in self._universe:
            try:
                analysis = self.get_company_analysis(company.ticker)
            except Exception as exc:
                analysis = {
                    "company": company.to_dict(),
                    "market": {},
                    "metrics": {},
                    "score": None,
                    "data_quality": {
                        "missing_metrics": [],
                        "data_completeness": 0.0,
                        "warnings": ["Unexpected screening error."],
                    },
                    "error": str(exc),
                }
            score = analysis["score"]["score"] if analysis.get("score") else None
            if min_score is not None and (score is None or score < min_score):
                continue
            results.append(analysis)

        results.sort(key=lambda item: item["score"]["score"] if item.get("score") else -1, reverse=True)
        return results[:limit] if limit is not None else results

    def _find_company(self, ticker: str) -> Company:
        """Find a company in the active universe by ticker."""
        if self._universe == EUROPEAN_UNIVERSE:
            return get_company(ticker)

        normalized = ticker.upper()
        for company in self._universe:
            if company.ticker.upper() == normalized:
                return company
        raise KeyError(f"Ticker not found in universe: {ticker}")


def default_companies() -> list[dict[str, str]]:
    """Return the default 20-company European universe."""
    return list_companies()


def _market_snapshot(data) -> dict[str, Any]:
    info = data.info or {}
    return {
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "last_close": _last_close(data),
    }


def _last_close(data) -> float | None:
    history = data.price_history
    if history is None or history.empty or "Close" not in history.columns:
        return None
    close = history["Close"].dropna()
    if close.empty:
        return None
    return float(close.iloc[-1])


def _data_quality(metrics: EquityMetrics, source_error: str | None) -> dict[str, Any]:
    missing_metrics = missing_metric_names(metrics)
    data_completeness = round((len(metrics.to_dict()) - len(missing_metrics)) / len(metrics.to_dict()), 2)
    warnings = []
    if source_error:
        warnings.append(f"Data provider error: {source_error}")
    if missing_metrics:
        warnings.append("Some metrics could not be calculated from available yfinance data.")
    if len(missing_metrics) == len(metrics.to_dict()):
        warnings.append("No usable financial metrics were available; score is neutral by design.")
    return {
        "missing_metrics": missing_metrics,
        "data_completeness": data_completeness,
        "warnings": warnings,
    }


def _unavailable_analysis(company: Company, error: str) -> dict[str, Any]:
    metrics = EquityMetrics(
        revenue_growth=None,
        ebitda_margin=None,
        net_debt_to_ebitda=None,
        pe_ratio=None,
        ev_to_ebitda=None,
        roe=None,
        free_cash_flow_yield=None,
    )
    score = score_metrics(metrics)
    return {
        "company": company.to_dict(),
        "market": {},
        "metrics": metrics.to_dict(),
        "score": score.to_dict(),
        "data_quality": _data_quality(metrics, source_error=error),
        "error": error,
    }
