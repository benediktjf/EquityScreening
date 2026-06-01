"""Starting universe for the European equity screener."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    country: str
    exchange: str
    sector: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


EUROPEAN_UNIVERSE: tuple[Company, ...] = (
    Company("ASML.AS", "ASML Holding", "Netherlands", "Euronext Amsterdam", "Technology"),
    Company("NESN.SW", "Nestle", "Switzerland", "SIX Swiss Exchange", "Consumer Staples"),
    Company("NOVN.SW", "Novartis", "Switzerland", "SIX Swiss Exchange", "Healthcare"),
    Company("ROG.SW", "Roche Holding", "Switzerland", "SIX Swiss Exchange", "Healthcare"),
    Company("SAP.DE", "SAP", "Germany", "Xetra", "Technology"),
    Company("SIE.DE", "Siemens", "Germany", "Xetra", "Industrials"),
    Company("ALV.DE", "Allianz", "Germany", "Xetra", "Financials"),
    Company("MC.PA", "LVMH", "France", "Euronext Paris", "Consumer Discretionary"),
    Company("OR.PA", "L'Oreal", "France", "Euronext Paris", "Consumer Staples"),
    Company("AIR.PA", "Airbus", "France", "Euronext Paris", "Industrials"),
    Company("TTE.PA", "TotalEnergies", "France", "Euronext Paris", "Energy"),
    Company("SAN.PA", "Sanofi", "France", "Euronext Paris", "Healthcare"),
    Company("AZN.L", "AstraZeneca", "United Kingdom", "London Stock Exchange", "Healthcare"),
    Company("SHEL.L", "Shell", "United Kingdom", "London Stock Exchange", "Energy"),
    Company("ULVR.L", "Unilever", "United Kingdom", "London Stock Exchange", "Consumer Staples"),
    Company("HSBA.L", "HSBC Holdings", "United Kingdom", "London Stock Exchange", "Financials"),
    Company("BP.L", "BP", "United Kingdom", "London Stock Exchange", "Energy"),
    Company("ITX.MC", "Inditex", "Spain", "Bolsa de Madrid", "Consumer Discretionary"),
    Company("SAN.MC", "Banco Santander", "Spain", "Bolsa de Madrid", "Financials"),
    Company("ENEL.MI", "Enel", "Italy", "Borsa Italiana", "Utilities"),
)


def list_companies() -> list[dict[str, str]]:
    return [company.to_dict() for company in EUROPEAN_UNIVERSE]


def get_company(ticker: str) -> Company:
    normalized = ticker.upper()
    for company in EUROPEAN_UNIVERSE:
        if company.ticker.upper() == normalized:
            return company
    raise KeyError(f"Ticker not found in universe: {ticker}")
