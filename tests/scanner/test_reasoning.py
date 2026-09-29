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


def test_and_expression_returns_reason_for_every_matched_condition():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("150"),
                "EMA50": Decimal("140"),
                "RSI14": Decimal("28"),
            }
        ),
        previous=IndicatorSnapshot(values={}),
    )

    stocks = {"RELIANCE": snapshot}

    request = ScanRequest(
        expression=ScanExpression(
            operator=LogicalOperator.AND,
            children=[
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
            ],
        )
    )

    engine = ScannerEngine()
    results = engine.scan(stocks, request)

    assert len(results) == 1
    assert len(results[0].reasons) == 2
    assert "EMA20 (150.00) > EMA50 (140.00)" in results[0].reasons
    assert "RSI14 (28.00) < 35.00" in results[0].reasons


def test_crossover_condition_produces_readable_reason():

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

    stocks = {"TCS": snapshot}

    request = ScanRequest(
        expression=ScanExpression(
            operator=LogicalOperator.AND,
            children=[
                ScanCondition(
                    left=IndicatorField.EMA20,
                    operator=ComparisonOperator.CROSSES_ABOVE,
                    right=IndicatorField.EMA50,
                ),
            ],
        )
    )

    engine = ScannerEngine()
    results = engine.scan(stocks, request)

    assert len(results) == 1
    assert results[0].reasons == [
        "EMA20 crossed above EMA50 (105.00 vs 100.00)"
    ]


def test_or_expression_only_includes_reason_for_matching_branch():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={
                "RSI14": Decimal("25"),
                "ADX14": Decimal("10"),
            }
        ),
        previous=IndicatorSnapshot(values={}),
    )

    stocks = {"INFY": snapshot}

    request = ScanRequest(
        expression=ScanExpression(
            operator=LogicalOperator.OR,
            children=[
                ScanCondition(
                    left=IndicatorField.RSI14,
                    operator=ComparisonOperator.LESS_THAN,
                    right=Decimal("30"),
                ),
                ScanCondition(
                    left=IndicatorField.ADX14,
                    operator=ComparisonOperator.GREATER_THAN,
                    right=Decimal("25"),
                ),
            ],
        )
    )

    engine = ScannerEngine()
    results = engine.scan(stocks, request)

    assert len(results) == 1
    # Only the RSI14 branch was true; ADX14 branch was false and
    # should not contribute a reason.
    assert results[0].reasons == ["RSI14 (25.00) < 30.00"]


def test_no_match_returns_no_results():

    snapshot = StockSnapshot(
        current=IndicatorSnapshot(
            values={"RSI14": Decimal("60")}
        ),
        previous=IndicatorSnapshot(values={}),
    )

    stocks = {"TCS": snapshot}

    request = ScanRequest(
        expression=ScanExpression(
            operator=LogicalOperator.AND,
            children=[
                ScanCondition(
                    left=IndicatorField.RSI14,
                    operator=ComparisonOperator.LESS_THAN,
                    right=Decimal("30"),
                ),
            ],
        )
    )

    engine = ScannerEngine()
    results = engine.scan(stocks, request)

    assert results == []