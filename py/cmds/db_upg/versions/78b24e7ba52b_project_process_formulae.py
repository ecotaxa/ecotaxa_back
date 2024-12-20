"""project process formulae

Revision ID: 78b24e7ba52b
Revises: 032dfb7159d5
Create Date: 2024-12-05 10:05:36.987004

"""

# revision identifiers, used by Alembic.
revision = "78b24e7ba52b"
down_revision = "032dfb7159d5"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # PUBLIC ="1" when visible=True and no license
    op.add_column(
        "projects",
        sa.Column("access", sa.VARCHAR(length=1), nullable=False, server_default="0"),
    )
    op.execute("UPDATE projects set access = '1' WHERE visible=true AND license=''")
    # OPEN="2" when visible=True and license = CC
    op.execute(
        "UPDATE projects set access = '2' WHERE visible=true AND license!='' AND license!='copyright'"
    )
    # private when copyright or visible=False
    op.execute(
        "UPDATE projects set access = '0' WHERE visible=false OR license='copyright'"
    )
    op.add_column("projects", sa.Column("formulae", sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("projects", "formulae")
    op.drop_column("projects", "access")
    # ### end Alembic commands ###