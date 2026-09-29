"""
Backtesting: finds every historical occurrence of a strategy's
signal across an instrument's full history (not just the latest
day, which is all the live scanner looks at), then measures what
happened to price in the days/weeks afterward.

This answers a different question than the live scanner does. The
scanner tells you a stock matches right now and why. A backtest
tells you: historically, when this exact signal fired, did the
stock tend to go up afterward, and by how much? That's what
determines whether a strategy has real edge, as opposed to just
being a plausible-sounding rule.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.scanner.expression import evaluate_expression_with_reasons
from app.scanner.schemas import IndicatorSnapshot, ScanExpression, StockSnapshot

# Standard holding periods (in trading days) to measure forward
# returns over. Chosen to cover short-term follow-through (1 week),
# medium-term (1 month), and whether the move held up (1 quarter).
DEFAULT_HOLDING_PERIODS = (5, 10, 20, 60)


@dataclass(frozen=True)
class HistoricalSignal:
    """
    One point in an instrument's history where a strategy's
    expression matched.
    """

    trade_date: date
    reasons: list[str]


@dataclass(frozen=True)
class BacktestEvent:
    """
    A historical signal plus what happened to price afterward, for
    every holding period that had enough subsequent data available.
    """

    symbol: str
    trade_date: date
    entry_price: Decimal
    reasons: list[str]

    # holding_period (trading days) -> forward return, as a
    # percentage (5.0 means +5%). Missing key means there wasn't
    # enough subsequent history to measure that holding period yet
    # (e.g. a signal from last week can't have a 60-day return).
    forward_returns: dict[int, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class HoldingPeriodStats:
    """
    Aggregate statistics for one holding period, across every event
    that had enough data to measure it.
    """

    holding_period: int
    sample_size: int
    win_rate: Decimal
    average_return: Decimal
    median_return: Decimal
    best_return: Decimal
    worst_return: Decimal

    # Outlier-robust view: mean after dropping the top and bottom
    # 10% of returns. Comparing this to average_return shows how
    # much a handful of extreme events are driving the plain
    # average -- a large gap between the two means the "average"
    # figure alone is misleading.
    trimmed_mean_return: Decimal = Decimal("0")

    # Count and share of events with an absolute return beyond 20%
    # (an arbitrary but reasonable "extreme move" threshold for
    # equities over these holding periods).
    outlier_count: int = 0
    outlier_share: Decimal = Decimal("0")


def build_time_series(
    history_rows: list[tuple],
) -> dict[date, dict[str, Decimal]]:
    """
    Groups raw (trade_date, feature_name, decimal_value,
    integer_value, boolean_value) rows (as returned by
    FeatureValueRepository.get_history_for_instrument) into a
    date -> {feature_name: value} time series.
    """

    series: dict[date, dict[str, Decimal]] = {}

    for trade_date, feature_name, decimal_value, integer_value, boolean_value in history_rows:

        if decimal_value is not None:
            value = decimal_value
        elif integer_value is not None:
            value = Decimal(integer_value)
        elif boolean_value is not None:
            value = boolean_value
        else:
            continue

        series.setdefault(trade_date, {})[feature_name] = value

    return series


def find_historical_signals(
    time_series: dict[date, dict[str, Decimal]],
    expression: ScanExpression,
) -> list[HistoricalSignal]:
    """
    Walks the time series chronologically, evaluating the strategy's
    expression against each day (using that day as "current" and
    the prior trading day as "previous", matching exactly how the
    live scanner evaluates a snapshot) and collecting every match.
    """

    trading_days = sorted(time_series.keys())

    signals: list[HistoricalSignal] = []

    for i in range(1, len(trading_days)):

        current_date = trading_days[i]
        previous_date = trading_days[i - 1]

        snapshot = StockSnapshot(
            current=IndicatorSnapshot(values=time_series[current_date]),
            previous=IndicatorSnapshot(values=time_series[previous_date]),
        )

        matched, reasons = evaluate_expression_with_reasons(
            snapshot,
            expression,
        )

        if matched:
            signals.append(
                HistoricalSignal(
                    trade_date=current_date,
                    reasons=reasons,
                )
            )

    return signals


# A single-day close-to-close ratio outside this range is treated
# as implausible for organic trading (Indian exchange circuit
# limits are typically 5-20%) and far more likely to be an
# unadjusted corporate action (stock split, bonus issue, etc.) in
# the raw data. Confirmed by direct investigation: several of the
# most extreme outlier returns in a real backtest traced back to
# exactly this -- a stock's raw close cliff-dropping ~99% in one
# day (a split, not a loss), which otherwise silently distorted the
# forward-return statistics.
PRICE_DISCONTINUITY_MIN_RATIO = Decimal("0.5")
PRICE_DISCONTINUITY_MAX_RATIO = Decimal("2.0")


def _has_price_discontinuity(
    trading_days: list[date],
    time_series: dict[date, dict[str, Decimal]],
    start_index: int,
    end_index: int,
) -> bool:
    """
    Scans consecutive-day CLOSE prices between start_index and
    end_index (inclusive) for an implausible single-day jump.
    """

    previous_close = None

    for i in range(start_index, end_index + 1):

        close = time_series.get(trading_days[i], {}).get("CLOSE")

        if close is None:
            continue

        if previous_close is not None and previous_close != 0:

            ratio = close / previous_close

            if (
                ratio < PRICE_DISCONTINUITY_MIN_RATIO
                or ratio > PRICE_DISCONTINUITY_MAX_RATIO
            ):
                return True

        previous_close = close

    return False


def compute_forward_returns(
    symbol: str,
    signals: list[HistoricalSignal],
    time_series: dict[date, dict[str, Decimal]],
    holding_periods: tuple[int, ...] = DEFAULT_HOLDING_PERIODS,
) -> list[BacktestEvent]:
    """
    For every signal, looks up the closing price N trading days
    later (for each holding period) and computes the percentage
    return. A holding period is omitted from an event's
    forward_returns if there isn't yet enough subsequent history to
    measure it (e.g. a signal from last week has no 60-day return
    yet), or if an implausible single-day price discontinuity is
    found within that window (see _has_price_discontinuity) -- in
    both cases, the return is left out rather than included with a
    number that can't be trusted.
    """

    trading_days = sorted(time_series.keys())
    date_index = {d: i for i, d in enumerate(trading_days)}

    events: list[BacktestEvent] = []

    for signal in signals:

        entry_values = time_series.get(signal.trade_date, {})
        entry_price = entry_values.get("CLOSE")

        if entry_price is None:
            continue

        entry_index = date_index[signal.trade_date]

        forward_returns: dict[int, Decimal] = {}

        for period in holding_periods:

            exit_index = entry_index + period

            if exit_index >= len(trading_days):
                continue

            exit_date = trading_days[exit_index]
            exit_price = time_series.get(exit_date, {}).get("CLOSE")

            if exit_price is None or entry_price == 0:
                continue

            if _has_price_discontinuity(
                trading_days,
                time_series,
                max(entry_index - 1, 0),
                exit_index,
            ):
                continue

            return_pct = (
                (exit_price - entry_price) / entry_price * Decimal("100")
            )

            forward_returns[period] = return_pct.quantize(Decimal("0.01"))

        events.append(
            BacktestEvent(
                symbol=symbol,
                trade_date=signal.trade_date,
                entry_price=entry_price,
                reasons=signal.reasons,
                forward_returns=forward_returns,
            )
        )

    return events


def _stats_from_returns(
    period: int,
    returns: list[Decimal],
) -> HoldingPeriodStats:
    """
    Shared aggregation logic for a single holding period's list of
    returns, used both for actual signal events and for the
    universe baseline (see compute_universe_baseline_returns).
    """

    if not returns:
        return HoldingPeriodStats(
            holding_period=period,
            sample_size=0,
            win_rate=Decimal("0"),
            average_return=Decimal("0"),
            median_return=Decimal("0"),
            best_return=Decimal("0"),
            worst_return=Decimal("0"),
            trimmed_mean_return=Decimal("0"),
            outlier_count=0,
            outlier_share=Decimal("0"),
        )

    sorted_returns = sorted(returns)
    n = len(sorted_returns)

    wins = sum(1 for r in returns if r > 0)

    if n % 2 == 1:
        median = sorted_returns[n // 2]
    else:
        median = (
            sorted_returns[n // 2 - 1] + sorted_returns[n // 2]
        ) / 2

    # Trimmed mean: drop the top and bottom 10% of returns, then
    # average what's left. This shows whether the plain average is
    # being dominated by a handful of extreme events -- a big gap
    # between average_return and trimmed_mean_return means yes.
    trim_count = int(n * 0.1)
    trimmed = (
        sorted_returns[trim_count: n - trim_count]
        if n - 2 * trim_count > 0
        else sorted_returns
    )

    outlier_threshold = Decimal("20")
    outliers = [r for r in returns if abs(r) > outlier_threshold]

    return HoldingPeriodStats(
        holding_period=period,
        sample_size=n,
        win_rate=(
            Decimal(wins) / Decimal(n) * Decimal("100")
        ).quantize(Decimal("0.01")),
        average_return=(
            sum(returns) / Decimal(n)
        ).quantize(Decimal("0.01")),
        median_return=median.quantize(Decimal("0.01")),
        best_return=max(returns),
        worst_return=min(returns),
        trimmed_mean_return=(
            sum(trimmed) / Decimal(len(trimmed))
        ).quantize(Decimal("0.01")),
        outlier_count=len(outliers),
        outlier_share=(
            Decimal(len(outliers)) / Decimal(n) * Decimal("100")
        ).quantize(Decimal("0.01")),
    )


def aggregate_backtest_stats(
    events: list[BacktestEvent],
    holding_periods: tuple[int, ...] = DEFAULT_HOLDING_PERIODS,
) -> list[HoldingPeriodStats]:
    """
    Aggregates per-holding-period statistics across every event that
    had a measurable return for that period.
    """

    results: list[HoldingPeriodStats] = []

    for period in holding_periods:

        returns = [
            event.forward_returns[period]
            for event in events
            if period in event.forward_returns
        ]

        results.append(_stats_from_returns(period, returns))

    return results


def compute_universe_baseline_returns(
    all_time_series: dict[str, dict[date, dict[str, Decimal]]],
    holding_periods: tuple[int, ...] = DEFAULT_HOLDING_PERIODS,
    sample_every: int = 10,
) -> list[HoldingPeriodStats]:
    """
    Baseline for comparison: "if I'd bought ANY stock in this same
    universe on a given day, unconditionally, what would I have
    made over the same holding periods?"

    Without this, a strategy's average return is meaningless on its
    own -- if the whole dataset happens to trend upward over the
    period covered, almost any signal will show a "positive"
    average return that has nothing to do with the signal itself.

    Samples every `sample_every`-th trading day per instrument
    (rather than every single day) to keep this computationally
    reasonable across a large universe/long history while still
    giving a representative baseline.
    """

    returns_by_period: dict[int, list[Decimal]] = {
        period: [] for period in holding_periods
    }

    for time_series in all_time_series.values():

        trading_days = sorted(time_series.keys())

        for i in range(0, len(trading_days), sample_every):

            entry_date = trading_days[i]
            entry_price = time_series[entry_date].get("CLOSE")

            if entry_price is None or entry_price == 0:
                continue

            for period in holding_periods:

                exit_index = i + period

                if exit_index >= len(trading_days):
                    continue

                exit_date = trading_days[exit_index]
                exit_price = time_series[exit_date].get("CLOSE")

                if exit_price is None:
                    continue

                return_pct = (
                    (exit_price - entry_price) / entry_price * Decimal("100")
                )

                returns_by_period[period].append(
                    return_pct.quantize(Decimal("0.01"))
                )

    return [
        _stats_from_returns(period, returns_by_period[period])
        for period in holding_periods
    ]