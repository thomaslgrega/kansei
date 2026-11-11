"""Archive tracked postings and record when they moved

Revision ID: 6562eda23d5b
Revises: ee506d3446fc
Create Date: 2026-11-11 21:04:00.513787

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6562eda23d5b'
down_revision: str | Sequence[str] | None = 'ee506d3446fc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tracked', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tracked', sa.Column('moved_at', sa.DateTime(timezone=True), nullable=True))
    # A rejection implies an application; see ADR 0002.
    op.execute(
        "UPDATE tracked SET stage = 'applied', archived_at = created_at WHERE stage = 'rejected'"
    )
    op.execute('UPDATE tracked SET moved_at = created_at')
    op.alter_column('tracked', 'moved_at', nullable=False)
    # Autogenerate misses a changed CHECK constraint.
    op.drop_constraint(op.f('ck_tracked_stage'), 'tracked', type_='check')
    op.create_check_constraint(
        op.f('ck_tracked_stage'), 'tracked', "stage IN ('saved', 'applied', 'interviewing', 'offer')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('ck_tracked_stage'), 'tracked', type_='check')
    op.create_check_constraint(
        op.f('ck_tracked_stage'), 'tracked',
        "stage IN ('saved', 'applied', 'interviewing', 'offer', 'rejected')",
    )
    # Archived rows lose their stage, since rejected was the only way out.
    op.execute("UPDATE tracked SET stage = 'rejected' WHERE archived_at IS NOT NULL")
    op.drop_column('tracked', 'moved_at')
    op.drop_column('tracked', 'archived_at')
