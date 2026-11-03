"""Exceptions: the run they belong to, the quantity found, and where the task was rerouted.

from_location_id is NOT NULL with no default. That is safe because nothing has written to
exceptions before this migration, so the table is empty.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exceptions", sa.Column("run_id", sa.Integer(), nullable=True))
    op.add_column("exceptions", sa.Column("qty_found", sa.Integer(), nullable=True))
    op.add_column("exceptions", sa.Column("from_location_id", sa.Integer(), nullable=False))
    op.add_column("exceptions", sa.Column("rerouted_to_location_id", sa.Integer(), nullable=True))
    op.create_foreign_key("exceptions_run_id_foreign", "exceptions", "sim_runs", ["run_id"], ["id"])
    op.create_foreign_key(
        "exceptions_from_location_id_foreign", "exceptions", "locations", ["from_location_id"], ["id"]
    )
    op.create_foreign_key(
        "exceptions_rerouted_to_location_id_foreign", "exceptions", "locations", ["rerouted_to_location_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("exceptions_rerouted_to_location_id_foreign", "exceptions", type_="foreignkey")
    op.drop_constraint("exceptions_from_location_id_foreign", "exceptions", type_="foreignkey")
    op.drop_constraint("exceptions_run_id_foreign", "exceptions", type_="foreignkey")
    # MySQL keeps the indexes it created for the foreign keys; dropping each column removes its index.
    op.drop_column("exceptions", "rerouted_to_location_id")
    op.drop_column("exceptions", "from_location_id")
    op.drop_column("exceptions", "qty_found")
    op.drop_column("exceptions", "run_id")
