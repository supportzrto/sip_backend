from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.auth.repository import UserRepository
from app.core.email import EmailDeliveryError, send_alert_email
from app.models.alert_notification import AlertNotification
from app.models.alert_rule import AlertRule
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)
from app.repositories.watchlist_repository import WatchlistRepository
from app.scanner.schemas import ScanExpression, ScanRequest, ScanResult
from app.scanner.strategies import AVAILABLE_STRATEGIES
from app.services.scanner_service import ScannerService

logger = logging.getLogger(__name__)


class AlertService:
    """
    Runs alert rules: scans for matches (optionally scoped to a
    watchlist), works out which matches are genuinely *new* since
    the rule's last run, records + emails those, and updates the
    rule's state for next time.

    "New" means: matched this run but did NOT match the immediately
    preceding run. A symbol that keeps matching day after day (e.g.
    RSI staying oversold) only notifies once, on the day it starts
    matching -- not every single day it continues to.
    """

    def __init__(
        self,
        scanner_service: ScannerService,
        alert_rule_repository: AlertRuleRepository,
        watchlist_repository: WatchlistRepository,
        instrument_repository: InstrumentRepository,
        saved_strategy_repository: SavedStrategyRepository,
        user_repository: UserRepository,
    ) -> None:

        self._scanner_service = scanner_service
        self._alert_rule_repository = alert_rule_repository
        self._watchlist_repository = watchlist_repository
        self._instrument_repository = instrument_repository
        self._saved_strategy_repository = saved_strategy_repository
        self._user_repository = user_repository

    def run_rule(self, alert_rule: AlertRule) -> list[ScanResult]:
        """
        Evaluate one alert rule end to end and commit its updated
        state. Returns the newly matched results (empty if nothing
        new fired this run).
        """

        scan_request = self._build_scan_request(alert_rule)

        if scan_request is None:
            return []

        symbols: list[str] | None = None

        if alert_rule.watchlist_id is not None:

            symbols = self._watchlist_repository.get_symbols(
                alert_rule.watchlist_id,
            )

            if not symbols:
                # An empty (or since-emptied) watchlist has nothing
                # to scan -- not an error, just nothing to do this
                # run. Still record that we checked.
                self._touch_rule(alert_rule, matched_symbols=[])
                self._alert_rule_repository.commit()
                return []

        results = self._scanner_service.scan(
            scan_request,
            user_id=alert_rule.user_id,
            symbols=symbols,
        )

        current_matches = {result.symbol: result for result in results}
        previously_matched = set(alert_rule.last_matched_symbols or [])

        newly_matched = [
            result
            for symbol, result in current_matches.items()
            if symbol not in previously_matched
        ]

        if newly_matched:
            self._notify(alert_rule, newly_matched)

        self._touch_rule(
            alert_rule,
            matched_symbols=list(current_matches.keys()),
        )

        self._alert_rule_repository.commit()

        return newly_matched

    def _build_scan_request(
        self,
        alert_rule: AlertRule,
    ) -> ScanRequest | None:
        """
        Resolves the rule's strategy source -- a built-in
        strategy_key or a saved_strategy_id -- into a ScanRequest.
        Returns None (logging why) if the source can no longer be
        resolved, e.g. an unknown/removed strategy_key.
        """

        if alert_rule.strategy_key is not None:

            strategy = AVAILABLE_STRATEGIES.get(alert_rule.strategy_key)

            if strategy is None:
                # Not expected in practice -- strategy_key is
                # validated against this same dict when a rule is
                # created/updated -- but a strategy could
                # theoretically be removed later.
                logger.error(
                    "Alert rule %s has an unknown strategy_key "
                    "'%s' -- skipping.",
                    alert_rule.id,
                    alert_rule.strategy_key,
                )
                return None

            return strategy.build_request()

        # Otherwise saved_strategy_id is set -- enforced by the
        # AlertRule.__table_args__ CHECK constraint, so this is the
        # only other case.
        saved_strategy = self._saved_strategy_repository.get_by_id(
            alert_rule.saved_strategy_id,
        )

        if saved_strategy is None:
            # Shouldn't happen -- saved_strategy_id is an
            # ON DELETE CASCADE FK, so the rule is deleted along with
            # its saved strategy -- but a dangling reference
            # shouldn't crash the whole run.
            logger.error(
                "Alert rule %s references a missing saved strategy "
                "%s -- skipping.",
                alert_rule.id,
                alert_rule.saved_strategy_id,
            )
            return None

        return ScanRequest(
            strategy_name=saved_strategy.name,
            expression=ScanExpression.model_validate(
                saved_strategy.expression,
            ),
        )

    def run_all_active(self) -> None:
        """
        Entry point for the scheduler: evaluate every active alert
        rule. One rule failing (bad strategy key, an unexpected
        error, etc.) is logged and skipped rather than aborting the
        rest -- a single broken rule shouldn't stop everyone else's
        alerts from running.
        """

        for alert_rule in self._alert_rule_repository.list_active():

            try:
                self.run_rule(alert_rule)
            except Exception:
                logger.exception(
                    "Failed to run alert rule %s.",
                    alert_rule.id,
                )

    def _touch_rule(
        self,
        alert_rule: AlertRule,
        matched_symbols: list[str],
    ) -> None:

        alert_rule.last_matched_symbols = matched_symbols
        alert_rule.last_checked_at = datetime.now(timezone.utc)

        self._alert_rule_repository.db.flush()

    def _notify(
        self,
        alert_rule: AlertRule,
        newly_matched: list[ScanResult],
    ) -> None:

        user = self._user_repository.get_by_id(alert_rule.user_id)

        if user is None:
            # Shouldn't happen -- user_id is a not-null FK -- but a
            # dangling reference shouldn't crash the whole run.
            logger.error(
                "Alert rule %s references a missing user %s.",
                alert_rule.id,
                alert_rule.user_id,
            )
            return

        instrument_ids = {
            instrument.symbol: instrument.id
            for instrument in self._instrument_repository.get_all()
            if instrument.symbol in {r.symbol for r in newly_matched}
        }

        notifications = [
            AlertNotification(
                alert_rule_id=alert_rule.id,
                instrument_id=instrument_ids[result.symbol],
                symbol=result.symbol,
                reasons=result.reasons,
            )
            for result in newly_matched
            if result.symbol in instrument_ids
        ]

        self._alert_rule_repository.create_notifications(notifications)

        try:
            send_alert_email(
                to=user.email,
                full_name=user.full_name,
                alert_name=alert_rule.name,
                matches=[
                    (result.symbol, result.reasons)
                    for result in newly_matched
                ],
            )
        except EmailDeliveryError:
            # The match is already recorded either way -- a delivery
            # failure shouldn't lose the signal, just the
            # notification of it. send_email already logged this.
            pass