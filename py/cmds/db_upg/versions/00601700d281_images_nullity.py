"""images nullity

Revision ID: 00601700d281
Revises: dae002b5d15a
Create Date: 2021-06-10 07:06:21.424432

"""

# revision identifiers, used by Alembic.
revision = "00601700d281"
down_revision = "dae002b5d15a"

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "images", "file_name", existing_type=sa.VARCHAR(length=255), nullable=False
    )
    op.alter_column("images", "height", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("images", "imgrank", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column(
        "images", "orig_file_name", existing_type=sa.VARCHAR(length=255), nullable=False
    )
    op.alter_column("images", "width", existing_type=sa.INTEGER(), nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("images", "width", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "images", "orig_file_name", existing_type=sa.VARCHAR(length=255), nullable=True
    )
    op.alter_column("images", "imgrank", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column("images", "height", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "images", "file_name", existing_type=sa.VARCHAR(length=255), nullable=True
    )
    # ### end Alembic commands ###
