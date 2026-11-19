"""Answer status (complete/stopped/failed) and an index for reading chat history.

Revision ID: fffb848d8cd5
Revises: a7ca3754f2f4
Create Date: 2026-11-19 15:26:37.364709

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fffb848d8cd5"
down_revision: str | Sequence[str] | None = "a7ca3754f2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column("status", sa.String(length=20), server_default="complete", nullable=False),
    )
    op.drop_index(op.f("ix_questions_workspace_id"), table_name="questions")
    op.create_index(
        "ix_questions_workspace_created", "questions", ["workspace_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_questions_workspace_created", table_name="questions")
    op.create_index(op.f("ix_questions_workspace_id"), "questions", ["workspace_id"], unique=False)
    op.drop_column("answers", "status")
