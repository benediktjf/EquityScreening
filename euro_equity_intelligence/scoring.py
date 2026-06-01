"""Score financial metrics on a 0-100 scale."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .metrics import EquityMetrics


WEIGHTS = {
    "revenue_growth": 0.15,
    "ebitda_margin": 0.15,
    "net_debt_to_ebitda": 0.15,
    "pe_ratio": 0.15,
    "ev_to_ebitda": 0.15,
    "roe": 0.15,
    "free_cash_flow_yield": 0.10,
}


@dataclass(frozen=True)
class ScoreResult:
    """Final score, component scores, and source-data completeness."""

    score: float
    components: dict[str, float]
    data_completeness: float

    def to_dict(self) -> dict:
        return asdict(self)


def score_metrics(metrics: EquityMetrics) -> ScoreResult:
    """Convert financial metrics into a weighted 0-100 score."""
    raw_values = metrics.to_dict()
    components = {
        "revenue_growth": _higher_is_better(raw_values["revenue_growth"], low=-0.10, high=0.20),
        "ebitda_margin": _higher_is_better(raw_values["ebitda_margin"], low=0.00, high=0.30),
        "net_debt_to_ebitda": _lower_is_better(
            raw_values["net_debt_to_ebitda"],
            low=0.00,
            high=5.00,
            allow_non_positive=True,
        ),
        "pe_ratio": _lower_is_better(raw_values["pe_ratio"], low=8.00, high=35.00),
        "ev_to_ebitda": _lower_is_better(raw_values["ev_to_ebitda"], low=6.00, high=20.00),
        "roe": _higher_is_better(raw_values["roe"], low=0.00, high=0.25),
        "free_cash_flow_yield": _higher_is_better(raw_values["free_cash_flow_yield"], low=0.00, high=0.10),
    }
    weighted_score = sum(components[name] * WEIGHTS[name] for name in WEIGHTS)
    present_count = sum(1 for value in raw_values.values() if value is not None)

    return ScoreResult(
        score=round(float(weighted_score), 2),
        components={name: round(value, 2) for name, value in components.items()},
        data_completeness=round(present_count / len(raw_values), 2),
    )


def _higher_is_better(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 50.0
    return _scale(value, low=low, high=high)


def _lower_is_better(
    value: float | None,
    low: float,
    high: float,
    allow_non_positive: bool = False,
) -> float:
    if value is None:
        return 50.0
    if value <= 0 and not allow_non_positive:
        return 10.0
    return 100.0 - _scale(value, low=low, high=high)


def _scale(value: float, low: float, high: float) -> float:
    if high <= low:
        raise ValueError("high must be greater than low")
    return float(np.clip((value - low) / (high - low) * 100.0, 0.0, 100.0))
