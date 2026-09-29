from decimal import Decimal

from app.scanner.enums import (
    ComparisonOperator,
    LogicalOperator,
)
from app.scanner.expression import evaluate_expression
from app.scanner.schemas import (
    IndicatorSnapshot,
    ScanCondition,
    ScanExpression,
    StockSnapshot,
)


def test_and_expression():

    stock = StockSnapshot(

        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("120"),
                "EMA50": Decimal("100"),
                "RSI14": Decimal("28"),
            }
        ),

        previous=IndicatorSnapshot(values={}),
    )

    expression = ScanExpression(

        operator=LogicalOperator.AND,

        children=[

            ScanCondition(
                left="EMA20",
                operator=ComparisonOperator.GREATER_THAN,
                right="EMA50",
            ),

            ScanCondition(
                left="RSI14",
                operator=ComparisonOperator.LESS_THAN,
                right=Decimal("30"),
            ),
        ],
    )

    assert evaluate_expression(
        stock,
        expression,
    )