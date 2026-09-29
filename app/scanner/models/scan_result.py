from __future__ import annotations

from dataclasses import dataclass

from app.scanner.schemas import StockSnapshot


@dataclass(slots=True)
class ScanResult:
    """
    Result returned by a scanner strategy.
    """

    matched: bool

    strategy: str

    snapshot: StockSnapshot

    reason: str | None = None