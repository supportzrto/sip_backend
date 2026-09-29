from decimal import Decimal

from app.scanner.engine import ScannerEngine
from app.scanner.schemas import IndicatorSnapshot, StockSnapshot
from app.scanner.strategies import BreakdownStrategy, BreakoutStrategy


def test_breakout_strategy_matches_genuine_breakout():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("110"),
                "HIGHEST252": Decimal("103"),
                "VOLUME_SURGE20": Decimal("2.1"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("101"),
                "HIGHEST252": Decimal("103"),
            }
        ),
    )

    strategy = BreakoutStrategy()
    request = strategy.build_request()

    engine = ScannerEngine()
    results = engine.scan({"DEMO": snapshot}, request)

    assert len(results) == 1
    assert results[0].symbol == "DEMO"
    assert any("HIGHEST252" in r for r in results[0].reasons)
    assert any("VOLUME_SURGE20" in r for r in results[0].reasons)


def test_breakout_strategy_does_not_match_without_volume_confirmation():
    """
    Price broke out, but volume was ordinary -- should NOT match,
    since volume confirmation is required by design.
    """

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("110"),
                "HIGHEST252": Decimal("103"),
                "VOLUME_SURGE20": Decimal("1.1"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("101"),
                "HIGHEST252": Decimal("103"),
            }
        ),
    )

    strategy = BreakoutStrategy()
    request = strategy.build_request()

    engine = ScannerEngine()
    results = engine.scan({"DEMO": snapshot}, request)

    assert results == []


def test_breakout_strategy_does_not_match_stock_already_above_high():
    """
    The stock was already above its 252-day high yesterday too --
    not a fresh breakout, just a continuation. Should NOT match,
    since the strategy uses crosses_above (a fresh event), not a
    plain 'is currently above' check.
    """

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("115"),
                "HIGHEST252": Decimal("103"),
                "VOLUME_SURGE20": Decimal("2.5"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("112"),  # already above 103 yesterday
                "HIGHEST252": Decimal("103"),
            }
        ),
    )

    strategy = BreakoutStrategy()
    request = strategy.build_request()

    engine = ScannerEngine()
    results = engine.scan({"DEMO": snapshot}, request)

    assert results == []


def test_breakdown_strategy_matches_genuine_breakdown():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("90"),
                "LOWEST252": Decimal("95"),
                "VOLUME_SURGE20": Decimal("1.8"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("97"),
                "LOWEST252": Decimal("95"),
            }
        ),
    )

    strategy = BreakdownStrategy()
    request = strategy.build_request()

    engine = ScannerEngine()
    results = engine.scan({"DEMO": snapshot}, request)

    assert len(results) == 1
    assert any("LOWEST252" in r for r in results[0].reasons)


def test_breakout_strategy_custom_volume_threshold():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("110"),
                "HIGHEST252": Decimal("103"),
                "VOLUME_SURGE20": Decimal("1.3"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "CLOSE": Decimal("101"),
                "HIGHEST252": Decimal("103"),
            }
        ),
    )

    engine = ScannerEngine()

    # Default threshold (1.5x) should reject a 1.3x surge.
    default_strategy = BreakoutStrategy()
    assert engine.scan({"DEMO": snapshot}, default_strategy.build_request()) == []

    # A lower custom threshold should accept it.
    lenient_strategy = BreakoutStrategy(volume_surge_threshold=Decimal("1.2"))
    results = engine.scan({"DEMO": snapshot}, lenient_strategy.build_request())
    assert len(results) == 1


def test_strategy_names_and_request_labels():

    assert BreakoutStrategy().name == "Breakout Strategy"
    assert BreakdownStrategy().name == "Breakdown Strategy"

    assert BreakoutStrategy().build_request().strategy_name == "Breakout Strategy"
    assert BreakdownStrategy().build_request().strategy_name == "Breakdown Strategy"