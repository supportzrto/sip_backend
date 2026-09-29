from concurrent.futures import ProcessPoolExecutor
from collections.abc import Callable


class ParallelProcessor:
    """
    Executes CPU-bound work using multiple processes.
    """

    @staticmethod
    def process(
        items: list,
        worker: Callable,
        max_workers: int | None = None,
    ):
        """
        Run worker(item) in parallel.

        Returns results in the same order
        as the input items.
        """

        with ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:

            results = list(
                executor.map(
                    worker,
                    items,
                )
            )

        return results