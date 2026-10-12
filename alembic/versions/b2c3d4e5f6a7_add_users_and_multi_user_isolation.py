"""add users and multi-user data isolation

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("profile_picture", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    # 2. Add nullable user_id to existing private tables
    tables = [
        "papers",
        "research_projects",
        "paper_documents",
        "chat_sessions",
        "research_notes",
        "export_reports",
        "research_sessions",
        "background_jobs",
    ]
    for table_name in tables:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            batch_op.create_index(f"ix_{table_name}_user_id", ["user_id"])
            batch_op.create_foreign_key(
                f"fk_{table_name}_user_id",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    tables = [
        "background_jobs",
        "research_sessions",
        "export_reports",
        "research_notes",
        "chat_sessions",
        "paper_documents",
        "research_projects",
        "papers",
    ]
    for table_name in tables:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(f"fk_{table_name}_user_id", type_="foreignkey")
            batch_op.drop_index(f"ix_{table_name}_user_id")
            batch_op.drop_column("user_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
