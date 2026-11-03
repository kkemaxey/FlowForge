"""Workers: version (optimistic concurrency) and updated_at.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workers", sa.Column("version", sa.Integer(), server_default="0", nullable=False))
    # The server default gives existing rows a value; the app sets it on every write.
    op.add_column(
        "workers",
        sa.Column(
            "updated_at",
            sa.DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql"),
            server_default=sa.text("CURRENT_TIMESTAMP(3)"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("workers", "updated_at")
    op.drop_column("workers", "version")
