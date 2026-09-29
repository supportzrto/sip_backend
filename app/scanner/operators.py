from decimal import Decimal

from app.scanner.enums import ComparisonOperator
from app.scanner.schemas import StockSnapshot

def compare(
    left: Decimal,
    operator: ComparisonOperator,
    right: Decimal,
) -> bool:
    """
    Compare two numeric values.
    """

    match operator:

        case ComparisonOperator.GREATER_THAN:
            return left > right

        case ComparisonOperator.LESS_THAN:
            return left < right

        case ComparisonOperator.GREATER_EQUAL:
            return left >= right

        case ComparisonOperator.LESS_EQUAL:
            return left <= right

        case ComparisonOperator.EQUAL:
            return left == right

        case ComparisonOperator.NOT_EQUAL:
            return left != right

    raise ValueError(
        f"Unsupported operator: {operator}"
    )




def crosses_above(
    stock: StockSnapshot,
    left: str,
    right: str,
) -> bool:
    """
    Returns True only when the left indicator
    crosses above the right indicator.
    """

    previous_left = stock.previous.values.get(left)
    previous_right = stock.previous.values.get(right)

    current_left = stock.current.values.get(left)
    current_right = stock.current.values.get(right)

    if None in (
        previous_left,
        previous_right,
        current_left,
        current_right,
    ):
        return False

    return (
        previous_left <= previous_right
        and
        current_left > current_right
    )


def crosses_below(
    stock: StockSnapshot,
    left: str,
    right: str,
) -> bool:
    """
    Returns True only when the left indicator
    crosses below the right indicator.
    """

    previous_left = stock.previous.values.get(left)
    previous_right = stock.previous.values.get(right)

    current_left = stock.current.values.get(left)
    current_right = stock.current.values.get(right)

    if None in (
        previous_left,
        previous_right,
        current_left,
        current_right,
    ):
        return False

    return (
        previous_left >= previous_right
        and
        current_left < current_right
    )