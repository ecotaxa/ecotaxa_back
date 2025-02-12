""" top_n after logs clean

Revision ID: 067cd670782d
Revises: d3bfaa54d544
Create Date: 2024-01-07 07:30:50.772766

"""

# revision identifiers, used by Alembic.
revision = "067cd670782d"
down_revision = "d3bfaa54d544"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table("dbplyr_006")
    # op.drop_table("dbplyr_003")
    # op.drop_table("dbplyr_007")
    # op.drop_table("dbplyr_002")
    # op.drop_table("dbplyr_005")
    # op.drop_table("dbplyr_001")
    # op.drop_table("dbplyr_004")
    # op.drop_table('dropped_samples_26032024')
    # op.drop_table('dropped_process_26032024')
    # op.drop_table('proj_with_incon')
    # op.drop_table('dropped_acquisitions_26032024')

    op.create_table(
        "training",
        sa.Column("training_id", sa.INTEGER(), nullable=False),
        sa.Column("projid", sa.INTEGER(), nullable=True),
        sa.Column("training_author", sa.INTEGER(), nullable=False),
        sa.Column("training_start", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("training_end", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("training_path", sa.VARCHAR(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["training_author"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["projid"], ["projects.projid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("training_id"),
    )
    op.create_index(
        "trn_projid_start", "training", ["projid", "training_start"], unique=True
    )

    op.create_table(
        "prediction",
        sa.Column("object_id", sa.BIGINT(), nullable=False),
        sa.Column("training_id", sa.INTEGER(), nullable=False),
        sa.Column("classif_id", sa.INTEGER(), nullable=False),
        sa.Column("score", postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.ForeignKeyConstraint(["classif_id"], ["taxonomy.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_id"], ["obj_head.objid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["training_id"], ["training.training_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("object_id", "classif_id"),
    )
    op.create_index(
        "is_prediction_training", "prediction", ["training_id"], unique=False
    )

    op.create_table(
        "prediction_histo",
        sa.Column("object_id", sa.BIGINT(), nullable=False),
        sa.Column("training_id", sa.INTEGER(), nullable=False),
        sa.Column("classif_id", sa.INTEGER(), nullable=False),
        sa.Column("score", postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.ForeignKeyConstraint(["classif_id"], ["taxonomy.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_id"], ["obj_head.objid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["training_id"], ["training.training_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("training_id", "object_id", "classif_id"),
    )
    op.create_index(
        "is_prediction_histo_object", "prediction_histo", ["object_id"], unique=False
    )

    # op.create_index('is_phy_image_file', 'image_file', ['digest_type', 'digest'], unique=False)
    #
    # op.alter_column('images', 'imgid',
    #            existing_type=sa.BIGINT(),
    #            nullable=True)
    # op.create_foreign_key(None, 'images', 'obj_head', ['objid'], ['objid'])

    # Migrate the relevant predictions for each object
    # In previous schema, the last prediction is in the object, whatever its classif_qual
    # When moving from 'P' to 'V', the last prediction was (sometimes...) copied into log table, but not removed from object
    op.execute(
        """
    -- All objects ever predicted, with their project        
    CREATE UNLOGGED TABLE mig_obj_prj as
    SELECT prj.projid, -- optimized column order as we have 500M lines here
           obh.classif_auto_id,
           obh.objid,
           obh.classif_auto_score,
           obh.classif_auto_when
      FROM obj_head obh
         JOIN acquisitions acq ON obh.acquisid = acq.acquisid
         JOIN samples sam ON acq.acq_sample_id = sam.sampleid
         JOIN projects prj ON sam.projid = prj.projid
    WHERE obh.classif_auto_when IS NOT NULL
    UNION
    -- All objects previously predicted (lots were cleaned!), with their project        
    SELECT prj.projid,
           och.classif_id as classif_auto_id,
           och.objid,
           och.classif_score as classif_auto_score,
           och.classif_date as classif_auto_when
      FROM objectsclassifhisto och
         JOIN obj_head obh ON och.objid = obh.objid
         JOIN acquisitions acq ON obh.acquisid = acq.acquisid
         JOIN samples sam ON acq.acq_sample_id = sam.sampleid
         JOIN projects prj ON sam.projid = prj.projid
    WHERE och.classif_qual = 'P'
    """
    )
    op.execute(
        """
    create index on mig_obj_prj (projid, objid);
    ALTER TABLE mig_obj_prj SET (autovacuum_enabled = off);
    analyze mig_obj_prj
    """
    )

    op.execute(
        """
    -- Grouped writes of previous prediction tasks, per project & date
    create UNLOGGED table mig_unq_classif_per_proj as
    SELECT projid, classif_auto_when, count(objid) as nb_objs
    from mig_obj_prj
    group by projid, classif_auto_when
    """
    )

    # Determined via
    # with nxt as (select objid, classif_auto_when, lead(classif_auto_when) over (partition by projid,objid order by classif_auto_when) next_same_obj from mig_obj_prj)
    # select min(next_same_obj-classif_auto_when) from nxt where next_same_obj is not null;
    #      min
    # -----------------
    #  00:00:44.886878
    interv = "'44 sec'"

    op.execute(
        f"""
    -- Look for start and end dates of prediction tasks
    -- assuming that 5 minutes have elapsed b/w 2 tasks on same project (time for human to read a bit the result)
    create UNLOGGED table mig_classif_chunks_per_proj as
    SELECT case when delta_prev > {interv} then 'B' end as B,
       case when delta_next > {interv} then 'E' end as E,
       *
    from (SELECT projid,
             classif_auto_when,
             nb_objs,
             case -- no previous line or different project -> yesterday -> kept in filter
                 when (lead(projid, -1, -1) OVER paw) != projid then '1 day'::interval
                 else classif_auto_when - lead(classif_auto_when, -1) OVER paw
                 end as delta_prev,
             case -- no next line or different project -> tomorrow -> kept in filter
                 when (lead(projid, 1, -1) OVER paw) != projid then '1 day'::interval
                 else lead(classif_auto_when, 1) OVER paw - classif_auto_when
                 end as delta_next
      from mig_unq_classif_per_proj
      window paw as (ORDER BY projid, classif_auto_when)) deltas
    where (delta_next > {interv}
    or delta_prev > {interv})
    order by projid, classif_auto_when
    """
    )
    op.execute(
        f"""
    -- Reconstituted (approximately) old tasks
    create UNLOGGED table mig_classif_tasks as
    SELECT projid,
       classif_auto_when as begin_date,
       (SELECT classif_auto_when
        from mig_classif_chunks_per_proj mcc2
        where mcc2.classif_auto_when >= mcc.classif_auto_when
          and mcc2.projid = mcc.projid
          and mcc2.delta_next > {interv}
        order by mcc2.classif_auto_when
        limit 1) as end_date
    from mig_classif_chunks_per_proj mcc
    where delta_prev > {interv}
    """
    )
    op.execute(
        """
    create unique index on mig_classif_tasks (projid, begin_date, end_date);
    analyze mig_classif_tasks
    """
    )

    op.execute(
        """
    -- Each task becomes a training.
    -- Note that some old tasks have the _same_ begin_date for different projects.
    insert into training (projid, training_author, training_start, training_end, training_path)
    select mct.projid, 1, mct.begin_date, mct.end_date, 'Migrated ' || current_date 
      from mig_classif_tasks mct        
    """
    )
    # Note: Trainings do not overlap:
    # select * from training trn
    #     where exists(select 1 from training trn2 where trn2.projid = trn.projid and trn.training_id != trn2.training_id
    #                                              and (trn2.training_start between trn.training_start and trn.training_end
    #                                                  or trn2.training_end between trn.training_start and trn.training_end))
    op.execute(
        """
    analyze training
    """
    )

    op.execute(
        """
    create UNLOGGED table mig_obj_prj2 as select mop.*, trn.training_id
                    from mig_obj_prj mop
                             join training trn on mop.projid = trn.projid and
                                                  mop.classif_auto_when between trn.training_start and trn.training_end;
    create index on mig_obj_prj2 (projid, objid);
    create unique index on mig_obj_prj2 (objid, classif_auto_when); -- An object could not be moved state twice at same time
    analyze mig_obj_prj2; 
    ALTER TABLE mig_obj_prj2 SET (autovacuum_enabled = off)
    """
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
        vacuum full verbose mig_obj_prj2
        """
        )

    op.execute(
        """
do
$$
    declare
        curprj  record;
        o_count integer;
        h_count integer;
        sum_o integer = 0;
    begin
        for curprj in (select distinct projid from mig_obj_prj2 order by projid)
            loop
                -- Active predictions - the objects currently predicted
                insert into prediction(training_id, object_id, classif_id, score)
                select mop.training_id, mop.objid, mop.classif_auto_id, mop.classif_auto_score
                  from mig_obj_prj2 mop
                  join obj_head obh 
                    on obh.objid = mop.objid
                       and obh.classif_auto_when = mop.classif_auto_when
                       -- and obh.classif_auto_id = mop.classif_auto_id
                 where mop.projid = curprj.projid
                   and obh.classif_qual = 'P'
                  -- favorable grouping of tuples in blocks
                  order by 2,3,4;
                GET DIAGNOSTICS o_count = ROW_COUNT;
                sum_o = sum_o + o_count;
                -- Archived predictions - the history.
                -- Note: in theory, the last 'P' is not an archive if current state is not 'P'
                insert into prediction_histo(training_id, object_id, classif_id, score)
                select mop.training_id, mop.objid, mop.classif_auto_id, mop.classif_auto_score
                  from mig_obj_prj2 mop
                  join objectsclassifhisto och 
                    on och.objid = mop.objid
                       and och.classif_date = mop.classif_auto_when
                       -- and och.classif_id = mop.classif_auto_id
                       -- and och.classif_qual = 'P'
                       -- and och.classif_score = mop.classif_auto_score
                 where mop.projid = curprj.projid                   
                  -- favorable grouping of tuples in blocks
                  order by 1,2,3,4;
                GET DIAGNOSTICS h_count = ROW_COUNT;
                sum_o = sum_o + h_count;
                RAISE NOTICE 'project: % preds % hist % Σ %, time:%', curprj.projid, o_count, h_count, sum_o, clock_timestamp();
                -- COMMIT;
            end loop;
    end;
$$
"""
    )

    op.execute(
        """
    analyze prediction;
    analyze prediction_histo
    """
    )

    # TODO: Check all trainings are used
    # create temp table trainings_used as select distinct training_id from prediction union select distinct training_id from prediction_histo;
    # select count(1) from training; select count(1) from trainings_used;

    # TODO: Check nightly job verifications are OK
    # TODO: Check values are == b/w object/histo and their freshest predictions

    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole")

    # ### end Alembic commands ###


def downgrade():
    # There is no way back
    pass
    # ### end Alembic commands ###
