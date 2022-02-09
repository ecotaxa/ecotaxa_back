"""empty message

Revision ID: 4cb636df602
Revises: 519060922e3
Create Date: 2015-09-24 17:09:38.893038

"""

# revision identifiers, used by Alembic.
revision = '4cb636df602'
down_revision = '519060922e3'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('acquisitions', sa.Column('instrument', sa.VARCHAR(length=255), nullable=True))
    op.add_column('projects', sa.Column('objcount', postgresql.DOUBLE_PRECISION(), nullable=True))
    op.add_column('projects', sa.Column('pctclassified', postgresql.DOUBLE_PRECISION(), nullable=True))
    op.add_column('taxonomy', sa.Column('nbrobj', sa.INTEGER(), nullable=True))
    op.add_column('taxonomy', sa.Column('nbrobjcum', sa.INTEGER(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('taxonomy', 'nbrobjcum')
    op.drop_column('taxonomy', 'nbrobj')
    op.drop_column('projects', 'pctclassified')
    op.drop_column('projects', 'objcount')
    op.drop_column('acquisitions', 'instrument')
    ### end Alembic commands ###