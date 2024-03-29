"""redundant columns

Revision ID: 6f57c8aa715d
Revises: d3309bb7012e
Create Date: 2021-01-18 10:40:39.241669

"""

# revision identifiers, used by Alembic.
revision = "6f57c8aa715d"
down_revision = "08fdc2b6bce0"

remove_unreferenced_processes = """
    delete from process 
     where processid not in (select acquisid from acquisitions);
"""

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.execute(remove_unreferenced_processes)
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("IS_AcquisitionsProjectOrigId", table_name="acquisitions")
    op.drop_constraint("acquisitions_projid_fkey", "acquisitions", type_="foreignkey")
    op.drop_column("acquisitions", "projid")

    op.drop_index("IS_ProcessProject", table_name="process")
    op.drop_constraint("process_projid_fkey", "process", type_="foreignkey")
    op.drop_column("process", "projid")

    # Forgotten (in 2.5.0) FK which allows sane link process<->acquisitions
    op.create_foreign_key(
        None,
        "process",
        "acquisitions",
        ["processid"],
        ["acquisid"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade():
    # Below is a bit theoretical... No way back
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "process", sa.Column("projid", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.drop_constraint(None, "process", type_="foreignkey")
    op.create_foreign_key(
        "process_projid_fkey", "process", "projects", ["projid"], ["projid"]
    )
    op.create_index("IS_ProcessProject", "process", ["projid"], unique=False)

    op.add_column(
        "acquisitions",
        sa.Column("projid", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        "acquisitions_projid_fkey", "acquisitions", "projects", ["projid"], ["projid"]
    )
    op.create_index(
        "IS_AcquisitionsProjectOrigId",
        "acquisitions",
        ["projid", "orig_id"],
        unique=True,
    )
    # ### end Alembic commands ###
