from app.indicators.supertrend import SupertrendIndicator
from app.market_data.providers.csv_provider import CSVProvider


def main():

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    indicator = SupertrendIndicator()

    values = indicator.calculate(candles)

    print(f"Calculated {len(values)} Supertrend values")

    bullish = sum(
        1 for v in values
        if v.is_bullish
    )

    bearish = len(values) - bullish

    print(f"Bullish: {bullish}")
    print(f"Bearish: {bearish}")

    print()
    print("=" * 100)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()