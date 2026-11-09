"""Allow hrmos board source and add headline to postings

Revision ID: 567ed3c5bd17
Revises: 6ea5bdd25bf9
Create Date: 2026-11-09 17:20:25.645456

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '567ed3c5bd17'
down_revision: str | Sequence[str] | None = '6ea5bdd25bf9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('postings', sa.Column('headline', sa.String(), nullable=True))
    # Autogenerate misses a changed CHECK constraint.
    op.drop_constraint(op.f('ck_boards_source'), 'boards', type_='check')
    op.create_check_constraint(
        op.f('ck_boards_source'), 'boards', "source IN ('greenhouse', 'lever', 'ashby', 'hrmos')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails while any hrmos board remains; delete those boards first.
    op.drop_constraint(op.f('ck_boards_source'), 'boards', type_='check')
    op.create_check_constraint(
        op.f('ck_boards_source'), 'boards', "source IN ('greenhouse', 'lever', 'ashby')"
    )
    op.drop_column('postings', 'headline')
