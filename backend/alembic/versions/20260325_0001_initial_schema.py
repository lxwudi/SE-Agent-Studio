"""initial schema

Revision ID: 20260325_0001
Revises: 
Create Date: 2026-03-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_code", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("default_model", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("allow_delegation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("meta_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_code"),
    )
    op.create_index("ix_agent_profiles_agent_code", "agent_profiles", ["agent_code"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("uid"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_uid", "users", ["uid"], unique=True)

    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_code"),
    )
    op.create_index("ix_workflow_templates_workflow_code", "workflow_templates", ["workflow_code"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("requirement_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="DRAFT"),
        sa.Column("meta_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.UniqueConstraint("uid"),
    )
    op.create_index("ix_projects_uid", "projects", ["uid"], unique=True)

    op.create_table(
        "prompt_template_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_profile_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("backstory_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("rules_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_profile_id"], ["agent_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_profile_id", "version", name="uq_prompt_template_version"),
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_template_id", sa.Integer(), nullable=False),
        sa.Column("step_code", sa.String(length=120), nullable=False),
        sa.Column("step_type", sa.String(length=120), nullable=False),
        sa.Column("agent_code", sa.String(length=120), nullable=True),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column("parallel_group", sa.String(length=120), nullable=True),
        sa.Column("output_schema", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["workflow_template_id"], ["workflow_templates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow_template_id", "step_code", name="uq_workflow_step_code"),
    )
    op.create_index("ix_workflow_steps_step_code", "workflow_steps", ["step_code"], unique=False)

    op.create_table(
        "flow_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_uid", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("workflow_template_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="CREATED"),
        sa.Column("current_stage", sa.String(length=120), nullable=False, server_default="created"),
        sa.Column("input_requirement", sa.Text(), nullable=False, server_default=""),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_template_id"], ["workflow_templates.id"]),
        sa.UniqueConstraint("run_uid"),
    )
    op.create_index("ix_flow_runs_run_uid", "flow_runs", ["run_uid"], unique=True)
    op.create_index("ix_flow_runs_status", "flow_runs", ["status"], unique=False)

    op.create_table(
        "task_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_uid", sa.String(length=64), nullable=False),
        sa.Column("flow_run_id", sa.Integer(), nullable=False),
        sa.Column("step_code", sa.String(length=120), nullable=False),
        sa.Column("agent_code", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("crew_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_snapshot", sa.JSON(), nullable=False),
        sa.Column("token_usage_prompt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_usage_completion", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flow_run_id"], ["flow_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("task_uid"),
    )
    op.create_index("ix_task_runs_flow_run_id", "task_runs", ["flow_run_id"], unique=False)
    op.create_index("ix_task_runs_step_code", "task_runs", ["step_code"], unique=False)
    op.create_index("ix_task_runs_status", "task_runs", ["status"], unique=False)
    op.create_index("ix_task_runs_task_uid", "task_runs", ["task_uid"], unique=True)

    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("flow_run_id", sa.Integer(), nullable=False),
        sa.Column("task_run_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("event_source", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flow_run_id"], ["flow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.id"]),
    )
    op.create_index("ix_run_events_event_type", "run_events", ["event_type"], unique=False)
    op.create_index("ix_run_events_flow_run_id", "run_events", ["flow_run_id"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("artifact_uid", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("flow_run_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("source_task_run_id", sa.Integer(), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flow_run_id"], ["flow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_task_run_id"], ["task_runs.id"]),
        sa.UniqueConstraint("artifact_uid"),
    )
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_artifacts_artifact_uid", "artifacts", ["artifact_uid"], unique=True)
    op.create_index("ix_artifacts_flow_run_id", "artifacts", ["flow_run_id"], unique=False)
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_index("ix_artifacts_flow_run_id", table_name="artifacts")
    op.drop_index("ix_artifacts_artifact_uid", table_name="artifacts")
    op.drop_index("ix_artifacts_artifact_type", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_run_events_flow_run_id", table_name="run_events")
    op.drop_index("ix_run_events_event_type", table_name="run_events")
    op.drop_table("run_events")

    op.drop_index("ix_task_runs_task_uid", table_name="task_runs")
    op.drop_index("ix_task_runs_status", table_name="task_runs")
    op.drop_index("ix_task_runs_step_code", table_name="task_runs")
    op.drop_index("ix_task_runs_flow_run_id", table_name="task_runs")
    op.drop_table("task_runs")

    op.drop_index("ix_flow_runs_status", table_name="flow_runs")
    op.drop_index("ix_flow_runs_run_uid", table_name="flow_runs")
    op.drop_table("flow_runs")

    op.drop_index("ix_workflow_steps_step_code", table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_table("prompt_template_versions")

    op.drop_index("ix_projects_uid", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_workflow_templates_workflow_code", table_name="workflow_templates")
    op.drop_table("workflow_templates")

    op.drop_index("ix_users_uid", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_agent_profiles_agent_code", table_name="agent_profiles")
    op.drop_table("agent_profiles")
