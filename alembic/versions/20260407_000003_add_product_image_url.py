"""add product image url

Revision ID: 20260407_000003
Revises: 20260407_000002
Create Date: 2026-04-07 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260407_000003"
down_revision: Union[str, None] = "20260407_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
