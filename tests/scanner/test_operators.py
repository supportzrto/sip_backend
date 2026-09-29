from decimal import Decimal

from app.scanner.enums import ComparisonOperator
from app.scanner.operators import compare


def test_greater_than():

    assert compare(
        Decimal("10"),
        ComparisonOperator.GREATER_THAN,
        Decimal("5"),
    )


def test_less_than():

    assert compare(
        Decimal("5"),
        ComparisonOperator.LESS_THAN,
        Decimal("10"),
    )


def test_greater_equal():

    assert compare(
        Decimal("5"),
        ComparisonOperator.GREATER_EQUAL,
        Decimal("5"),
    )


def test_less_equal():

    assert compare(
        Decimal("5"),
        ComparisonOperator.LESS_EQUAL,
        Decimal("5"),
    )


def test_equal():

    assert compare(
        Decimal("10"),
        ComparisonOperator.EQUAL,
        Decimal("10"),
    )


def test_not_equal():

    assert compare(
        Decimal("10"),
        ComparisonOperator.NOT_EQUAL,
        Decimal("20"),
    )