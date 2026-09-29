from decimal import Decimal, ROUND_HALF_UP

# Standard precision for indicator values.
INDICATOR_PRECISION = Decimal("0.0001")


def round_decimal(
    value: Decimal,
) -> Decimal:
    """
    Round indicator values using the project's standard precision.
    """

    return value.quantize(
        INDICATOR_PRECISION,
        rounding=ROUND_HALF_UP,
    )