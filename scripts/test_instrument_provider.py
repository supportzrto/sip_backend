from app.market_data.providers.csv_provider import CSVProvider

provider = CSVProvider("data/candles")

instruments = provider.fetch_instruments()

print(f"Total Instruments: {len(instruments)}")

print()

print(instruments[0])

print()

print(instruments[-1])