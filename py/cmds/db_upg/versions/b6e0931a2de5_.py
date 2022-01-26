"""empty message

Revision ID: b6e0931a2de5
Revises: 06ae8724ba37
Create Date: 2019-08-14 15:09:53.498680

"""

# revision identifiers, used by Alembic.
revision = 'b6e0931a2de5'
down_revision = '06ae8724ba37'

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column('part_samples', sa.Column('integrationtime', sa.INTEGER(), nullable=True))


def downgrade():
    op.drop_column('part_samples', 'integrationtime')
