"""add record name

Revision ID: 20260526_000002
Revises: 20260519_000001
Create Date: 2026-05-26 20:30:00
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260526_000002"
down_revision: Union[str, None] = "20260519_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recorded_request", sa.Column("name", sa.String(length=255), nullable=True))

    recorded_request = sa.table(
        "recorded_request",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=255)),
    )
    op.execute(
        recorded_request.update()
        .where(sa.or_(recorded_request.c.name.is_(None), recorded_request.c.name == ""))
        .values(name=sa.cast(recorded_request.c.id, sa.String(length=255)))
    )


def downgrade() -> None:
    op.drop_column("recorded_request", "name")
