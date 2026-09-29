from decimal import Decimal
from enum import Enum

from app.scanner.enums import ComparisonOperator
from app.scanner.operators import compare, crosses_above, crosses_below
from app.scanner.schemas import ScanCondition, StockSnapshot


def evaluate_condition(
    indicators: dict[str, Decimal],
    condition: ScanCondition,
) -> bool:
    """
    Evaluate a single scan condition.
    """

    # Resolve left indicator
    left_key = (
        condition.left.value
        if isinstance(condition.left, Enum)
        else condition.left
    )

    if left_key not in indicators:
        return False

    left_value = indicators[left_key]

    # Right side can be another indicator or a constant
    if isinstance(condition.right, Decimal):

        right_value = condition.right

    else:

        right_key = (
            condition.right.value
            if isinstance(condition.right, Enum)
            else condition.right
        )

        # print("\n======================")
        # print("Condition:", condition)
        # print("Left Key :", left_key, type(left_key))
        # print("Right Key:", right_key, type(right_key))
        # print("Indicator Keys:", sorted(indicators.keys()))
        # print("======================")

        if right_key not in indicators:
            return False

        right_value = indicators[right_key]

    return compare(
        left_value,
        condition.operator,
        right_value,
    )


def evaluate_condition_on_stock(
    stock: StockSnapshot,
    condition: ScanCondition,
) -> bool:
    """
    Evaluate a single scan condition against a full stock snapshot.

    Unlike evaluate_condition (which only sees "today's" indicator
    values), this also has access to "previous" values, so it can
    additionally handle crossover operators (CROSSES_ABOVE /
    CROSSES_BELOW) used to detect breakouts and breakdowns.
    """

    if condition.operator in (
        ComparisonOperator.CROSSES_ABOVE,
        ComparisonOperator.CROSSES_BELOW,
    ):

        # Crossovers only make sense between two indicators,
        # not against a fixed constant.
        if isinstance(condition.right, Decimal):
            return False

        left_key = (
            condition.left.value
            if isinstance(condition.left, Enum)
            else condition.left
        )

        right_key = (
            condition.right.value
            if isinstance(condition.right, Enum)
            else condition.right
        )

        if condition.operator == ComparisonOperator.CROSSES_ABOVE:
            return crosses_above(stock, left_key, right_key)

        return crosses_below(stock, left_key, right_key)

    return evaluate_condition(stock.current.values, condition)