"""create saved_strategies, allow alert_rules to reference one

Revision ID: f1a4d9c2e6b8
Revises: e7c3b8a1f4d2
Create Date: 2026-09-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a4d9c2e6b8'
down_revision: Union[str, Sequence[str], None] = 'e7c3b8a1f4d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        'saved_strategies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('expression', sa.JSON(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint(
            'user_id', 'name', name='uq_saved_strategy_user_name',
        ),
    )
    op.create_index(
        'ix_saved_strategies_user_id', 'saved_strategies', ['user_id'],
    )

    # strategy_key was NOT NULL -- a rule now points at *either* a
    # built-in strategy_key or a saved_strategy_id, so it has to
    # become nullable. Existing rows already have a strategy_key
    # (that's all that existed before this migration), so no backfill
    # is needed -- they satisfy the new CHECK constraint as-is.
    with op.batch_alter_table('alert_rules') as batch_op:

        batch_op.alter_column(
            'strategy_key',
            existing_type=sa.String(length=50),
            nullable=True,
        )

        batch_op.add_column(
            sa.Column(
                'saved_strategy_id', sa.Integer(),
                sa.ForeignKey('saved_strategies.id', ondelete='CASCADE'),
                nullable=True,
            ),
        )

        batch_op.create_check_constraint(
            'ck_alert_rule_exactly_one_strategy_source',
            '(strategy_key IS NOT NULL) != (saved_strategy_id IS NOT NULL)',
        )

    op.create_index(
        'ix_alert_rules_saved_strategy_id',
        'alert_rules', ['saved_strategy_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('ix_alert_rules_saved_strategy_id', table_name='alert_rules')

    with op.batch_alter_table('alert_rules') as batch_op:

        batch_op.drop_constraint(
            'ck_alert_rule_exactly_one_strategy_source',
            type_='check',
        )
        batch_op.drop_column('saved_strategy_id')
        batch_op.alter_column(
            'strategy_key',
            existing_type=sa.String(length=50),
            nullable=False,
        )

    op.drop_table('saved_strategies')