"""top-n

Revision ID: d3bfaa54d544
Revises: 0a3132f436fb
Create Date: 2024-01-07 07:30:50.772766

"""

# revision identifiers, used by Alembic.
revision = "d3bfaa54d544"
down_revision = "0a3132f436fb"

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
        sa.PrimaryKeyConstraint("object_id", "training_id", "classif_id", "score"),
    )
    op.create_index(
        "pred_object_id", "prediction", ["training_id", "object_id"], unique=False
    )

    # op.create_index('is_phy_image_file', 'image_file', ['digest_type', 'digest'], unique=False)
    #
    # op.alter_column('images', 'imgid',
    #            existing_type=sa.BIGINT(),
    #            nullable=True)
    # op.create_foreign_key(None, 'images', 'obj_head', ['objid'], ['objid'])

    op.add_column("obj_head", sa.Column("training_id", sa.INTEGER(), nullable=True))
    op.create_index("is_objecttraining", "obj_head", ["training_id"], unique=False)
    op.create_foreign_key(
        None, "obj_head", "training", ["training_id"], ["training_id"]
    )

    op.execute(
        """
    ALTER TABLE objectsclassifhisto SET (autovacuum_enabled = off);
    vacuum verbose objectsclassifhisto
    """
    )
    op.execute(
        """
    -- Remove consecutive predictions in history    
    delete from objectsclassifhisto och
    where och.classif_qual = 'P'
      and (select och2.classif_qual
           from objectsclassifhisto och2
           where och2.objid = och.objid
             and och2.classif_date > och.classif_date
           order by och.classif_date
           limit 1) = 'P'
           """
    )

    op.add_column(
        "objectsclassifhisto", sa.Column("training_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "is_objecthistotraining", "objectsclassifhisto", ["training_id"], unique=False
    )
    op.create_foreign_key(
        None,
        "objectsclassifhisto",
        "training",
        ["training_id"],
        ["training_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(None, "obj_head", "taxonomy", ["classif_id"], ["id"])

    op.execute(
        """
    -- No classif_id, 777 lines as of 07/01/2024    
    delete from objectsclassifhisto where classif_id is null"""
    )
    #
    op.execute(
        """
    -- Wrong classif_id,  8960 lines as of 07/01/2024        
    delete from objectsclassifhisto where classif_id not in (SELECT id from taxonomy)"""
    )
    # FK is now consistent
    op.create_foreign_key(
        None,
        "objectsclassifhisto",
        "taxonomy",
        ["classif_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        """
    -- Some 4007 objects in PROD have an invalid classif_auto_id, for 'P' we need to recreate the fake prediction
    update obj_head
       set classif_auto_id=classif_id,
           classif_auto_score=coalesce(classif_auto_score, 1),
           classif_auto_when=coalesce(classif_auto_when,'01/01/1970')
     where classif_qual = 'P'
       and classif_auto_id is not null
       and classif_auto_id not in (SELECT id from taxonomy)
    """
    )
    op.execute(
        """
    -- Some 4007 objects in PROD have an invalid classif_auto_id, for 'V'/'D' we can just erase _auto*
    update obj_head
       set classif_auto_id=null,
           classif_auto_score=null,
           classif_auto_when=null
     where classif_qual in ('V','D')
       and classif_auto_id is not null
       and classif_auto_id not in (SELECT id from taxonomy)
    """
    )

    # Migrate the relevant predictions for each object
    # In previous schema, the last prediction is in the object, whatever its classif_qual
    # When moving from 'P' to 'V', the last prediction was copied into log table, but not removed from object
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
    create index on mig_obj_prj (objid, classif_auto_id, classif_auto_when);
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

    op.execute(
        """
    -- Look for start and end dates of prediction tasks
    -- assuming that 5 minutes have elapsed b/w 2 tasks on same project (time for human to read a bit the result)
    create UNLOGGED table mig_classif_chunks_per_proj as
    SELECT case when delta_prev > '5 min' then 'B' end as B,
       case when delta_next > '5 min' then 'E' end as E,
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
    where (delta_next > '5 min'
    or delta_prev > '5 min')
    order by projid, classif_auto_when
    """
    )
    op.execute(
        """
    -- Reconstituted (approximately) old tasks
    create UNLOGGED table mig_classif_tasks as
    SELECT projid,
       classif_auto_when as begin_date,
       (SELECT classif_auto_when
        from mig_classif_chunks_per_proj mcc2
        where mcc2.classif_auto_when >= mcc.classif_auto_when
          and mcc2.projid = mcc.projid
          and mcc2.delta_next > '5 min'
        order by mcc2.classif_auto_when
        limit 1) as end_date
    from mig_classif_chunks_per_proj mcc
    where delta_prev > '5 min'
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
    alter table mig_obj_prj add column training_id integer;
    update mig_obj_prj mop
       set training_id = (select trn.training_id
                            from training trn
                           where mop.projid = trn.projid
                             and mop.classif_auto_when between trn.training_start and trn.training_end);    
    """
    )

    op.execute(
        """
    -- Create predictions for past values
    insert into prediction(training_id, object_id, classif_id, score)
    select mop.training_id, mop.objid, mop.classif_auto_id, mop.classif_auto_score
      from mig_obj_prj mop
      -- There are a few duplicates (6K/500M) as the assumption '5 minutes b/w predictions' above in not true
      on conflict (object_id, training_id, classif_id, score) do nothing
    """
    )
    op.execute(
        """
    analyze prediction
    """
    )

    op.execute(
        """
    ALTER TABLE obj_head SET (autovacuum_enabled = off)
    """
    )
    op.execute(
        """
do
$$
    declare
        curprj  record;
        o_count integer;
        sum_count integer = 0;
    begin
        for curprj in (select distinct projid from mig_obj_prj order by projid)
            loop
                -- Inject training back into objects
                update obj_head obh
                   set training_id = mop.training_id
                  from mig_obj_prj mop
                 where obh.classif_qual = 'P'
                   and mop.objid = obh.objid
                   and mop.classif_auto_id = obh.classif_auto_id
                   and mop.classif_auto_score = obh.classif_auto_score
                   and mop.classif_auto_when = obh.classif_auto_when
                   and mop.projid = curprj.projid;
                GET DIAGNOSTICS o_count = ROW_COUNT;
                sum_count = sum_count + o_count;
                RAISE NOTICE 'project: % preds % Σ %, time:%', curprj.projid, o_count, sum_count, clock_timestamp();
            end loop;
    end;
$$;
"""
    )

    op.execute(
        """
do
$$
    declare
        curprj  record;
        o_count integer;
        sum_count integer = 0;
    begin
        for curprj in (select distinct projid from mig_obj_prj order by projid)
            loop
            -- Link historical Predicted with reconstituted predictions
            update objectsclassifhisto och
               set training_id = mop.training_id
              from mig_obj_prj mop
             where och.classif_qual = 'P'
               and mop.objid = och.objid
               and mop.classif_auto_id = och.classif_id
               and mop.classif_auto_score = och.classif_score
               and mop.classif_auto_when = och.classif_date
               and mop.projid = curprj.projid;
            GET DIAGNOSTICS o_count = ROW_COUNT;
            sum_count = sum_count + o_count;
            RAISE NOTICE 'project: % hpreds % Σ %, time:%', curprj.projid, o_count, sum_count, clock_timestamp();
        end loop;
    end;
$$;
      """
    )

    # TODO: Check all trainings are used
    # TODO: Check nightly job verifications are OK
    # TODO: Check values are == b/w object/histo and their fresh predictions

    # op.drop_column("objectsclassifhisto", "classif_score")
    # op.drop_column("objectsclassifhisto", "classif_type")
    # op.drop_column("obj_head", "classif_auto_id")
    # op.drop_column("obj_head", "classif_auto_score")
    # op.drop_column("obj_head", "classif_auto_when")

    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole")


# ### end Alembic commands ###


def downgrade():
    # There is no way back, we drop unused columns
    pass
    # ### end Alembic commands ###
