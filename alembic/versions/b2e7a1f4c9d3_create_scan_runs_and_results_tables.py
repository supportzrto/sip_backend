"""create scan runs and results tables

Revision ID: b2e7a1f4c9d3
Revises: a1556d734f79
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2e7a1f4c9d3'
down_revision: Union[str, Sequence[str], None] = 'a1556d734f79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'scan_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('stocks_scanned', sa.Integer(), nullable=False),
        sa.Column('matches_found', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'scan_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scan_run_id', sa.Integer(), nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['scan_run_id'], ['scan_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scan_results_scan_run_id', 'scan_results', ['scan_run_id'], unique=False)
    op.create_index('ix_scan_results_instrument_id', 'scan_results', ['instrument_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_scan_results_instrument_id', table_name='scan_results')
    op.drop_index('ix_scan_results_scan_run_id', table_name='scan_results')
    op.drop_table('scan_results')
    op.drop_table('scan_runs')