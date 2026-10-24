"""users_oidc: durable link between local accounts and OpenID identities

Revision ID: 1f4c9b7e2a10
Revises: ffe643791883
Create Date: 2026-10-22 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "1f4c9b7e2a10"
down_revision = "ffe643791883"

from alembic import op

# Plain SQL, mirrored in QA/py/pg_files/upgrade_prod.sql
UPGRADE_SQL = """
CREATE SEQUENCE seq_users_oidc;

CREATE TABLE users_oidc (
    id INTEGER NOT NULL DEFAULT nextval('seq_users_oidc'),
    user_id INTEGER NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    created_on TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    last_login TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT users_oidc_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_users_oidc_user_id ON users_oidc (user_id);

CREATE UNIQUE INDEX ix_users_oidc_issuer_subject ON users_oidc (issuer, subject);
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute("DROP TABLE users_oidc; DROP SEQUENCE seq_users_oidc;")
