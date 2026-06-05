from __future__ import annotations

from math import isclose
import unittest

from euro_equity_intelligence.metrics import EquityMetrics
from euro_equity_intelligence.scoring import CATEGORY_WEIGHTS, METRIC_SCORE_CONFIG, score_metrics


def _metrics(**overrides: float | None) -> EquityMetrics:
    values = {name: None for name in METRIC_SCORE_CONFIG}
    values.update(overrides)
    return EquityMetrics(**values)


class ScoringTest(unittest.TestCase):
    def test_score_metrics_returns_zero_to_one_hundred_score(self) -> None:
        metrics = _metrics(
            revenue_growth=0.20,
            ebitda_margin=0.30,
            operating_margin=0.25,
            net_margin=0.20,
            net_debt_to_ebitda=0.0,
            interest_coverage=12.0,
            pe_ratio=8.0,
            ev_to_ebitda=6.0,
            ev_to_sales=0.5,
            roe=0.25,
            roic=0.20,
            free_cash_flow_yield=0.10,
            free_cash_flow_margin=0.20,
        )

        result = score_metrics(metrics)

        self.assertTrue(isclose(result.score, 100.0))
        self.assertTrue(isclose(result.metric_coverage, 1.0))
        self.assertTrue(isclose(result.data_completeness, 1.0))
        self.assertEqual(set(result.score_breakdown), set(METRIC_SCORE_CONFIG))
        self.assertTrue(all(isclose(score, 100.0) for score in result.category_scores.values()))

    def test_missing_metrics_are_neutral_and_reduce_metric_coverage(self) -> None:
        result = score_metrics(_metrics())

        self.assertTrue(isclose(result.score, 50.0))
        self.assertTrue(isclose(result.metric_coverage, 0.0))
        self.assertTrue(isclose(result.data_completeness, 0.0))
        self.assertTrue(all(isclose(component, 50.0) for component in result.components.values()))
        self.assertTrue(all(item.raw_value is None for item in result.score_breakdown.values()))

    def test_partial_metrics_keep_weighted_score_and_metric_coverage(self) -> None:
        metrics = _metrics(
            revenue_growth=0.05,
            net_debt_to_ebitda=2.5,
            roe=0.125,
            free_cash_flow_margin=0.10,
        )

        result = score_metrics(metrics)

        self.assertTrue(isclose(result.components["revenue_growth"], 50.0))
        self.assertTrue(isclose(result.components["net_debt_to_ebitda"], 50.0))
        self.assertTrue(isclose(result.components["roe"], 50.0))
        self.assertTrue(isclose(result.components["free_cash_flow_margin"], 50.0))
        self.assertTrue(isclose(result.score, 50.0))
        self.assertTrue(isclose(result.metric_coverage, 0.31))

    def test_score_breakdown_contains_weighted_contributions_and_categories(self) -> None:
        result = score_metrics(_sample_metrics())

        weighted_score = round(
            sum(item.weighted_contribution for item in result.score_breakdown.values()),
            2,
        )
        self.assertEqual(result.score, weighted_score)
        for metric_name, item in result.score_breakdown.items():
            config = METRIC_SCORE_CONFIG[metric_name]
            self.assertEqual(item.weight, config.weight)
            self.assertEqual(item.direction, config.direction)
            self.assertEqual(item.category, config.category)
            self.assertEqual(item.component_score, result.components[metric_name])
            self.assertEqual(
                item.weighted_contribution,
                round(item.component_score * item.weight, 2),
            )

    def test_category_scores_are_weighted_averages_of_metric_components(self) -> None:
        result = score_metrics(_sample_metrics())

        for category, category_weight in CATEGORY_WEIGHTS.items():
            expected = round(
                sum(
                    item.weighted_contribution
                    for item in result.score_breakdown.values()
                    if item.category == category
                )
                / category_weight,
                2,
            )
            self.assertEqual(result.category_scores[category], expected)

    def test_component_scores_are_clamped_to_zero_and_one_hundred(self) -> None:
        metrics = _metrics(
            revenue_growth=1.00,
            ebitda_margin=-0.10,
            operating_margin=-0.10,
            net_margin=-0.10,
            net_debt_to_ebitda=10.0,
            interest_coverage=30.0,
            pe_ratio=100.0,
            ev_to_ebitda=100.0,
            ev_to_sales=100.0,
            roe=0.50,
            roic=0.50,
            free_cash_flow_yield=0.50,
            free_cash_flow_margin=0.50,
        )

        result = score_metrics(metrics)

        self.assertEqual(result.components["revenue_growth"], 100.0)
        self.assertEqual(result.components["ebitda_margin"], 0.0)
        self.assertEqual(result.components["operating_margin"], 0.0)
        self.assertEqual(result.components["net_margin"], 0.0)
        self.assertEqual(result.components["net_debt_to_ebitda"], 0.0)
        self.assertEqual(result.components["interest_coverage"], 100.0)
        self.assertEqual(result.components["pe_ratio"], 0.0)
        self.assertEqual(result.components["ev_to_ebitda"], 0.0)
        self.assertEqual(result.components["ev_to_sales"], 0.0)
        self.assertEqual(result.components["roe"], 100.0)
        self.assertEqual(result.components["roic"], 100.0)
        self.assertEqual(result.components["free_cash_flow_yield"], 100.0)
        self.assertEqual(result.components["free_cash_flow_margin"], 100.0)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 100.0)

    def test_net_cash_is_scored_as_strong_leverage(self) -> None:
        result = score_metrics(_metrics(net_debt_to_ebitda=-1.0))

        self.assertEqual(result.components["net_debt_to_ebitda"], 100.0)

    def test_negative_valuation_multiples_are_penalized(self) -> None:
        result = score_metrics(
            _metrics(
                pe_ratio=-4.0,
                ev_to_ebitda=-2.0,
                ev_to_sales=-1.0,
            )
        )

        self.assertEqual(result.components["pe_ratio"], 10.0)
        self.assertEqual(result.components["ev_to_ebitda"], 10.0)
        self.assertEqual(result.components["ev_to_sales"], 10.0)


def _sample_metrics() -> EquityMetrics:
    return _metrics(
        revenue_growth=0.08,
        ebitda_margin=0.22,
        operating_margin=0.18,
        net_margin=0.11,
        net_debt_to_ebitda=1.5,
        interest_coverage=8.0,
        pe_ratio=18.0,
        ev_to_ebitda=11.0,
        ev_to_sales=3.0,
        roe=0.16,
        roic=0.13,
        free_cash_flow_yield=0.045,
        free_cash_flow_margin=0.09,
    )


if __name__ == "__main__":
    unittest.main()
