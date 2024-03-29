"""No dup fk in objects

Revision ID: a74a857fe352
Revises: f4ea49253597
Create Date: 2021-01-25 09:48:31.333083

"""

# revision identifiers, used by Alembic.
revision = "a74a857fe352"
down_revision = "f4ea49253597"

import sqlalchemy as sa
from alembic import op

OBJECTS_DDL_a74a857fe352 = """create view objects as 
                  select sam.projid, sam.sampleid, obh.*, obh.acquisid as processid, ofi.*
                    from obj_head obh
                    join acquisitions acq on obh.acquisid = acq.acquisid
                    join samples sam on acq.acq_sample_id = sam.sampleid 
                    left join obj_field ofi on obh.objid = ofi.objfid; -- allow elimination by planner
                    """


def upgrade():
    op.execute("drop view objects")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("is_objectsdate", table_name="obj_head")
    op.drop_index("is_objectsdepth", table_name="obj_head")
    op.drop_index("is_objectstime", table_name="obj_head")
    op.drop_index("is_objectsampleclassif", table_name="obj_head")
    op.drop_index("is_objectsprojclassifqual", table_name="obj_head")
    op.drop_index("is_objectsprojectonly", table_name="obj_head")
    op.drop_index("is_objectsprojrandom", table_name="obj_head")

    op.create_index("is_objectsdate", "obj_head", ["objdate", "acquisid"], unique=False)
    op.create_index(
        "is_objectsdepth",
        "obj_head",
        ["depth_max", "depth_min", "acquisid"],
        unique=False,
    )
    op.create_index("is_objectstime", "obj_head", ["objtime", "acquisid"], unique=False)
    op.create_index(
        "is_objectsacqclassifqual",
        "obj_head",
        ["acquisid", "classif_id", "classif_qual"],
        unique=False,
    )
    op.create_index(
        "is_objectsacqrandom",
        "obj_head",
        ["acquisid", "random_value", "classif_qual"],
        unique=False,
    )
    # op.create_index('is_objectfieldsorigid', 'obj_field', ['orig_id'], unique=False)

    op.drop_constraint("obj_head_sampleid_fkey", "obj_head", type_="foreignkey")
    op.drop_constraint("obj_head_projid_fkey", "obj_head", type_="foreignkey")
    # op.drop_constraint('obj_head_acquisid_fkey', 'obj_head', type_='foreignkey')
    # op.create_foreign_key(None, 'obj_head', 'acquisitions', ['acquisid'], ['acquisid'])
    op.drop_column("obj_head", "projid")
    op.drop_column("obj_head", "sampleid")
    # ### end Alembic commands ###
    op.execute(OBJECTS_DDL_a74a857fe352)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "obj_head",
        sa.Column("sampleid", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "obj_head",
        sa.Column("projid", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_constraint(None, "obj_head", type_="foreignkey")
    op.create_foreign_key(
        "obj_head_projid_fkey", "obj_head", "projects", ["projid"], ["projid"]
    )
    op.create_foreign_key(
        "obj_head_sampleid_fkey", "obj_head", "samples", ["sampleid"], ["sampleid"]
    )
    op.create_foreign_key(
        "obj_head_acquisid_fkey",
        "obj_head",
        "acquisitions",
        ["acquisid"],
        ["acquisid"],
        ondelete="CASCADE",
    )
    op.create_index(
        "is_objectsprojrandom",
        "obj_head",
        ["projid", "random_value", "classif_qual"],
        unique=False,
    )
    op.create_index("is_objectsprojectonly", "obj_head", ["projid"], unique=False)
    op.create_index(
        "is_objectsprojclassifqual",
        "obj_head",
        ["projid", "classif_id", "classif_qual"],
        unique=False,
    )
    op.create_index(
        "is_objectsampleclassif",
        "obj_head",
        ["sampleid", "classif_id", "classif_qual"],
        unique=False,
    )
    op.drop_index("is_objectstime", table_name="obj_head")
    op.create_index("is_objectstime", "obj_head", ["objtime", "projid"], unique=False)
    op.drop_index("is_objectsdepth", table_name="obj_head")
    op.create_index(
        "is_objectsdepth",
        "obj_head",
        ["depth_max", "depth_min", "projid"],
        unique=False,
    )
    op.drop_index("is_objectsdate", table_name="obj_head")
    op.create_index("is_objectsdate", "obj_head", ["objdate", "projid"], unique=False)
    op.drop_index("is_objectsacqrandom", table_name="obj_head")
    op.drop_index("is_objectsacqclassifqual", table_name="obj_head")
    op.drop_index("is_objectfieldsorigid", table_name="obj_field")
    # ### end Alembic commands ###
