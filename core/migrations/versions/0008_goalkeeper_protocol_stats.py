"""goalkeeper protocol stats

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-21 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("match_appearance", sa.Column("position", sa.String(length=2), nullable=True))
    op.add_column(
        "player_tournament_stats",
        sa.Column("goalkeeper_played", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_tournament_stats",
        sa.Column("goalkeeper_conceded", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("player_tournament_stats", "goalkeeper_conceded")
    op.drop_column("player_tournament_stats", "goalkeeper_played")
    op.drop_column("match_appearance", "position")
