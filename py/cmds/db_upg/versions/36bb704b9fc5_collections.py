"""Collections

Revision ID: 36bb704b9fc5
Revises: 15cad3c0948e
Create Date: 2020-11-03 05:57:12.753456

"""

# revision identifiers, used by Alembic.
revision = "36bb704b9fc5"
down_revision = "15cad3c0948e"

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "collection",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("external_id", sa.VARCHAR(), nullable=False),
        sa.Column("external_id_system", sa.VARCHAR(), nullable=False),
        sa.Column("provider_user_id", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(), nullable=False),
        sa.Column("contact_user_id", sa.INTEGER(), nullable=True),
        sa.Column("citation", sa.VARCHAR(), nullable=True),
        sa.Column("license", sa.VARCHAR(length=16), nullable=True),
        sa.Column("abstract", sa.VARCHAR(), nullable=True),
        sa.Column("description", sa.VARCHAR(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contact_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("CollectionTitle", "collection", ["title"], unique=True)
    op.create_table(
        "collection_project",
        sa.Column("collection_id", sa.INTEGER(), nullable=False),
        sa.Column("project_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collection.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.projid"],
        ),
        sa.PrimaryKeyConstraint("collection_id", "project_id"),
    )
    op.create_table(
        "collection_user_role",
        sa.Column("collection_id", sa.INTEGER(), nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("role", sa.VARCHAR(length=1), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collection.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("collection_id", "user_id", "role"),
    )
    op.create_table(
        "collection_orga_role",
        sa.Column("collection_id", sa.INTEGER(), nullable=False),
        sa.Column("organisation", sa.String(length=255), nullable=False),
        sa.Column("role", sa.VARCHAR(length=1), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collection.id"],
        ),
        sa.PrimaryKeyConstraint("collection_id", "organisation", "role"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("collection_orga_role")
    op.drop_table("collection_user_role")
    op.drop_table("collection_project")
    op.drop_index("CollectionTitle", table_name="collection")
    op.drop_table("collection")
    # ### end Alembic commands ###
