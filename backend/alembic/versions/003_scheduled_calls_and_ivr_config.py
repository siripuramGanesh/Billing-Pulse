"""scheduled_calls table and ivr_config on payers

Revision ID: 003
Revises: 002
Create Date: 2025-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payers", sa.Column("ivr_config", sa.JSON(), nullable=True))
    op.create_table(
        "scheduled_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("call_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_calls_call_after"), "scheduled_calls", ["call_after"], unique=False)
    op.create_index(op.f("ix_scheduled_calls_claim_id"), "scheduled_calls", ["claim_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_calls_claim_id"), table_name="scheduled_calls")
    op.drop_index(op.f("ix_scheduled_calls_call_after"), table_name="scheduled_calls")
    op.drop_table("scheduled_calls")
    op.drop_column("payers", "ivr_config")
