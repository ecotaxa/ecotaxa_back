"""projects_cnn_image_position: position of image (by rank) to use for CNN prediction

Revision ID: 324867bfe911
Revises: 5d2e8c41a7b3
Create Date: 2026-11-19 17:35:58.138752

"""

# revision identifiers, used by Alembic.
revision = "324867bfe911"
down_revision = "5d2e8c41a7b3"

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column(
        "projects",
        sa.Column("cnn_image_position", sa.INTEGER(), nullable=True),
    )


def downgrade():
    op.drop_column("projects", "cnn_image_position")
