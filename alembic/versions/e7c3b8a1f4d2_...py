"""create watchlists, watchlist_items, alert_rules, alert_notifications

Revision ID: e7c3b8a1f4d2
Revises: d4a9f1e6c2b7
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e7c3b8a1f4d2'
down_revision: Union[str, Sequence[str], None] = 'd4a9f1e6c2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint(
            'user_id', 'name', name='uq_watchlist_user_name',
        ),
    )
    op.create_index(
        'ix_watchlists_user_id', 'watchlists', ['user_id'],
    )

    op.create_table(
        'watchlist_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'watchlist_id', sa.Integer(),
            sa.ForeignKey('watchlists.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'instrument_id', sa.Integer(),
            sa.ForeignKey('instruments.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'added_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint(
            'watchlist_id', 'instrument_id', name='uq_watchlist_item',
        ),
    )
    op.create_index(
        'ix_watchlist_items_watchlist_id',
        'watchlist_items', ['watchlist_id'],
    )
    op.create_index(
        'ix_watchlist_items_instrument_id',
        'watchlist_items', ['instrument_id'],
    )

    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('strategy_key', sa.String(length=50), nullable=False),
        sa.Column(
            'watchlist_id', sa.Integer(),
            sa.ForeignKey('watchlists.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'is_active', sa.Boolean(),
            server_default=sa.true(), nullable=False,
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'last_checked_at', sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            'last_matched_symbols', sa.JSON(),
            server_default='[]', nullable=False,
        ),
    )
    op.create_index(
        'ix_alert_rules_user_id', 'alert_rules', ['user_id'],
    )
    op.create_index(
        'ix_alert_rules_watchlist_id', 'alert_rules', ['watchlist_id'],
    )

    op.create_table(
        'alert_notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'alert_rule_id', sa.Integer(),
            sa.ForeignKey('alert_rules.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'instrument_id', sa.Integer(),
            sa.ForeignKey('instruments.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column(
            'reasons', sa.JSON(),
            server_default='[]', nullable=False,
        ),
        sa.Column(
            'notified_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        'ix_alert_notifications_alert_rule_id',
        'alert_notifications', ['alert_rule_id'],
    )
    op.create_index(
        'ix_alert_notifications_instrument_id',
        'alert_notifications', ['instrument_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('alert_notifications')
    op.drop_table('alert_rules')
    op.drop_table('watchlist_items')
    op.drop_table('watchlists')