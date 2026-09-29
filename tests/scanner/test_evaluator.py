from decimal import Decimal

import pytest

from app.scanner.enums import ComparisonOperator
from app.scanner.evaluator import evaluate_condition
from app.scanner.schemas import ScanCondition


def test_indicator_vs_indicator():

    indicators = {
        "EMA20": Decimal("150"),
        "EMA50": Decimal("140"),
    }

    condition = ScanCondition(
        left="EMA20",
        operator=ComparisonOperator.GREATER_THAN,
        right="EMA50",
    )

    assert evaluate_condition(
        indicators,
        condition,
    )


def test_indicator_vs_value():

    indicators = {
        "RSI14": Decimal("28"),
    }

    condition = ScanCondition(
        left="RSI14",
        operator=ComparisonOperator.LESS_THAN,
        right=Decimal("30"),
    )

    assert evaluate_condition(
        indicators,
        condition,
    )


def test_false_condition():

    indicators = {
        "RSI14": Decimal("55"),
    }

    condition = ScanCondition(
        left="RSI14",
        operator=ComparisonOperator.LESS_THAN,
        right=Decimal("30"),
    )

    assert not evaluate_condition(
        indicators,
        condition,
    )


def test_unknown_left_indicator():

    indicators = {}

    condition = ScanCondition(
        left="EMA20",
        operator=ComparisonOperator.GREATER_THAN,
        right=Decimal("10"),
    )

    assert (
        evaluate_condition(
            indicators,
            condition,
        )
        is False
)


def test_unknown_right_indicator():

    indicators = {
        "EMA20": Decimal("100"),
    }

    condition = ScanCondition(
        left="EMA20",
        operator=ComparisonOperator.GREATER_THAN,
        right="EMA50",
    )

    assert (
        evaluate_condition(
            indicators,
            condition,
        )
        is False
)