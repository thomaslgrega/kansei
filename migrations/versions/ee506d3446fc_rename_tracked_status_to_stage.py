"""Rename tracked status to stage

Revision ID: ee506d3446fc
Revises: c54f150dbb59
Create Date: 2026-11-11 19:02:19.858941

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ee506d3446fc'
down_revision: str | Sequence[str] | None = 'c54f150dbb59'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('tracked', 'status', new_column_name='stage')
    op.execute('ALTER TABLE tracked RENAME CONSTRAINT ck_tracked_status TO ck_tracked_stage')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE tracked RENAME CONSTRAINT ck_tracked_stage TO ck_tracked_status')
    op.alter_column('tracked', 'stage', new_column_name='status')
