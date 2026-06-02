"""Score financial metrics on a 0-100 scale."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .metrics import EquityMetrics


@dataclass(frozen=True)
class MetricScoreConfig:
    weight: float
    low: float
    high: float
    direction: str
    allow_non_positive: bool = False


METRIC_SCORE_CONFIG = {
    "revenue_growth": MetricScoreConfig(weight=0.15, low=-0.10, high=0.20, direction="higher_is_better"),
    "ebitda_margin": MetricScoreConfig(weight=0.15, low=0.00, high=0.30, direction="higher_is_better"),
    "net_debt_to_ebitda": MetricScoreConfig(
        weight=0.15,
        low=0.00,
        high=5.00,
        direction="lower_is_better",
        allow_non_positive=True,
    ),
    "pe_ratio": MetricScoreConfig(weight=0.15, low=8.00, high=35.00, direction="lower_is_better"),
    "ev_to_ebitda": MetricScoreConfig(weight=0.15, low=6.00, high=20.00, direction="lower_is_better"),
    "roe": MetricScoreConfig(weight=0.15, low=0.00, high=0.25, direction="higher_is_better"),
    "free_cash_flow_yield": MetricScoreConfig(weight=0.10, low=0.00, high=0.10, direction="higher_is_better"),
}

WEIGHTS = {name: config.weight for name, config in METRIC_SCORE_CONFIG.items()}


@dataclass(frozen=True)
class ScoreBreakdownItem:
    raw_value: float | None
    component_score: float
    weight: float
    weighted_contribution: float
    direction: str


@dataclass(frozen=True)
class ScoreResult:
    """Final score, component scores, score breakdown, and data completeness."""

    score: float
    components: dict[str, float]
    score_breakdown: dict[str, ScoreBreakdownItem]
    data_completeness: float

    def to_dict(self) -> dict:
        return asdict(self)


def score_metrics(metrics: EquityMetrics) -> ScoreResult:
    """Convert financial metrics into a weighted 0-100 score."""
    raw_values = metrics.to_dict()
    components = {
        name: round(_component_score(raw_values[name], config), 2)
        for name, config in METRIC_SCORE_CONFIG.items()
    }
    score_breakdown = {
        name: ScoreBreakdownItem(
            raw_value=raw_values[name],
            component_score=components[name],
            weight=config.weight,
            weighted_contribution=round(components[name] * config.weight, 2),
            direction=config.direction,
        )
        for name, config in METRIC_SCORE_CONFIG.items()
    }
    weighted_score = sum(item.weighted_contribution for item in score_breakdown.values())
    present_count = sum(1 for value in raw_values.values() if value is not None)

    return ScoreResult(
        score=round(float(weighted_score), 2),
        components=components,
        score_breakdown=score_breakdown,
        data_completeness=round(present_count / len(raw_values), 2),
    )


def _component_score(value: float | None, config: MetricScoreConfig) -> float:
    if config.direction == "higher_is_better":
        return _higher_is_better(value, low=config.low, high=config.high)
    if config.direction == "lower_is_better":
        return _lower_is_better(
            value,
            low=config.low,
            high=config.high,
            allow_non_positive=config.allow_non_positive,
        )
    raise ValueError(f"Unsupported scoring direction: {config.direction}")


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
