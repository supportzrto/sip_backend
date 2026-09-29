from pathlib import Path


class MarketLoader:
    """
    Finds available market data files.
    """

    def __init__(
        self,
        data_directory: str,
    ):
        self.path = Path(data_directory)

    def symbols(self) -> list[str]:

        return sorted(

            file.stem

            for file in self.path.rglob("*.csv")

        )