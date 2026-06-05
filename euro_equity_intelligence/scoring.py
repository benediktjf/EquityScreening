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
    category: str
    allow_non_positive: bool = False


METRIC_SCORE_CONFIG = {
    "revenue_growth": MetricScoreConfig(
        weight=0.15,
        low=-0.10,
        high=0.20,
        direction="higher_is_better",
        category="growth",
    ),
    "ebitda_margin": MetricScoreConfig(
        weight=0.06,
        low=0.00,
        high=0.30,
        direction="higher_is_better",
        category="profitability",
    ),
    "operating_margin": MetricScoreConfig(
        weight=0.06,
        low=0.00,
        high=0.25,
        direction="higher_is_better",
        category="profitability",
    ),
    "net_margin": MetricScoreConfig(
        weight=0.05,
        low=0.00,
        high=0.20,
        direction="higher_is_better",
        category="profitability",
    ),
    "roe": MetricScoreConfig(
        weight=0.06,
        low=0.00,
        high=0.25,
        direction="higher_is_better",
        category="profitability",
    ),
    "roic": MetricScoreConfig(
        weight=0.07,
        low=0.00,
        high=0.20,
        direction="higher_is_better",
        category="profitability",
    ),
    "pe_ratio": MetricScoreConfig(
        weight=0.08,
        low=8.00,
        high=35.00,
        direction="lower_is_better",
        category="valuation",
    ),
    "ev_to_ebitda": MetricScoreConfig(
        weight=0.08,
        low=6.00,
        high=20.00,
        direction="lower_is_better",
        category="valuation",
    ),
    "ev_to_sales": MetricScoreConfig(
        weight=0.09,
        low=0.50,
        high=8.00,
        direction="lower_is_better",
        category="valuation",
    ),
    "net_debt_to_ebitda": MetricScoreConfig(
        weight=0.08,
        low=0.00,
        high=5.00,
        direction="lower_is_better",
        category="balance_sheet",
        allow_non_positive=True,
    ),
    "interest_coverage": MetricScoreConfig(
        weight=0.07,
        low=1.00,
        high=12.00,
        direction="higher_is_better",
        category="balance_sheet",
    ),
    "free_cash_flow_yield": MetricScoreConfig(
        weight=0.08,
        low=0.00,
        high=0.10,
        direction="higher_is_better",
        category="cash_flow",
    ),
    "free_cash_flow_margin": MetricScoreConfig(
        weight=0.07,
        low=0.00,
        high=0.20,
        direction="higher_is_better",
        category="cash_flow",
    ),
}

WEIGHTS = {name: config.weight for name, config in METRIC_SCORE_CONFIG.items()}
CATEGORY_ORDER = ("growth", "profitability", "valuation", "balance_sheet", "cash_flow")
CATEGORY_WEIGHTS = {
    category: round(sum(config.weight for config in METRIC_SCORE_CONFIG.values() if config.category == category), 2)
    for category in CATEGORY_ORDER
}


@dataclass(frozen=True)
class ScoreBreakdownItem:
    raw_value: float | None
    component_score: float
    weight: float
    weighted_contribution: float
    direction: str
    category: str


@dataclass(frozen=True)
class ScoreResult:
    """Final score, category scores, metric scores, and model metric coverage."""

    score: float
    components: dict[str, float]
    category_scores: dict[str, float]
    score_breakdown: dict[str, ScoreBreakdownItem]
    metric_coverage: float

    @property
    def data_completeness(self) -> float:
        """Backward-compatible alias for metric_coverage."""
        return self.metric_coverage

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["data_completeness"] = self.metric_coverage
        return payload


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
            category=config.category,
        )
        for name, config in METRIC_SCORE_CONFIG.items()
    }
    weighted_score = sum(item.weighted_contribution for item in score_breakdown.values())
    present_count = sum(1 for name in METRIC_SCORE_CONFIG if raw_values[name] is not None)

    return ScoreResult(
        score=round(float(weighted_score), 2),
        components=components,
        category_scores=_category_scores(score_breakdown),
        score_breakdown=score_breakdown,
        metric_coverage=round(present_count / len(METRIC_SCORE_CONFIG), 2),
    )


def _category_scores(score_breakdown: dict[str, ScoreBreakdownItem]) -> dict[str, float]:
    scores = {}
    for category, category_weight in CATEGORY_WEIGHTS.items():
        category_contribution = sum(
            item.weighted_contribution
            for item in score_breakdown.values()
            if item.category == category
        )
        scores[category] = round(category_contribution / category_weight, 2)
    return scores


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
