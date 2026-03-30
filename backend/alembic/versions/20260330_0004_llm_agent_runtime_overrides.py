"""add llm agent runtime overrides

Revision ID: 20260330_0004
Revises: 20260330_0003
Create Date: 2026-03-30 18:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_0004"
down_revision = "20260330_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_llm_configs",
        sa.Column(
            "agent_runtime_overrides",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_llm_configs", "agent_runtime_overrides")
