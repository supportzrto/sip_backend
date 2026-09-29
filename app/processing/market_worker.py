from app.market.analyzer import MarketAnalyzer
from app.market_data.providers.csv_provider import CSVProvider

DATA_DIRECTORY = "data/candles"


def analyze_symbol(symbol: str):
    """
    Analyze one symbol and return its snapshot.
    """

    provider = CSVProvider(DATA_DIRECTORY)
    analyzer = MarketAnalyzer()

    try:
        candles = provider.fetch_daily_candles(symbol)

        snapshot = analyzer.analyze(candles)

        return symbol, snapshot

    except Exception:

        return symbol, None