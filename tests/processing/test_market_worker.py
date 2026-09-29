from app.processing.market_worker import analyze_symbol


def test_market_worker():

    symbol, snapshot = analyze_symbol("RELIANCE")

    assert symbol == "RELIANCE"

    assert snapshot is not None