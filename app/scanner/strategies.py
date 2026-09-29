from abc import ABC, abstractmethod

from decimal import Decimal

from app.scanner.enums import (
    ComparisonOperator,
    IndicatorField,
    LogicalOperator,
)
from app.scanner.schemas import (
    ScanCondition,
    ScanExpression,
    ScanRequest,
)


class ScanStrategy(ABC):
    """
    Base class for all scan strategies.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def build_request(self) -> ScanRequest:
        ...
    
class SwingStrategy(ScanStrategy):

    @property
    def name(self) -> str:
        return "Swing Strategy"

    def build_request(self) -> ScanRequest:

        return ScanRequest(

            strategy_name=self.name,

            expression=ScanExpression(

                operator=LogicalOperator.AND,

                children=[

                    ScanCondition(
                        left=IndicatorField.EMA20,
                        operator=ComparisonOperator.GREATER_THAN,
                        right=IndicatorField.EMA50,
                    ),

                    ScanCondition(
                        left=IndicatorField.RSI14,
                        operator=ComparisonOperator.LESS_THAN,
                        right=Decimal("35"),
                    ),

                    ScanCondition(
                        left=IndicatorField.ADX14,
                        operator=ComparisonOperator.GREATER_THAN,
                        right=Decimal("25"),
                    ),
                ],
            )
        )


class BreakoutStrategy(ScanStrategy):
    """
    A stock breaking out to a new 252-day (52-week) high, confirmed
    by a volume surge -- the price move is backed by unusually high
    trading activity rather than being a low-conviction move.
    """

    def __init__(
        self,
        volume_surge_threshold: Decimal = Decimal("1.5"),
    ):
        self.volume_surge_threshold = volume_surge_threshold

    @property
    def name(self) -> str:
        return "Breakout Strategy"

    def build_request(self) -> ScanRequest:

        return ScanRequest(

            strategy_name=self.name,

            expression=ScanExpression(

                operator=LogicalOperator.AND,

                children=[

                    # Close crosses above the highest high of the
                    # preceding 252 trading days -- a genuine new
                    # 52-week-high breakout, not just "currently
                    # above" (which would also match every day
                    # afterwards).
                    ScanCondition(
                        left=IndicatorField.CLOSE,
                        operator=ComparisonOperator.CROSSES_ABOVE,
                        right=IndicatorField.HIGHEST252,
                    ),

                    # Confirmation: today's volume is meaningfully
                    # above its recent average.
                    ScanCondition(
                        left=IndicatorField.VOLUME_SURGE20,
                        operator=ComparisonOperator.GREATER_THAN,
                        right=self.volume_surge_threshold,
                    ),
                ],
            )
        )


class BreakdownStrategy(ScanStrategy):
    """
    The mirror of BreakoutStrategy: a stock breaking down to a new
    252-day (52-week) low, confirmed by a volume surge.
    """

    def __init__(
        self,
        volume_surge_threshold: Decimal = Decimal("1.5"),
    ):
        self.volume_surge_threshold = volume_surge_threshold

    @property
    def name(self) -> str:
        return "Breakdown Strategy"

    def build_request(self) -> ScanRequest:

        return ScanRequest(

            strategy_name=self.name,

            expression=ScanExpression(

                operator=LogicalOperator.AND,

                children=[

                    ScanCondition(
                        left=IndicatorField.CLOSE,
                        operator=ComparisonOperator.CROSSES_BELOW,
                        right=IndicatorField.LOWEST252,
                    ),

                    ScanCondition(
                        left=IndicatorField.VOLUME_SURGE20,
                        operator=ComparisonOperator.GREATER_THAN,
                        right=self.volume_surge_threshold,
                    ),
                ],
            )
        )


# Named, ready-to-run strategies. Keyed by a URL-friendly slug. This
# is the single source of truth for valid strategy keys -- both
# app/api/scanner.py (manual "run this now" scans) and the alert
# system (app/services/alert_service.py, which validates a rule's
# strategy_key against this same dict) key off of it, so a strategy
# added here is automatically available in both places.
AVAILABLE_STRATEGIES: dict[str, ScanStrategy] = {
    "breakout": BreakoutStrategy(),
    "breakdown": BreakdownStrategy(),
    "swing": SwingStrategy(),
}