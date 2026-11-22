"""organizations_creator: who created an organization, to limit the unused ones

Revision ID: 5d2e8c41a7b3
Revises: 1f4c9b7e2a10
Create Date: 2026-11-02 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "5d2e8c41a7b3"
down_revision = "1f4c9b7e2a10"

from alembic import op

# Plain SQL, mirrored in QA/py/pg_files/upgrade_prod.sql
UPGRADE_SQL = """
ALTER TABLE organizations ADD COLUMN creator_email VARCHAR(255);
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute("ALTER TABLE organizations DROP COLUMN creator_email;")
