"""FastAPI application for the equity screener."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from .screener import EquityScreener


def create_app(screener: EquityScreener | None = None) -> FastAPI:
    """Create the FastAPI application with an injectable screener."""
    app = FastAPI(
        title="Euro Equity Intelligence",
        version="0.1.0",
        description="A modular equity screening API for European stocks.",
    )
    app.state.screener = screener or EquityScreener()

    @app.get("/companies")
    def companies() -> list[dict[str, str]]:
        """List the configured European equity universe."""
        return app.state.screener.list_companies()

    @app.get("/companies/{ticker}")
    def company_detail(ticker: str) -> dict:
        """Return market snapshot, metrics, score, and data quality for one ticker."""
        try:
            return app.state.screener.get_company_analysis(ticker)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/screen")
    def screen(
        limit: int = Query(20, ge=1, le=50),
        min_score: float | None = Query(None, ge=0, le=100),
    ) -> dict:
        """Rank the universe by score."""
        results = app.state.screener.screen(limit=limit, min_score=min_score)
        return {"count": len(results), "results": results}

    return app


app = create_app()
