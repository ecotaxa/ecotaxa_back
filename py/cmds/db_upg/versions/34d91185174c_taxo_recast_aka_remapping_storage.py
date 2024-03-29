"""Taxo recast AKA remapping storage

Revision ID: 34d91185174c
Revises: 521c25353fa0
Create Date: 2023-05-21 10:58:56.188510

"""

# revision identifiers, used by Alembic.
revision = "34d91185174c"
down_revision = "521c25353fa0"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "taxo_recast",
        sa.Column("recast_id", sa.INTEGER(), sa.Identity(always=True), nullable=False),
        sa.Column("collection_id", sa.INTEGER(), nullable=True),
        sa.Column("project_id", sa.INTEGER(), nullable=True),
        sa.Column("operation", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "transforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "documentation", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collection.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.projid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("recast_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("taxo_recast")
    # ### end Alembic commands ###
