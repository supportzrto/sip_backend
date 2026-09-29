from app.market_data.schemas import HistoricalCandle


class CandleValidator:
    """
    Validates historical market candles.

    This validator is independent of:
    - CSV
    - Pandas
    - Database
    - Data Provider
    """

    @staticmethod
    def validate(candle: HistoricalCandle) -> None:
        """
        Validate a single historical candle.

        Raises:
            ValueError: If validation fails.
        """

        symbol = candle.symbol.strip().upper()

        if not symbol:
           raise ValueError("Symbol cannot be empty.")

        if not candle.symbol.strip():
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) " "Symbol cannot be empty."
            )

        if candle.open <= 0:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "Open price must be greater than zero."
            )

        if candle.high <= 0:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "High price must be greater than zero."
            )

        if candle.low <= 0:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "Low price must be greater than zero."
            )

        if candle.close <= 0:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "Close price must be greater than zero."
            )

        if candle.volume < 0:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) " "Volume cannot be negative."
            )

        if candle.high < candle.open:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "High price cannot be lower than Open price."
            )

        if candle.high < candle.close:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "High price cannot be lower than Close price."
            )

        if candle.high < candle.low:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "High price cannot be lower than Low price."
            )

        if candle.low > candle.open:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "Low price cannot be greater than Open price."
            )

        if candle.low > candle.close:
            raise ValueError(
                f"{candle.symbol} ({candle.trade_date}) "
                "Low price cannot be greater than Close price."
            )
