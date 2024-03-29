"""users validation

Revision ID: 1b1beb672279
Revises: 34d91185174c
Create Date: 2023-09-08 16:29:27.440565

"""

# revision identifiers, used by Alembic.
revision = "1b1beb672279"
down_revision = "34d91185174c"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user_password_reset",
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("temp_password", sa.VARCHAR(), nullable=False),
        sa.Column(
            "creation_date",
            postgresql.TIMESTAMP(),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.add_column(
        "users",
        sa.Column("status_admin_comment", sa.VARCHAR(255), nullable=True),
    )
    op.add_column(
        "users", sa.Column("status_date", postgresql.TIMESTAMP(), nullable=True)
    )
    op.execute("""ALTER TABLE users ALTER active DROP DEFAULT;""")
    op.execute(
        """ALTER TABLE users ALTER active TYPE SMALLINT
        USING
        CASE
        WHEN active=false THEN 0 ELSE 1
        END;"""
    )
    op.execute("""ALTER TABLE users ALTER active SET DEFAULT 1;""")
    op.execute("""ALTER TABLE users RENAME COLUMN active TO status ;""")
    # alter mail_status from char  to bool
    op.execute("""ALTER TABLE users ALTER mail_status DROP DEFAULT;""")
    op.execute(
        """ALTER TABLE users ALTER mail_status TYPE BOOLEAN
        USING
        CASE
        WHEN mail_status='V' THEN true
        WHEN mail_status='W' then false
        ELSE NULL
        END;"""
    )
    op.execute("""ALTER TABLE users ALTER mail_status SET DEFAULT NULL;""")
    #### samples free_cols
    op.execute(
        """DO
    $$
    BEGIN
        FOR  colnames
        in 31..60
        LOOP
         EXECUTE 'ALTER TABLE samples ADD COLUMN t' || colnames || ' VARCHAR(250);';
        END LOOP;
    END
    $$;"""
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_password_reset")
    op.drop_column("users", "status_date")
    op.drop_column("users", "status_admin_comment")
    op.execute("""ALTER TABLE users ALTER status DROP DEFAULT;""")
    op.execute(
        """ALTER TABLE users ALTER status TYPE BOOLEAN
    USING
    CASE
    WHEN status=1 THEN true ELSE false
    END;"""
    )
    op.execute("""ALTER TABLE users ALTER status SET DEFAULT true;""")
    op.execute("""ALTER TABLE users RENAME COLUMN status TO active ;""")
    # alter mail_status from bool to char
    op.execute("""ALTER TABLE users ALTER mail_status DROP DEFAULT;""")
    op.execute(
        """ALTER TABLE users ALTER mail_status TYPE CHAR
        USING
        CASE
        WHEN mail_status=true THEN 'V'
        WHEN mail_status=false then 'W'
        ELSE ' '
        END;"""
    )
    op.execute("""ALTER TABLE users ALTER mail_status SET DEFAULT ' ';""")
    #### samples free_cols
    op.execute(
        """DO
        $$
        BEGIN
            FOR  colnames
            in 31..60
            LOOP
             EXECUTE 'ALTER TABLE samples DROP COLUMN t' || colnames || '';
            END LOOP;
        END
        $$;"""
    )
    # ### end Alembic commands ###
