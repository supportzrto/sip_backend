"""
Turns a matched ScanCondition into a plain-English reason,
e.g. "RSI14 (28.40) < 35" or "EMA20 crossed above EMA50 (105.20 vs 100.00)".

This is what powers the "why did this stock break out / break down"
explanation shown to the user, instead of just returning a bare symbol.
"""

from decimal import Decimal
from enum import Enum

from app.scanner.enums import ComparisonOperator
from app.scanner.schemas import ScanCondition, StockSnapshot

_OPERATOR_LABELS: dict[ComparisonOperator, str] = {
    ComparisonOperator.GREATER_THAN: ">",
    ComparisonOperator.LESS_THAN: "<",
    ComparisonOperator.GREATER_EQUAL: ">=",
    ComparisonOperator.LESS_EQUAL: "<=",
    ComparisonOperator.EQUAL: "==",
    ComparisonOperator.NOT_EQUAL: "!=",
}


def _field_name(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _format_value(value: Decimal | int | bool | None) -> str:

    if value is None:
        return "n/a"

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, Decimal):
        return f"{value:.2f}"

    return str(value)


def describe_condition(
    stock: StockSnapshot,
    condition: ScanCondition,
) -> str:
    """
    Build a human-readable description of a single matched condition,
    using the stock's actual current/previous values.
    """

    left_key = _field_name(condition.left)

    if condition.operator in (
        ComparisonOperator.CROSSES_ABOVE,
        ComparisonOperator.CROSSES_BELOW,
    ):

        right_key = _field_name(condition.right)

        current_left = stock.current.values.get(left_key)
        current_right = stock.current.values.get(right_key)

        verb = (
            "crossed above"
            if condition.operator == ComparisonOperator.CROSSES_ABOVE
            else "crossed below"
        )

        return (
            f"{left_key} {verb} {right_key} "
            f"({_format_value(current_left)} vs {_format_value(current_right)})"
        )

    label = _OPERATOR_LABELS.get(
        condition.operator,
        condition.operator.value,
    )

    left_value = stock.current.values.get(left_key)

    if isinstance(condition.right, Decimal):
        return (
            f"{left_key} ({_format_value(left_value)}) "
            f"{label} {_format_value(condition.right)}"
        )

    right_key = _field_name(condition.right)
    right_value = stock.current.values.get(right_key)

    return (
        f"{left_key} ({_format_value(left_value)}) "
        f"{label} {right_key} ({_format_value(right_value)})"
    )