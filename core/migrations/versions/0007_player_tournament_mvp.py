"""player tournament MVP count

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-17 10:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "player_tournament_stats",
        sa.Column("mvp", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("player_tournament_stats", "mvp")
