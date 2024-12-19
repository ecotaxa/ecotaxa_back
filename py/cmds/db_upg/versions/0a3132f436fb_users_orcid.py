"""users_orcid

Revision ID: 0a3132f436fb
Revises: 4e25988b1e56
Create Date: 2024-03-29 16:10:04.417410

"""

# revision identifiers, used by Alembic.
revision = "0a3132f436fb"
down_revision = "4e25988b1e56"

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users", sa.Column("orcid", sa.String(length=20), nullable=True, default="")
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "orcid")
    # ### end Alembic commands ###
