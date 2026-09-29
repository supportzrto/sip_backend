import time

from app.market.analyzer import MarketAnalyzer
from app.market_data.loader import MarketLoader
from app.market_data.providers.csv_provider import CSVProvider
from app.scanner.engine import ScannerEngine
from app.scanner.strategies import SwingStrategy
from app.processing.parallel import ParallelProcessor
from app.processing.market_worker import analyze_symbol

import time

DATA_DIRECTORY = "data/candles"


def main():

    start_time = time.perf_counter()

    print("=" * 80)
    print("SIP MARKET SCANNER")
    print("=" * 80)

    loader = MarketLoader(DATA_DIRECTORY)
    provider = CSVProvider(DATA_DIRECTORY)
    analyzer = MarketAnalyzer()
    scanner = ScannerEngine()

    strategy = SwingStrategy()
    request = strategy.build_request()

    symbols = loader.symbols()

    print(f"\nFound {len(symbols)} symbols\n")

    snapshots = {}

    total = len(symbols)

    for index, symbol in enumerate(symbols, start=1):

        try:

            candles = provider.fetch_daily_candles(symbol)

            snapshots[symbol] = analyzer.analyze(candles)

            # if symbol == "RELIANCE":
            #     print("\nSnapshot values:")
            #     print(snapshots[symbol].current.values)
            #     return

        except Exception as exc:

            print(f"\nSkipped {symbol}: {exc}")

        # Show progress every 100 stocks
        if index % 100 == 0 or index == total:

            print(f"Processed {index}/{total}")

    print("\nRunning Scanner...\n")

    results = scanner.scan(
        snapshots,
        request,
    )

    elapsed = time.perf_counter() - start_time

    print("=" * 80)
    print("SCAN RESULTS")
    print("=" * 80)

    if results:

        for result in results:
            print(f"✓ {result.symbol}")

    else:

        print("No matching stocks found.")

    print("\n" + "=" * 80)
    print(f"Stocks Loaded : {len(snapshots)}")
    print(f"Matches Found : {len(results)}")
    print(f"Completed In  : {elapsed:.2f} seconds")
    print("=" * 80)


if __name__ == "__main__":
    main()