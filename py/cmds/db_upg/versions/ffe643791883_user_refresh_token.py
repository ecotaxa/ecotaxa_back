"""user_refresh_token table, for rotating refresh tokens

Revision ID: ffe643791883
Revises: af45d71653e4
Create Date: 2026-10-05 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "ffe643791883"
down_revision = "af45d71653e4"

from alembic import op

# Plain SQL, mirrored in QA/py/pg_files/upgrade_prod.sql
UPGRADE_SQL = """
CREATE SEQUENCE seq_user_refresh_token;

CREATE TABLE user_refresh_token (
    id INTEGER NOT NULL DEFAULT nextval('seq_user_refresh_token'),
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    family_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITHOUT TIME ZONE,
    revoked_at TIMESTAMP WITHOUT TIME ZONE,
    replaced_by INTEGER,
    client_info VARCHAR(255),
    PRIMARY KEY (id),
    CONSTRAINT user_refresh_token_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT user_refresh_token_replaced_by_fkey FOREIGN KEY(replaced_by) REFERENCES user_refresh_token (id) ON DELETE SET NULL,
    CONSTRAINT user_refresh_token_token_hash_key UNIQUE (token_hash)
);

CREATE INDEX ix_user_refresh_token_user_id ON user_refresh_token (user_id);

CREATE INDEX ix_user_refresh_token_family_id ON user_refresh_token (family_id);
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute("DROP TABLE user_refresh_token; DROP SEQUENCE seq_user_refresh_token;")
