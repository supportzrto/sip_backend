from app.indicators.macd import MACDIndicator
from app.market_data.providers.csv_provider import CSVProvider


def main():

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    indicator = MACDIndicator()

    values = indicator.calculate(candles)

    print(f"Calculated {len(values)} MACD values")

    print()
    print("=" * 100)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()