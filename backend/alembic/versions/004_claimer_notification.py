"""Add claimer notification: practice.notification_email, claim.claimer_notified_at

Revision ID: 004
Revises: 003
Create Date: 2025-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("practices", sa.Column("notification_email", sa.String(255), nullable=True))
    op.add_column("claims", sa.Column("claimer_notified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "claimer_notified_at")
    op.drop_column("practices", "notification_email")
