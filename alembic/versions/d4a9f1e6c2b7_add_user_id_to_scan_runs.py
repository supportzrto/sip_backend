"""add user_id to scan_runs

Revision ID: d4a9f1e6c2b7
Revises: b2e7a1f4c9d3
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4a9f1e6c2b7'
down_revision: Union[str, Sequence[str], None] = 'b2e7a1f4c9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable: existing rows (scans run before ownership was
    # tracked) have no user to attribute them to. ON DELETE SET NULL
    # so a deleted user's scan history is preserved (not cascaded
    # away) rather than orphaning/blocking the delete.
    op.add_column(
        'scan_runs',
        sa.Column('user_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        'ix_scan_runs_user_id', 'scan_runs', ['user_id'], unique=False,
    )
    op.create_foreign_key(
        'fk_scan_runs_user_id_users',
        'scan_runs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_scan_runs_user_id_users', 'scan_runs', type_='foreignkey',
    )
    op.drop_index('ix_scan_runs_user_id', table_name='scan_runs')
    op.drop_column('scan_runs', 'user_id')