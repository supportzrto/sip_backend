from app.indicators.bollinger import BollingerBandsIndicator
from app.market_data.providers.csv_provider import CSVProvider


def main():

    provider = CSVProvider("data/candles")

    candles = provider.fetch_daily_candles("RELIANCE")

    print(f"Loaded {len(candles)} candles")

    indicator = BollingerBandsIndicator()

    values = indicator.calculate(candles)

    print(f"Calculated {len(values)} Bollinger values")

    print()
    print("=" * 100)

    for value in values[:10]:
        print(value)


if __name__ == "__main__":
    main()