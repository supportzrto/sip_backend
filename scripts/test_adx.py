from app.indicators.adx import ADXIndicator
from app.market_data.providers.csv_provider import CSVProvider


def main():

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    indicator = ADXIndicator()

    values = indicator.calculate(candles)

    print(f"Calculated {len(values)} ADX values")

    print()
    print("=" * 100)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()