"""Generate the deterministic example response used in docs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from euro_equity_intelligence.metrics import EquityMetrics, missing_metric_names
from euro_equity_intelligence.scoring import score_metrics


SAMPLE_METRICS = EquityMetrics(
    revenue_growth=0.08,
    ebitda_margin=0.22,
    net_debt_to_ebitda=1.5,
    pe_ratio=18.0,
    ev_to_ebitda=11.0,
    roe=0.16,
    free_cash_flow_yield=0.045,
)


def build_example_response() -> dict[str, Any]:
    """Build a reproducible API-shaped response from fixed sample metrics."""
    score = score_metrics(SAMPLE_METRICS)
    missing_metrics = missing_metric_names(SAMPLE_METRICS)
    return {
        "example_note": "Generated deterministic sample; not live market data.",
        "company": {
            "ticker": "EXAMPLE.DE",
            "name": "Example Industrials AG",
            "country": "Germany",
            "exchange": "Xetra",
            "sector": "Industrials",
        },
        "market": {
            "currency": "EUR",
            "market_cap": 10_000_000_000,
            "enterprise_value": 11_500_000_000,
            "last_close": 50.0,
        },
        "metrics": SAMPLE_METRICS.to_dict(),
        "score": score.to_dict(),
        "score_status": "scored",
        "data_quality": {
            "missing_metrics": missing_metrics,
            "data_completeness": score.data_completeness,
            "warnings": [],
        },
    }


def main() -> None:
    output_path = PROJECT_ROOT / "docs" / "example_company_response.json"
    output_path.write_text(json.dumps(build_example_response(), indent=2) + "\n")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
