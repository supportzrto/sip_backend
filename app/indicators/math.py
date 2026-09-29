from decimal import Decimal


def calculate_ema(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate EMA from numeric values.

    Returns only valid EMA values.
    """

    if len(values) < period:
        return []

    alpha = Decimal("2") / Decimal(period + 1)

    sma = sum(values[:period]) / Decimal(period)

    ema_values = [sma]

    previous = sma

    for value in values[period:]:

        current = previous + (
            alpha * (value - previous)
        )

        ema_values.append(current)

        previous = current

    return ema_values