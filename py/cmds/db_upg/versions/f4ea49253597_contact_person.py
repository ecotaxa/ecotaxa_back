"""Contact person

Revision ID: f4ea49253597
Revises: c30b923293e9
Create Date: 2021-01-20 17:33:44.068116

"""

# revision identifiers, used by Alembic.
revision = "f4ea49253597"
down_revision = "c30b923293e9"

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "projectspriv", sa.Column("extra", sa.VARCHAR(length=1), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("projectspriv", "extra")
    # ### end Alembic commands ###
