from datetime import date, timedelta
from decimal import Decimal

from app.scanner.backtest import (
    aggregate_backtest_stats,
    build_time_series,
    compute_forward_returns,
    find_historical_signals,
)
from app.scanner.enums import ComparisonOperator, LogicalOperator
from app.scanner.schemas import ScanCondition, ScanExpression


def _d(day_offset: int) -> date:
    return date(2024, 1, 1) + timedelta(days=day_offset)


SIMPLE_EXPRESSION = ScanExpression(
    operator=LogicalOperator.AND,
    children=[
        ScanCondition(
            left="RSI14",
            operator=ComparisonOperator.LESS_THAN,
            right=Decimal("30"),
        ),
    ],
)


def test_build_time_series_groups_by_date():

    rows = [
        (_d(0), "CLOSE", Decimal("100"), None, None),
        (_d(0), "RSI14", Decimal("25"), None, None),
        (_d(1), "CLOSE", Decimal("102"), None, None),
    ]

    series = build_time_series(rows)

    assert series[_d(0)] == {"CLOSE": Decimal("100"), "RSI14": Decimal("25")}
    assert series[_d(1)] == {"CLOSE": Decimal("102")}


def test_build_time_series_prefers_decimal_then_integer_then_boolean():

    rows = [
        (_d(0), "VOLUME", None, 5000, None),
        (_d(0), "SUPERTREND_BULLISH", None, None, True),
    ]

    series = build_time_series(rows)

    assert series[_d(0)]["VOLUME"] == Decimal(5000)
    assert series[_d(0)]["SUPERTREND_BULLISH"] is True


def test_find_historical_signals_finds_every_match_not_just_latest():

    # RSI drops below 30 on day 2 and again on day 5.
    time_series = {
        _d(0): {"RSI14": Decimal("50")},
        _d(1): {"RSI14": Decimal("45")},
        _d(2): {"RSI14": Decimal("28")},  # match
        _d(3): {"RSI14": Decimal("40")},
        _d(4): {"RSI14": Decimal("60")},
        _d(5): {"RSI14": Decimal("22")},  # match
    }

    signals = find_historical_signals(time_series, SIMPLE_EXPRESSION)

    assert [s.trade_date for s in signals] == [_d(2), _d(5)]
    assert all(len(s.reasons) == 1 for s in signals)


def test_find_historical_signals_skips_first_day_no_previous():

    # Day 0 has no "previous" day, so even if it matches it can't be
    # evaluated -- there's nothing before it to build a snapshot.
    time_series = {
        _d(0): {"RSI14": Decimal("20")},
    }

    signals = find_historical_signals(time_series, SIMPLE_EXPRESSION)

    assert signals == []


def test_compute_forward_returns_measures_correct_holding_periods():

    # 10 trading days of prices; signal fires on day 2 (index 2).
    prices = [100, 101, 102, 104, 106, 108, 103, 99, 97, 95]

    time_series = {
        _d(i): {"CLOSE": Decimal(str(p))}
        for i, p in enumerate(prices)
    }

    from app.scanner.backtest import HistoricalSignal

    signals = [HistoricalSignal(trade_date=_d(2), reasons=["test"])]

    events = compute_forward_returns(
        symbol="TEST",
        signals=signals,
        time_series=time_series,
        holding_periods=(1, 3, 5),
    )

    assert len(events) == 1
    event = events[0]

    assert event.entry_price == Decimal("102")

    # 1 day later (index 3): 104 -> (104-102)/102*100 = 1.96%
    assert event.forward_returns[1] == Decimal("1.96")

    # 3 days later (index 5): 108 -> (108-102)/102*100 = 5.88%
    assert event.forward_returns[3] == Decimal("5.88")

    # 5 days later (index 7): 99 -> (99-102)/102*100 = -2.94%
    assert event.forward_returns[5] == Decimal("-2.94")


def test_compute_forward_returns_omits_periods_without_enough_future_data():

    prices = [100, 105, 110]

    time_series = {
        _d(i): {"CLOSE": Decimal(str(p))}
        for i, p in enumerate(prices)
    }

    from app.scanner.backtest import HistoricalSignal

    signals = [HistoricalSignal(trade_date=_d(0), reasons=["test"])]

    events = compute_forward_returns(
        symbol="TEST",
        signals=signals,
        time_series=time_series,
        holding_periods=(1, 60),
    )

    assert 1 in events[0].forward_returns
    assert 60 not in events[0].forward_returns


