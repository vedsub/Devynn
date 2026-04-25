"""initial_schema

Revision ID: 4e4eb272343d
Revises: 
Create Date: 2026-04-25 11:08:40.468491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e4eb272343d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema: users, interview_sessions, turns."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("interview_sessions.id"), nullable=False, index=True),
        sa.Column("sequence_num", sa.Integer(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("audio_s3_key", sa.String(), nullable=True),
        sa.Column("pace_label", sa.String(), nullable=False),
        sa.Column("wps", sa.Float(), nullable=False),
        sa.Column("ai_response", sa.Text(), nullable=False),
        sa.Column("grammar_notes", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("turns")
    op.drop_table("interview_sessions")
    op.drop_table("users")
