"""add user llm config

Revision ID: 20260325_0002
Revises: 20260325_0001
Create Date: 2026-03-25 09:50:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_0002"
down_revision = "20260325_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_llm_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(length=120), nullable=False, server_default="OpenAI Compatible"),
        sa.Column("base_url", sa.String(length=255), nullable=False, server_default="https://api.openai.com/v1"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_model", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_llm_config_user_id"),
    )
    op.create_index("ix_user_llm_configs_user_id", "user_llm_configs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_llm_configs_user_id", table_name="user_llm_configs")
    op.drop_table("user_llm_configs")
