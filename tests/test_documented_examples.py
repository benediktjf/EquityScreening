from __future__ import annotations

import json
from pathlib import Path
import unittest

from euro_equity_intelligence.metrics import EquityMetrics
from euro_equity_intelligence.scoring import score_metrics
from scripts.generate_example_response import build_example_response


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DocumentedExamplesTest(unittest.TestCase):
    def test_documented_example_matches_generator(self) -> None:
        example_path = PROJECT_ROOT / "docs" / "example_company_response.json"
        example = json.loads(example_path.read_text())

        self.assertEqual(example, build_example_response())

    def test_documented_example_score_matches_scoring_function(self) -> None:
        example_path = PROJECT_ROOT / "docs" / "example_company_response.json"
        example = json.loads(example_path.read_text())

        metrics = EquityMetrics(**example["metrics"])
        expected_score = score_metrics(metrics)

        self.assertEqual(example["score"], expected_score.to_dict())
        self.assertEqual(example["data_quality"]["metric_coverage"], expected_score.metric_coverage)
        self.assertEqual(example["data_quality"]["data_completeness"], expected_score.data_completeness)
        self.assertEqual(example["score_status"], "scored")

    def test_documented_example_score_matches_component_breakdown(self) -> None:
        example_path = PROJECT_ROOT / "docs" / "example_company_response.json"
        example = json.loads(example_path.read_text())

        weighted_score = round(
            sum(
                item["weighted_contribution"]
                for item in example["score"]["score_breakdown"].values()
            ),
            2,
        )

        self.assertEqual(example["score"]["score"], weighted_score)


if __name__ == "__main__":
    unittest.main()
