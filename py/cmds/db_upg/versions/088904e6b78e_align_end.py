"""align end

Revision ID: 088904e6b78e
Revises: a173f0289de1
Create Date: 2022-03-02 10:13:31.452286

"""

# revision identifiers, used by Alembic.
revision = "088904e6b78e"
down_revision = "a173f0289de1"

from alembic import op

PROCESS_CLEAN = """
delete from process where processid in (select processid from process except select acquisid from acquisitions)
"""


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index("CollectionShortTitle", "collection", ["short_title"], unique=True)
    op.execute(PROCESS_CLEAN)
    op.create_foreign_key(
        None, "process", "acquisitions", ["processid"], ["acquisid"], ondelete="CASCADE"
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "process", type_="foreignkey")
    op.drop_index("CollectionShortTitle", table_name="collection")
    # ### end Alembic commands ###
