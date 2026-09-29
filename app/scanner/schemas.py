from datetime import date, datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from app.scanner.enums import ComparisonOperator, IndicatorField, LogicalOperator


class ScanCondition(BaseModel):
    """
    Represents a single scan condition.
    """

    model_config = ConfigDict(frozen=True)

    left: IndicatorField

    operator: ComparisonOperator

    right: Union[
        IndicatorField,
        Decimal,
    ]


class ScanExpression(BaseModel):
    """
    Logical expression consisting of
    conditions and/or child expressions.
    """

    model_config = ConfigDict(frozen=True)

    operator: LogicalOperator

    children: list[
        Union[
            "ScanExpression",
            ScanCondition,
        ]
    ]


ScanExpression.model_rebuild()


class ScanRequest(BaseModel):
    expression: ScanExpression

    # Label for the persisted scan run (e.g. "Swing Strategy").
    # Purely for record-keeping; doesn't affect evaluation.
    strategy_name: str = "custom"


class ScanResult(BaseModel):
    """
    One stock that matched the scan.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str

    reasons: list[str] = Field(default_factory=list)


class ScanRunSummary(BaseModel):
    """
    Summary of a past scan run (for history listings).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int

    user_id: int | None = None

    strategy: str

    stocks_scanned: int

    matches_found: int

    started_at: datetime

    completed_at: datetime


class ScanRunDetail(ScanRunSummary):
    """
    A past scan run including its matched results.
    """

    results: list[ScanResult]


class ScanRunListResponse(BaseModel):
    """
    A page of scan run summaries, with pagination metadata.
    """

    model_config = ConfigDict(frozen=True)

    total: int

    limit: int

    offset: int

    runs: list[ScanRunSummary]


class ScanStrategySummary(BaseModel):
    """
    A named, ready-to-run strategy.
    """

    model_config = ConfigDict(frozen=True)

    key: str

    name: str


class IndicatorSnapshot(BaseModel):
    """
    Indicator values for one candle.
    """

    model_config = ConfigDict(frozen=True)

    values: dict[
        IndicatorField,
        Decimal | int | bool,
    ]


class StockSnapshot(BaseModel):
    """
    Current and previous indicator values.
    """

    model_config = ConfigDict(frozen=True)

    current: IndicatorSnapshot

    previous: IndicatorSnapshot = Field(
        default_factory=lambda: IndicatorSnapshot(values={}),
    )


class BacktestEventResponse(BaseModel):
    """
    One historical occurrence of a strategy's signal, with what
    happened to price afterward.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str

    trade_date: date

    entry_price: Decimal

    reasons: list[str]

    # Keyed by holding period in trading days, as a string (JSON
    # object keys must be strings) -- e.g. {"5": 3.21, "20": -1.05}.
    # A holding period is absent if there wasn't enough subsequent
    # history yet to measure it.
    forward_returns: dict[str, Decimal]


class HoldingPeriodStatsResponse(BaseModel):
    """
    Aggregate statistics for one holding period, across every
    historical signal that had a measurable return for it.
    """

    model_config = ConfigDict(frozen=True)

    holding_period: int

    sample_size: int

    win_rate: Decimal

    average_return: Decimal

    median_return: Decimal

    best_return: Decimal

    worst_return: Decimal

    # Mean after dropping the top/bottom 10% of returns. A big gap
    # from average_return means a handful of extreme events are
    # driving the plain average.
    trimmed_mean_return: Decimal

    # Count and share of events with an absolute return beyond 20%.
    outlier_count: int

    outlier_share: Decimal


class BacktestResponse(BaseModel):
    """
    Full backtest result: aggregate stats per holding period, plus
    the individual historical events they're computed from.
    """

    model_config = ConfigDict(frozen=True)

    strategy_name: str

    instruments_scanned: int

    total_signals_found: int

    stats: list[HoldingPeriodStatsResponse]

    # "Buy any stock in this same universe, on any day" comparison.
    # Compare stats vs baseline_stats to see whether the signal
    # actually beat picking randomly, or whether the whole dataset
    # just trended upward over the period covered.
    baseline_stats: list[HoldingPeriodStatsResponse]

    events: list[BacktestEventResponse]