def test_aggregate_backtest_stats_computes_win_rate_and_averages():

    from app.scanner.backtest import BacktestEvent

    events = [
        BacktestEvent(
            symbol="A", trade_date=_d(0), entry_price=Decimal("100"),
            reasons=[], forward_returns={5: Decimal("10.00")},
        ),
        BacktestEvent(
            symbol="B", trade_date=_d(1), entry_price=Decimal("100"),
            reasons=[], forward_returns={5: Decimal("-4.00")},
        ),
        BacktestEvent(
            symbol="C", trade_date=_d(2), entry_price=Decimal("100"),
            reasons=[], forward_returns={5: Decimal("2.00")},
        ),
    ]

    stats = aggregate_backtest_stats(events, holding_periods=(5,))

    assert len(stats) == 1
    s = stats[0]

    assert s.sample_size == 3
    assert s.win_rate == Decimal("66.67")  # 2 of 3 positive
    assert s.average_return == Decimal("2.67")  # (10-4+2)/3
    assert s.median_return == Decimal("2.00")
    assert s.best_return == Decimal("10.00")
    assert s.worst_return == Decimal("-4.00")


def test_aggregate_backtest_stats_handles_no_data_for_a_period():

    stats = aggregate_backtest_stats([], holding_periods=(5, 20))

    assert len(stats) == 2
    assert all(s.sample_size == 0 for s in stats)


def test_compute_forward_returns_excludes_period_with_split_like_discontinuity():
    """
    Regression test for a real issue found investigating a live
    backtest: a stock (AURUM) whose raw close dropped ~99% in a
    single day (an unadjusted stock split, not a real loss), which
    silently produced a fake ~-98% "forward return" in the backtest.
    This must be excluded, not included as a real number.
    """

    from app.scanner.backtest import HistoricalSignal

    prices = [100, 101, 102, 103, 104, 105, 106, 2, 2.1, 2.2, 2.3, 2.4]

    time_series = {
        _d(i): {"CLOSE": Decimal(str(p))}
        for i, p in enumerate(prices)
    }

    # Signal fires on day 5 (index 5, price 105); the split happens
    # between day 6 (106) and day 7 (2) -- inside the 5-day forward
    # window.
    signals = [HistoricalSignal(trade_date=_d(5), reasons=["test"])]

    events = compute_forward_returns(
        symbol="TEST",
        signals=signals,
        time_series=time_series,
        holding_periods=(1, 5),
    )

    assert len(events) == 1
    # 1-day return (day 5 -> day 6, 105 -> 106) has no discontinuity
    # in its window and should be present.
    assert 1 in events[0].forward_returns
    # 5-day return's window includes the split -- must be excluded.
    assert 5 not in events[0].forward_returns


def test_compute_forward_returns_excludes_when_signal_itself_is_a_split_artifact():
    """
    Regression test for the LCCINFOTEC case: the breakout signal
    itself was triggered by a fake single-day price jump (comparing
    the signal's entry day to the day before it), not just
    distortion appearing later in the forward-return window.
    """

    from app.scanner.backtest import HistoricalSignal

    # Day 4 (index 4) is a fake +2000%-ish jump from day 3.
    prices = [10, 10.1, 10.2, 10.3, 220, 221, 222, 223, 224]

    time_series = {
        _d(i): {"CLOSE": Decimal(str(p))}
        for i, p in enumerate(prices)
    }

    signals = [HistoricalSignal(trade_date=_d(4), reasons=["test"])]

    events = compute_forward_returns(
        symbol="TEST",
        signals=signals,
        time_series=time_series,
        holding_periods=(1,),
    )

    assert len(events) == 1
    # Entry day itself is the artifact -- every holding period
    # should be excluded.
    assert events[0].forward_returns == {}


def test_compute_forward_returns_does_not_flag_normal_volatility():
    """
    A large but plausible multi-day move (e.g. a genuine 40% decline
    spread across several trading days, each within normal circuit
    limits) must NOT be excluded -- only actual single-day
    discontinuities should trigger the guard.
    """

    from app.scanner.backtest import HistoricalSignal

    # Each day is at most a ~9% move -- well within normal circuit
    # limits, even though the cumulative move over 5 days is large.
    prices = [100, 91, 92, 84, 85, 77]

    time_series = {
        _d(i): {"CLOSE": Decimal(str(p))}
        for i, p in enumerate(prices)
    }

    signals = [HistoricalSignal(trade_date=_d(0), reasons=["test"])]

    events = compute_forward_returns(
        symbol="TEST",
        signals=signals,
        time_series=time_series,
        holding_periods=(5,),
    )

    assert len(events) == 1
    assert 5 in events[0].forward_returns
    # Genuine ~23% decline over 5 days, not excluded.
    assert events[0].forward_returns[5] < Decimal("0")