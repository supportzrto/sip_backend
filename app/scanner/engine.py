from app.scanner.expression import (
    evaluate_expression,
    evaluate_expression_with_reasons,
)
from app.scanner.schemas import (
    ScanRequest,
    ScanResult,
    StockSnapshot,
)


class ScannerEngine:
    """
    Scanner Engine.

    Evaluates scan requests against one or more
    StockSnapshot objects.
    """

    def scan(
        self,
        stocks: dict[str, StockSnapshot],
        request: ScanRequest,
    ) -> list[ScanResult]:

        results: list[ScanResult] = []

        for symbol, snapshot in stocks.items():

            matched, reasons = evaluate_expression_with_reasons(
                snapshot,
                request.expression,
            )

            if matched:

                results.append(
                    ScanResult(
                        symbol=symbol,
                        reasons=reasons,
                    )
                )

        return results

    def matches(
        self,
        snapshot: StockSnapshot,
        request: ScanRequest,
    ) -> bool:
        """
        Evaluate a single stock snapshot.

        Returns True if the stock satisfies
        the scan's expression tree.
        """

        return evaluate_expression(
            snapshot,
            request.expression,
        )