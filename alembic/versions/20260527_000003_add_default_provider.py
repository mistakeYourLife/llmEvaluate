"""add default provider

Revision ID: 20260527_000003
Revises: 20260526_000002
Create Date: 2026-05-27 15:20:00
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260527_000003"
down_revision: Union[str, None] = "20260526_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("provider", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))

    provider = sa.table(
        "provider",
        sa.column("id", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("is_default", sa.Boolean()),
    )

    bind = op.get_bind()
    default_provider_id = bind.execute(
        sa.select(provider.c.id).where(provider.c.enabled.is_(True)).order_by(provider.c.id.asc()).limit(1)
    ).scalar_one_or_none()

    if default_provider_id is not None:
        op.execute(provider.update().values(is_default=False))
        op.execute(provider.update().where(provider.c.id == default_provider_id).values(is_default=True))


def downgrade() -> None:
    op.drop_column("provider", "is_default")
