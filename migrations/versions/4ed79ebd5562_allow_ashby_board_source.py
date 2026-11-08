"""Allow ashby board source

Revision ID: 4ed79ebd5562
Revises: abebe3ca9b15
Create Date: 2026-11-08 01:24:25.686331

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4ed79ebd5562'
down_revision: str | Sequence[str] | None = 'abebe3ca9b15'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate misses a changed CHECK constraint.
    op.drop_constraint(op.f('ck_boards_source'), 'boards', type_='check')
    op.create_check_constraint(
        op.f('ck_boards_source'), 'boards', "source IN ('greenhouse', 'lever', 'ashby')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails while any ashby board remains; delete those boards first.
    op.drop_constraint(op.f('ck_boards_source'), 'boards', type_='check')
    op.create_check_constraint(
        op.f('ck_boards_source'), 'boards', "source IN ('greenhouse', 'lever')"
    )
