from app.market_data.providers.csv_provider import CSVProvider
from app.indicators.sma import SMAIndicator


def main() -> None:

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    sma20 = SMAIndicator(period=20)

    values = sma20.calculate(candles)

    print(f"Calculated {len(values)} SMA values")

    print()
    print("=" * 80)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()