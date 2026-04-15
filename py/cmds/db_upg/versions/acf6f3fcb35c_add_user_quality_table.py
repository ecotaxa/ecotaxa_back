"""add user_quality table
Revision ID: acf6f3fcb35c
Revises: 9bf6b31796a2
Create Date: 2026-04-15 09:42:38.587711
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "acf6f3fcb35c"
down_revision = "9bf6b31796a2"


def upgrade():
    op.create_table(
        "user_quality",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("password_strong", sa.Boolean(), nullable=False),
        sa.Column(
            "check_date", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="user_quality_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("user_quality")
