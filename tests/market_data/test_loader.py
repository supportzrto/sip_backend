from pathlib import Path

from app.market_data.loader import MarketLoader


def test_loader(tmp_path: Path):

    (tmp_path / "RELIANCE.csv").touch()

    (tmp_path / "INFY.csv").touch()

    loader = MarketLoader(str(tmp_path))

    assert loader.symbols() == [

        "INFY",

        "RELIANCE",

    ]