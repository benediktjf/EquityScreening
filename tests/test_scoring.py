from __future__ import annotations

from math import isclose
import unittest

from euro_equity_intelligence.metrics import EquityMetrics
from euro_equity_intelligence.scoring import METRIC_SCORE_CONFIG, score_metrics


class ScoringTest(unittest.TestCase):
    def test_score_metrics_returns_zero_to_one_hundred_score(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=0.20,
            ebitda_margin=0.30,
            net_debt_to_ebitda=0.0,
            pe_ratio=8.0,
            ev_to_ebitda=6.0,
            roe=0.25,
            free_cash_flow_yield=0.10,
        )

        result = score_metrics(metrics)

        self.assertTrue(isclose(result.score, 100.0))
        self.assertTrue(isclose(result.data_completeness, 1.0))
        self.assertEqual(set(result.score_breakdown), set(METRIC_SCORE_CONFIG))

    def test_missing_metrics_are_neutral_and_reduce_completeness(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=None,
            ebitda_margin=None,
            net_debt_to_ebitda=None,
            pe_ratio=None,
            ev_to_ebitda=None,
            roe=None,
            free_cash_flow_yield=None,
        )

        result = score_metrics(metrics)

        self.assertTrue(isclose(result.score, 50.0))
        self.assertTrue(isclose(result.data_completeness, 0.0))
        self.assertTrue(all(isclose(component, 50.0) for component in result.components.values()))
        self.assertTrue(
            all(item.raw_value is None for item in result.score_breakdown.values())
        )

    def test_partial_metrics_keep_weighted_score_and_completeness(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=0.05,
            ebitda_margin=None,
            net_debt_to_ebitda=2.5,
            pe_ratio=None,
            ev_to_ebitda=None,
            roe=0.125,
            free_cash_flow_yield=None,
        )

        result = score_metrics(metrics)

        self.assertTrue(isclose(result.components["revenue_growth"], 50.0))
        self.assertTrue(isclose(result.components["ebitda_margin"], 50.0))
        self.assertTrue(isclose(result.components["net_debt_to_ebitda"], 50.0))
        self.assertTrue(isclose(result.components["roe"], 50.0))
        self.assertTrue(isclose(result.score, 50.0))
        self.assertTrue(isclose(result.data_completeness, 0.43))

    def test_score_breakdown_contains_weighted_contributions(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=0.08,
            ebitda_margin=0.22,
            net_debt_to_ebitda=1.5,
            pe_ratio=18.0,
            ev_to_ebitda=11.0,
            roe=0.16,
            free_cash_flow_yield=0.045,
        )

        result = score_metrics(metrics)

        weighted_score = round(
            sum(item.weighted_contribution for item in result.score_breakdown.values()),
            2,
        )
        self.assertEqual(result.score, weighted_score)
        for metric_name, item in result.score_breakdown.items():
            config = METRIC_SCORE_CONFIG[metric_name]
            self.assertEqual(item.weight, config.weight)
            self.assertEqual(item.direction, config.direction)
            self.assertEqual(item.component_score, result.components[metric_name])
            self.assertEqual(
                item.weighted_contribution,
                round(item.component_score * item.weight, 2),
            )

    def test_component_scores_are_clamped_to_zero_and_one_hundred(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=1.00,
            ebitda_margin=-0.10,
            net_debt_to_ebitda=10.0,
            pe_ratio=100.0,
            ev_to_ebitda=100.0,
            roe=0.50,
            free_cash_flow_yield=0.50,
        )

        result = score_metrics(metrics)

        self.assertEqual(result.components["revenue_growth"], 100.0)
        self.assertEqual(result.components["ebitda_margin"], 0.0)
        self.assertEqual(result.components["net_debt_to_ebitda"], 0.0)
        self.assertEqual(result.components["pe_ratio"], 0.0)
        self.assertEqual(result.components["ev_to_ebitda"], 0.0)
        self.assertEqual(result.components["roe"], 100.0)
        self.assertEqual(result.components["free_cash_flow_yield"], 100.0)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 100.0)

    def test_net_cash_is_scored_as_strong_leverage(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=None,
            ebitda_margin=None,
            net_debt_to_ebitda=-1.0,
            pe_ratio=None,
            ev_to_ebitda=None,
            roe=None,
            free_cash_flow_yield=None,
        )

        result = score_metrics(metrics)

        self.assertEqual(result.components["net_debt_to_ebitda"], 100.0)

    def test_negative_valuation_multiples_are_penalized(self) -> None:
        metrics = EquityMetrics(
            revenue_growth=None,
            ebitda_margin=None,
            net_debt_to_ebitda=None,
            pe_ratio=-4.0,
            ev_to_ebitda=-2.0,
            roe=None,
            free_cash_flow_yield=None,
        )

        result = score_metrics(metrics)

        self.assertEqual(result.components["pe_ratio"], 10.0)
        self.assertEqual(result.components["ev_to_ebitda"], 10.0)


if __name__ == "__main__":
    unittest.main()
