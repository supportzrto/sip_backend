from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.market_data.providers.base import MarketDataProvider
from app.market_data.schemas import (
    HistoricalCandle,
    HistoricalInstrument,
)


class CSVProvider(MarketDataProvider):
    """
    CSV implementation of the MarketDataProvider interface.
    """

    def __init__(self, data_directory: str):
        self.data_directory = data_directory

    def fetch_instruments(self) -> list[HistoricalInstrument]:
        """
        Discover all instruments from the historical candle dataset.
        One CSV file = One instrument.
        """

        instruments: list[HistoricalInstrument] = []

        candles_path = Path(self.data_directory)

        for csv_file in sorted(candles_path.glob("*.csv")):

            try:
                df = pd.read_csv(csv_file, nrows=1)

                if df.empty:
                    continue

                # Normalize column names
                df.columns = (
                    df.columns
                    .str.strip()
                    .str.lower()
                    .str.replace(" ", "_")
                )

                full_symbol = str(df.iloc[0]["symbol"]).strip()

                if ":" in full_symbol:
                    exchange, symbol = full_symbol.split(":", 1)
                else:
                    exchange = "NSE"
                    symbol = full_symbol

                instruments.append(
                    HistoricalInstrument(
                        symbol=symbol,
                        company_name=symbol,
                        exchange=exchange,
                        instrument_type="EQUITY",
                        isin=None,
                        provider="CSV",
                        provider_token=None,
                        is_active=True,
                    )
                )

            except Exception as e:
                print(f"Skipping {csv_file.name}: {e}")

        return instruments

    def fetch_daily_candles(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalCandle]:
        """
        Load historical daily candles from a CSV file.
        """

        file_path = Path(self.data_directory) / f"{symbol}.csv"

        if not file_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {file_path}"
            )

        df = pd.read_csv(file_path)

        print(file_path)
        print(f"Rows in CSV: {len(df)}")

        # Normalize column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        required_columns = {
            "datetime",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        # Convert datetime column once
        df["datetime"] = pd.to_datetime(df["datetime"]).dt.date

        # Filter by date if provided
        if start_date:
            df = df[df["datetime"] >= start_date]

        if end_date:
            df = df[df["datetime"] <= end_date]

        candles: list[HistoricalCandle] = []

        for row in df.itertuples(index=False):

            full_symbol = str(row.symbol).strip()

            if ":" in full_symbol:
                _, normalized_symbol = full_symbol.split(":", 1)
            else:
                normalized_symbol = full_symbol

            candles.append(
                HistoricalCandle(
                    symbol=normalized_symbol,
                    trade_date=row.datetime,
                    open=Decimal(str(row.open)),
                    high=Decimal(str(row.high)),
                    low=Decimal(str(row.low)),
                    close=Decimal(str(row.close)),
                    volume=int(row.volume),
                )
            )

        return candles