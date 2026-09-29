from sqlalchemy import select

from app.models.alert_notification import AlertNotification
from app.models.alert_rule import AlertRule
from app.repositories.base_repository import BaseRepository


class AlertRuleRepository(BaseRepository):

    def create(self, alert_rule: AlertRule) -> AlertRule:

        self.add(alert_rule)
        self.db.flush()

        return alert_rule

    def list_for_user(self, user_id: int) -> list[AlertRule]:

        statement = (
            select(AlertRule)
            .where(AlertRule.user_id == user_id)
            .order_by(AlertRule.name)
        )

        return list(self.db.scalars(statement).all())

    def get_by_id(
        self,
        alert_rule_id: int,
        user_id: int | None = None,
    ) -> AlertRule | None:
        """
        user_id=None returns the rule regardless of owner (for
        internal/scheduler use). Pass the requesting user's id to
        additionally require they own it -- a mismatch returns None,
        which callers should treat the same as "not found".
        """

        statement = select(AlertRule).where(AlertRule.id == alert_rule_id)

        if user_id is not None:
            statement = statement.where(AlertRule.user_id == user_id)

        return self.db.scalar(statement)

    def list_active(self) -> list[AlertRule]:
        """
        Every active alert rule, regardless of owner -- what the
        scheduler evaluates on each run.
        """

        statement = select(AlertRule).where(AlertRule.is_active.is_(True))

        return list(self.db.scalars(statement).all())

    def delete(self, alert_rule: AlertRule) -> None:

        self.db.delete(alert_rule)

    def create_notifications(
        self,
        notifications: list[AlertNotification],
    ) -> None:

        if notifications:
            self.add_many(notifications)
            self.db.flush()

    def list_recent_notifications_for_user(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[AlertNotification]:

        statement = (
            select(AlertNotification)
            .join(AlertRule)
            .where(AlertRule.user_id == user_id)
            .order_by(AlertNotification.notified_at.desc())
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())