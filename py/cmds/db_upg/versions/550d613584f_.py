"""empty message

Revision ID: 550d613584f
Revises: a9f4e64ac4
Create Date: 2015-08-04 10:39:05.875000

"""

# revision identifiers, used by Alembic.
revision = "550d613584f"
down_revision = "a9f4e64ac4"

import sqlalchemy as sa
from alembic import op


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "samples",
        sa.Column("dataportal_descriptor", sa.VARCHAR(length=8000), nullable=True),
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("samples", "dataportal_descriptor")
    ### end Alembic commands ###
