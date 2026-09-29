from pathlib import Path
from datetime import datetime


class MarketDataLogger:
    """
    Logs invalid market data during imports.
    """

    def __init__(self):

        log_directory = Path("logs/market_data")
        log_directory.mkdir(parents=True, exist_ok=True)

        filename = datetime.now().strftime(
            "invalid_candles_%Y%m%d.log"
        )

        self.log_file = log_directory / filename

    def log_invalid_candle(
        self,
        symbol: str,
        trade_date,
        error: str,
    ) -> None:

        with open(
            self.log_file,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                f"{symbol} | {trade_date} | {error}\n"
            )