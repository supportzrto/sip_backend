from decimal import Decimal
from math import sqrt
from typing import NamedTuple
from app.indicators.utils import round_decimal
from app.market_data.schemas import HistoricalCandle


class MACDResult(NamedTuple):
    macd: list[Decimal]
    signal: list[Decimal]
    histogram: list[Decimal]

class DirectionalMovementResult(NamedTuple):
    positive_dm: list[Decimal]
    negative_dm: list[Decimal]

class DirectionalIndicatorResult(NamedTuple):
    """
    Positive and Negative Directional Indicators.
    """

    positive_di: list[Decimal]
    negative_di: list[Decimal]

class BollingerBandsResult(NamedTuple):
    middle: list[Decimal]
    upper: list[Decimal]
    lower: list[Decimal]

class SupertrendBandsResult(NamedTuple):
    """
    Basic / Final Supertrend bands.
    """

    upper: list[Decimal]
    lower: list[Decimal]

class SupertrendResult(NamedTuple):
    values: list[Decimal]
    bullish: list[bool]


def calculate_sma(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate Simple Moving Average (SMA).

    Returns only valid SMA values.
    """

    if len(values) < period:
        return []

    running_sum = sum(values[:period])

    sma_values = [
        round_decimal(
            running_sum / Decimal(period)
        )
    ]

    for index in range(period, len(values)):

        running_sum += values[index]
        running_sum -= values[index - period]

        sma_values.append(
            round_decimal(
                running_sum / Decimal(period)
            )
        )

    return sma_values


def calculate_ema(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate Exponential Moving Average (EMA).

    Returns only valid EMA values.
    """

    if len(values) < period:
        return []

    alpha = Decimal("2") / Decimal(period + 1)

    previous = round_decimal(
        sum(values[:period]) / Decimal(period)
    )

    ema_values = [previous]

    for value in values[period:]:

        current = round_decimal(
            previous
            + alpha * (value - previous)
        )

        ema_values.append(current)

        previous = current

    return ema_values


def calculate_macd(
    values: list[Decimal],
    fast_period: int,
    slow_period: int,
    signal_period: int,
) -> MACDResult:
    """
    Calculate MACD using close prices.

    Returns:
        MACDResult containing:
            - macd
            - signal
            - histogram
    """

    if len(values) < slow_period:
        return MACDResult([], [], [])

    fast_ema = calculate_ema(
        values,
        fast_period,
    )

    slow_ema = calculate_ema(
        values,
        slow_period,
    )

    # Align the fast EMA with the slow EMA
    offset = slow_period - fast_period

    aligned_fast = fast_ema[offset:]

    macd_line = [
        round_decimal(fast - slow)
        for fast, slow in zip(
            aligned_fast,
            slow_ema,
        )
    ]

    signal_line = calculate_ema(
        macd_line,
        signal_period,
    )

    # Align MACD line with signal line
    macd_offset = signal_period - 1

    aligned_macd = macd_line[macd_offset:]

    histogram = [
        round_decimal(macd - signal)
        for macd, signal in zip(
            aligned_macd,
            signal_line,
        )
    ]

    return MACDResult(
        macd=aligned_macd,
        signal=signal_line,
        histogram=histogram,
    )

def calculate_rsi(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate Relative Strength Index (RSI)
    using Wilder's smoothing.
    """

    if len(values) <= period:
        return []

    gains: list[Decimal] = []
    losses: list[Decimal] = []

    # Calculate price changes
    for index in range(1, len(values)):

        change = values[index] - values[index - 1]

        gains.append(
            max(change, Decimal("0"))
        )

        losses.append(
            max(-change, Decimal("0"))
        )

    # Initial averages
    average_gain = (
        sum(gains[:period])
        / Decimal(period)
    )

    average_loss = (
        sum(losses[:period])
        / Decimal(period)
    )

    rsi_values: list[Decimal] = []

    # First RSI
    if average_loss == 0:
        rsi_values.append(
            Decimal("100.0000")
        )
    else:

        rs = average_gain / average_loss

        rsi = Decimal("100") - (
            Decimal("100")
            / (Decimal("1") + rs)
        )

        rsi_values.append(
            round_decimal(rsi)
        )

    # Wilder smoothing
    for index in range(period, len(gains)):

        average_gain = (
            (
                average_gain
                * Decimal(period - 1)
            )
            + gains[index]
        ) / Decimal(period)

        average_loss = (
            (
                average_loss
                * Decimal(period - 1)
            )
            + losses[index]
        ) / Decimal(period)

        if average_loss == 0:

            rsi_values.append(
                Decimal("100.0000")
            )

            continue

        rs = average_gain / average_loss

        rsi = Decimal("100") - (
            Decimal("100")
            / (Decimal("1") + rs)
        )

        rsi_values.append(
            round_decimal(rsi)
        )

    return rsi_values

def calculate_directional_movement(
    candles: list[HistoricalCandle],
) -> DirectionalMovementResult:
    """
    Calculate Positive and Negative Directional Movement (+DM / -DM).
    """

    if len(candles) < 2:
        return DirectionalMovementResult([], [])

    positive_dm: list[Decimal] = []
    negative_dm: list[Decimal] = []

    for index in range(1, len(candles)):

        current = candles[index]
        previous = candles[index - 1]

        up_move = current.high - previous.high
        down_move = previous.low - current.low

        if up_move > down_move and up_move > 0:
            positive_dm.append(round_decimal(up_move))
        else:
            positive_dm.append(Decimal("0.0000"))

        if down_move > up_move and down_move > 0:
            negative_dm.append(round_decimal(down_move))
        else:
            negative_dm.append(Decimal("0.0000"))

    return DirectionalMovementResult(
        positive_dm=positive_dm,
        negative_dm=negative_dm,
    )

def calculate_directional_indicators(
    positive_dm: list[Decimal],
    negative_dm: list[Decimal],
    true_ranges: list[Decimal],
    period: int,
) -> DirectionalIndicatorResult:
    """
    Calculate +DI and -DI.
    """

    if (
        len(positive_dm) < period
        or len(negative_dm) < period
        or len(true_ranges) < period
    ):
        return DirectionalIndicatorResult([], [])

    smoothed_positive = calculate_wilder_smoothing(
        positive_dm,
        period,
    )

    smoothed_negative = calculate_wilder_smoothing(
        negative_dm,
        period,
    )

    smoothed_tr = calculate_wilder_smoothing(
        true_ranges,
        period,
    )

    positive_di: list[Decimal] = []
    negative_di: list[Decimal] = []

    for plus_dm, minus_dm, atr in zip(
        smoothed_positive,
        smoothed_negative,
        smoothed_tr,
    ):

        if atr == Decimal("0.0000"):

            positive_di.append(
                Decimal("0.0000")
            )

            negative_di.append(
                Decimal("0.0000")
            )

            continue

        positive_di.append(
            round_decimal(
                Decimal("100")
                * plus_dm
                / atr
            )
        )

        negative_di.append(
            round_decimal(
                Decimal("100")
                * minus_dm
                / atr
            )
        )

    return DirectionalIndicatorResult(
        positive_di=positive_di,
        negative_di=negative_di,
    )

def calculate_dx(
    positive_di: list[Decimal],
    negative_di: list[Decimal],
) -> list[Decimal]:
    """
    Calculate Directional Index (DX).
    """

    dx_values: list[Decimal] = []

    for plus_di, minus_di in zip(
        positive_di,
        negative_di,
    ):

        denominator = plus_di + minus_di

        if denominator == Decimal("0.0000"):

            dx_values.append(
                Decimal("0.0000")
            )

            continue

        dx = (
            Decimal("100")
            * abs(plus_di - minus_di)
            / denominator
        )

        dx_values.append(
            round_decimal(dx)
        )

    return dx_values

def calculate_adx(
    candles: list[HistoricalCandle],
    period: int,
) -> list[Decimal]:
    """
    Calculate Average Directional Index (ADX).
    """

    if len(candles) <= period:
        return []

    true_ranges = calculate_true_range(
        candles,
    )

    dm = calculate_directional_movement(
        candles,
    )

    di = calculate_directional_indicators(
        dm.positive_dm,
        dm.negative_dm,
        true_ranges,
        period,
    )

    dx = calculate_dx(
        di.positive_di,
        di.negative_di,
    )

    return calculate_wilder_smoothing(
        dx,
        period,
    )


def calculate_wilder_smoothing(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate Wilder's smoothing.

    Returns only valid smoothed values.
    """

    if len(values) < period:
        return []

    average = (
        sum(values[:period])
        / Decimal(period)
    )

    smoothed = [
        round_decimal(average)
    ]

    for value in values[period:]:

        average = (
            (
                average
                * Decimal(period - 1)
            )
            + value
        ) / Decimal(period)

        smoothed.append(
            round_decimal(average)
        )

    return smoothed



def calculate_true_range(
    candles: list[HistoricalCandle],
) -> list[Decimal]:
    """
    Calculate True Range (TR).

    Returns one True Range value for every candle
    except the first.
    """

    if len(candles) < 2:
        return []

    true_ranges: list[Decimal] = []

    for index in range(1, len(candles)):

        current = candles[index]
        previous = candles[index - 1]

        tr = max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )

        true_ranges.append(
            round_decimal(tr)
        )

    return true_ranges

def calculate_atr(
    candles: list[HistoricalCandle],
    period: int,
) -> list[Decimal]:
    """
    Calculate Average True Range (ATR)
    using Wilder's smoothing.
    """

    true_ranges = calculate_true_range(
        candles
    )

    if len(true_ranges) < period:
        return []

    average = (
        sum(true_ranges[:period])
        / Decimal(period)
    )

    atr_values = [
        round_decimal(average)
    ]

    for tr in true_ranges[period:]:

        average = (
            (
                average
                * Decimal(period - 1)
            )
            + tr
        ) / Decimal(period)

        atr_values.append(
            round_decimal(average)
        )

    return atr_values



def calculate_standard_deviation(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Calculate rolling standard deviation.

    Returns one standard deviation
    for every valid window.
    """

    if len(values) < period:
        return []

    stddev_values: list[Decimal] = []

    for start in range(
        len(values) - period + 1
    ):

        window = values[
            start : start + period
        ]

        mean = (
            sum(window)
            / Decimal(period)
        )

        variance = (
            sum(
                (
                    value - mean
                ) ** 2
                for value in window
            )
            / Decimal(period)
        )

        stddev = Decimal(
            str(
                sqrt(
                    float(variance)
                )
            )
        )

        stddev_values.append(
            round_decimal(stddev)
        )

    return stddev_values

def calculate_bollinger_bands(
    values: list[Decimal],
    period: int,
    multiplier: Decimal = Decimal("2"),
) -> BollingerBandsResult:
    """
    Calculate Bollinger Bands.

    Returns:
        - Middle Band (SMA)
        - Upper Band
        - Lower Band
    """

    middle = calculate_sma(
        values,
        period,
    )

    stddev = calculate_standard_deviation(
        values,
        period,
    )

    upper: list[Decimal] = []
    lower: list[Decimal] = []

    for sma, sd in zip(
        middle,
        stddev,
    ):

        upper.append(
            round_decimal(
                sma + multiplier * sd
            )
        )

        lower.append(
            round_decimal(
                sma - multiplier * sd
            )
        )

    return BollingerBandsResult(
        middle=middle,
        upper=upper,
        lower=lower,
    )

def calculate_basic_bands(
    candles: list[HistoricalCandle],
    atr_values: list[Decimal],
    period: int,
    multiplier: Decimal,
) -> SupertrendBandsResult:
    """
    Calculate basic upper/lower bands.
    """

    upper: list[Decimal] = []
    lower: list[Decimal] = []

    for candle, atr in zip(
        candles[period:],
        atr_values,
    ):

        hl2 = (
            candle.high + candle.low
        ) / Decimal("2")

        upper.append(
            round_decimal(
                hl2 + multiplier * atr
            )
        )

        lower.append(
            round_decimal(
                hl2 - multiplier * atr
            )
        )

    return SupertrendBandsResult(
        upper=upper,
        lower=lower,
    )

def calculate_final_bands(
    candles: list[HistoricalCandle],
    basic: SupertrendBandsResult,
    period: int,
) -> SupertrendBandsResult:
    """
    Calculate final upper and lower bands.
    """

    if not basic.upper:
        return SupertrendBandsResult([], [])

    final_upper = [basic.upper[0]]
    final_lower = [basic.lower[0]]

    # candles aligned with ATR/basic bands
    aligned = candles[period:]

    for index in range(1, len(basic.upper)):

        previous_close = aligned[index - 1].close

        previous_upper = final_upper[-1]
        previous_lower = final_lower[-1]

        current_upper = basic.upper[index]
        current_lower = basic.lower[index]

        # Final Upper Band
        if (
            current_upper < previous_upper
            or previous_close > previous_upper
        ):
            final_upper.append(current_upper)
        else:
            final_upper.append(previous_upper)

        # Final Lower Band
        if (
            current_lower > previous_lower
            or previous_close < previous_lower
        ):
            final_lower.append(current_lower)
        else:
            final_lower.append(previous_lower)

    return SupertrendBandsResult(
        upper=final_upper,
        lower=final_lower,
    )

def calculate_supertrend(
    candles: list[HistoricalCandle],
    final_bands: SupertrendBandsResult,
    period: int,
) -> SupertrendResult:
    """
    Calculate Supertrend values and trend direction.
    """

    if not final_bands.upper:
        return SupertrendResult([], [])

    aligned = candles[period:]

    supertrend: list[Decimal] = []
    bullish: list[bool] = []

    # Initial trend
    first_close = aligned[0].close

    if first_close >= final_bands.lower[0]:
        supertrend.append(final_bands.lower[0])
        bullish.append(True)
    else:
        supertrend.append(final_bands.upper[0])
        bullish.append(False)

    for index in range(1, len(aligned)):

        current_close = aligned[index].close

        previous_trend = bullish[-1]

        current_upper = final_bands.upper[index]
        current_lower = final_bands.lower[index]

        # Bullish trend
        if previous_trend:

            if current_close < current_lower:

                bullish.append(False)

                supertrend.append(current_upper)

            else:

                bullish.append(True)

                supertrend.append(current_lower)

        # Bearish trend
        else:

            if current_close > current_upper:

                bullish.append(True)

                supertrend.append(current_lower)

            else:

                bullish.append(False)

                supertrend.append(current_upper)

    return SupertrendResult(
        values=supertrend,
        bullish=bullish,
    )

def calculate_rolling_max_lagged(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Highest value over the PRIOR `period` values, excluding the
    current index -- i.e. for index i, looks at values[i-period:i].

    This lag is what makes it usable as a breakout reference level:
    "today's close breaks above the highest high of the preceding
    N days" needs a window that does NOT include today itself,
    otherwise the condition could never trigger (today's own high
    is always >= today's close).
    """

    if len(values) <= period:
        return []

    return [
        max(values[i - period:i])
        for i in range(period, len(values))
    ]


def calculate_rolling_min_lagged(
    values: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Lowest value over the PRIOR `period` values, excluding the
    current index. See calculate_rolling_max_lagged for why the lag
    matters.
    """

    if len(values) <= period:
        return []

    return [
        min(values[i - period:i])
        for i in range(period, len(values))
    ]


def calculate_volume_surge(
    volumes: list[Decimal],
    period: int,
) -> list[Decimal]:
    """
    Ratio of the current day's volume to the average volume over the
    PRIOR `period` days (excluding today). A value of 2.0 means
    today's volume is twice the recent average -- the standard
    confirmation signal used alongside a price breakout.
    """

    if len(volumes) <= period:
        return []

    results = []

    for i in range(period, len(volumes)):

        window = volumes[i - period:i]
        average = sum(window) / Decimal(period)

        if average == 0:
            results.append(Decimal("0"))
            continue

        results.append(
            round_decimal(volumes[i] / average)
        )

    return results