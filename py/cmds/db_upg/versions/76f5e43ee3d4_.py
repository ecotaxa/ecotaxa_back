"""empty message

Revision ID: 76f5e43ee3d4
Revises: b6e0931a2de5
Create Date: 2019-09-04 11:14:34.336228

"""

# revision identifiers, used by Alembic.
revision = '76f5e43ee3d4'
down_revision = 'b6e0931a2de5'

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column('part_projects', sa.Column('remote_type', sa.VARCHAR(length=20), nullable=True))
    op.add_column('part_projects', sa.Column('remote_directory', sa.VARCHAR(length=200), nullable=True))
    op.add_column('part_projects', sa.Column('remote_password', sa.VARCHAR(length=100), nullable=True))
    op.add_column('part_projects', sa.Column('remote_url', sa.VARCHAR(length=200), nullable=True))
    op.add_column('part_projects', sa.Column('remote_user', sa.VARCHAR(length=100), nullable=True))
    op.add_column('part_projects', sa.Column('remote_vectorref', sa.VARCHAR(length=200), nullable=True))


def downgrade():
    op.drop_column('part_projects', 'remote_vectorref')
    op.drop_column('part_projects', 'remote_user')
    op.drop_column('part_projects', 'remote_url')
    op.drop_column('part_projects', 'remote_password')
    op.drop_column('part_projects', 'remote_directory')
    op.drop_column('part_projects', 'remote_type')
