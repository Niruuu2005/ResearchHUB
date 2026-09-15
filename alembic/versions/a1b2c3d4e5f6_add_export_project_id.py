"""add export_reports.project_id

Revision ID: a1b2c3d4e5f6
Revises: 08c76f335519
Create Date: 2026-09-15 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "08c76f335519"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("export_reports") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_export_reports_project_id", ["project_id"])
        batch_op.create_foreign_key(
            "fk_export_reports_project_id",
            "research_projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("export_reports") as batch_op:
        batch_op.drop_constraint("fk_export_reports_project_id", type_="foreignkey")
        batch_op.drop_index("ix_export_reports_project_id")
        batch_op.drop_column("project_id")
