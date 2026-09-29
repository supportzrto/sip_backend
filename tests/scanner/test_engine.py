from decimal import Decimal

from app.scanner.engine import ScannerEngine
from app.scanner.enums import ComparisonOperator, IndicatorField, LogicalOperator
from app.scanner.schemas import (
    IndicatorSnapshot,
    ScanCondition,
    ScanExpression,
    ScanRequest,
    StockSnapshot,
)


def create_snapshot(
    current_values: dict[str, Decimal],
) -> StockSnapshot:
    """
    Helper to create a StockSnapshot for tests.
    """

    return StockSnapshot(
        current=IndicatorSnapshot(
            values=current_values,
        ),
        previous=IndicatorSnapshot(
            values={},
        ),
    )


def request_from(*conditions: ScanCondition) -> ScanRequest:
    """
    Helper to wrap conditions in an AND expression.
    """

    return ScanRequest(
        expression=ScanExpression(
            operator=LogicalOperator.AND,
            children=list(conditions),
        )
    )


def test_single_match():

    stocks = {

        "RELIANCE": create_snapshot(
            {
                "EMA20": Decimal("150"),
                "EMA50": Decimal("140"),
                "RSI14": Decimal("30"),
            }
        ),

        "TCS": create_snapshot(
            {
                "EMA20": Decimal("130"),
                "EMA50": Decimal("140"),
                "RSI14": Decimal("28"),
            }
        ),
    }

    request = request_from(

        ScanCondition(
            left=IndicatorField.EMA20,
            operator=ComparisonOperator.GREATER_THAN,
            right=IndicatorField.EMA50,
        ),

        ScanCondition(
            left=IndicatorField.RSI14,
            operator=ComparisonOperator.LESS_THAN,
            right=Decimal("35"),
        ),
    )

    engine = ScannerEngine()

    results = engine.scan(
        stocks,
        request,
    )

    assert len(results) == 1
    assert results[0].symbol == "RELIANCE"


def test_no_match():

    stocks = {

        "RELIANCE": create_snapshot(
            {
                "RSI14": Decimal("60"),
            }
        )
    }

    request = request_from(

        ScanCondition(
            left=IndicatorField.RSI14,
            operator=ComparisonOperator.LESS_THAN,
            right=Decimal("30"),
        )
    )

    engine = ScannerEngine()

    results = engine.scan(
        stocks,
        request,
    )

    assert results == []


def test_multiple_matches():

    stocks = {

        "RELIANCE": create_snapshot(
            {
                "RSI14": Decimal("20"),
            }
        ),

        "INFY": create_snapshot(
            {
                "RSI14": Decimal("25"),
            }
        ),

        "TCS": create_snapshot(
            {
                "RSI14": Decimal("45"),
            }
        ),
    }

    request = request_from(

        ScanCondition(
            left=IndicatorField.RSI14,
            operator=ComparisonOperator.LESS_THAN,
            right=Decimal("30"),
        )
    )

    engine = ScannerEngine()

    results = engine.scan(
        stocks,
        request,
    )

    assert len(results) == 2

    symbols = {result.symbol for result in results}
    assert symbols == {"RELIANCE", "INFY"}


def test_matches():

    snapshot = create_snapshot(
        {
            "EMA20": Decimal("150"),
            "EMA50": Decimal("120"),
        }
    )

    request = request_from(

        ScanCondition(
            left=IndicatorField.EMA20,
            operator=ComparisonOperator.GREATER_THAN,
            right=IndicatorField.EMA50,
        )
    )

    engine = ScannerEngine()

    assert engine.matches(
        snapshot,
        request,
    )


def test_crossover_condition_matches():
    """
    A breakout-style condition: EMA20 must have just
    crossed above EMA50 (not merely be above it).
    """

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("105"),
                "EMA50": Decimal("100"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "EMA20": Decimal("95"),
                "EMA50": Decimal("100"),
            }
        ),
    )

    request = request_from(
        ScanCondition(
            left=IndicatorField.EMA20,
            operator=ComparisonOperator.CROSSES_ABOVE,
            right=IndicatorField.EMA50,
        )
    )

    engine = ScannerEngine()

    assert engine.matches(snapshot, request)


def test_crossover_condition_no_crossover_does_not_match():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("150"),
                "EMA50": Decimal("100"),
            }
        ),
        previous=IndicatorSnapshot(
            values={
                "EMA20": Decimal("145"),
                "EMA50": Decimal("100"),
            }
        ),
    )

    request = request_from(
        ScanCondition(
            left=IndicatorField.EMA20,
            operator=ComparisonOperator.CROSSES_ABOVE,
            right=IndicatorField.EMA50,
        )
    )

    engine = ScannerEngine()

    # EMA20 was already above EMA50 yesterday, so this is
    # not a fresh crossover.
    assert not engine.matches(snapshot, request)