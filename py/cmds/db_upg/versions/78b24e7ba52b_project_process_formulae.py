"""project process formulae

Revision ID: 78b24e7ba52b
Revises: f38a881a1f6c
Create Date: 2024-12-05 10:05:36.987004

"""

# revision identifiers, used by Alembic.
revision = "78b24e7ba52b"
down_revision = "f38a881a1f6c"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # PUBLIC ="1" when visible=True and no license
    op.add_column(
        "projects",
        sa.Column("access", sa.VARCHAR(length=1), nullable=True, server_default="0"),
    )
    op.execute("UPDATE projects set access='1' WHERE visible=true AND (license='' OR license IS NULL)")
    # OPEN="2" when visible=True and license = CC
    op.execute(
        "UPDATE projects set access='2' WHERE visible=true AND license!='' AND LOWER(license) NOT LIKE 'copyright'"
    )
    # private when copyright or visible=False
    op.execute(
        "UPDATE projects set access='0' WHERE visible=false OR LOWER(license) LIKE 'copyright'"
    )
    op.execute("ALTER TABLE projects ALTER COLUMN access SET NOT NULL")
    op.add_column("projects", sa.Column("formulae", sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("projects", "formulae")
    op.drop_column("projects", "access")
    # ### end Alembic commands ###
