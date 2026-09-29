from app.repositories.feature_value_repository import FeatureValueRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.scanner.backtest import (
    DEFAULT_HOLDING_PERIODS,
    BacktestEvent,
    HoldingPeriodStats,
    aggregate_backtest_stats,
    build_time_series,
    compute_forward_returns,
    compute_universe_baseline_returns,
    find_historical_signals,
)
from app.scanner.schemas import ScanExpression


class BacktestService:
    """
    Runs a strategy's expression against instruments' full
    historical data (not just the latest day) to find every past
    occurrence of the signal, then measures what happened to price
    afterward -- answering whether the strategy has real edge, as
    opposed to just being a plausible-sounding rule.
    """

    def __init__(
        self,
        instrument_repository: InstrumentRepository,
        feature_value_repository: FeatureValueRepository,
    ) -> None:

        self._instrument_repository = instrument_repository
        self._feature_value_repository = feature_value_repository

    def run(
        self,
        expression: ScanExpression,
        symbols: list[str] | None = None,
        holding_periods: tuple[int, ...] = DEFAULT_HOLDING_PERIODS,
        limit: int | None = None,
        include_baseline: bool = True,
    ) -> tuple[
        list[BacktestEvent],
        list[HoldingPeriodStats],
        list[HoldingPeriodStats],
        int,
    ]:
        """
        symbols=None backtests instruments in the database, capped
        to `limit` if given (recommended -- this walks each
        instrument's FULL history, which can be slow at real
        dataset scale). Pass an explicit symbol list to bypass the
        cap and scan exactly those instruments.

        Returns (events, stats, baseline_stats, instruments_scanned).
        baseline_stats is the "buy any stock in this universe on any
        day" comparison -- without it, a positive average return
        doesn't tell you whether the signal beat just picking
        randomly, or whether everything in the dataset went up over
        the period covered regardless of any signal.
        """

        instruments = self._instrument_repository.get_all()

        if symbols is not None:
            wanted = {s.upper() for s in symbols}
            instruments = [
                instrument
                for instrument in instruments
                if instrument.symbol.upper() in wanted
            ]
        elif limit is not None:
            instruments = instruments[:limit]

        all_events: list[BacktestEvent] = []
        all_close_series: dict[str, dict] = {}

        for instrument in instruments:

            history_rows = (
                self._feature_value_repository.get_history_for_instrument(
                    instrument.id,
                )
            )

            if not history_rows:
                continue

            time_series = build_time_series(history_rows)

            if include_baseline:
                # Only CLOSE is needed for the baseline -- keeping
                # just this field (instead of every indicator field)
                # is what keeps memory usage manageable across a
                # large universe of instruments.
                all_close_series[instrument.symbol] = {
                    trade_date: {"CLOSE": values["CLOSE"]}
                    for trade_date, values in time_series.items()
                    if "CLOSE" in values
                }

            signals = find_historical_signals(time_series, expression)

            if not signals:
                continue

            events = compute_forward_returns(
                symbol=instrument.symbol,
                signals=signals,
                time_series=time_series,
                holding_periods=holding_periods,
            )

            all_events.extend(events)

        stats = aggregate_backtest_stats(
            all_events,
            holding_periods=holding_periods,
        )

        baseline_stats = (
            compute_universe_baseline_returns(
                all_close_series,
                holding_periods=holding_periods,
            )
            if include_baseline
            else []
        )

        # Most recent first -- the events a person is most likely to
        # want to sanity-check are the recent ones.
        all_events.sort(key=lambda e: e.trade_date, reverse=True)

        return all_events, stats, baseline_stats, len(instruments)