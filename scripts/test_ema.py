from app.market_data.providers.csv_provider import CSVProvider
from app.indicators.ema import EMAIndicator


def main() -> None:

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    ema20 = EMAIndicator(period=20)

    values = ema20.calculate(candles)

    print(f"Calculated {len(values)} EMA values")

    print()
    print("=" * 80)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()