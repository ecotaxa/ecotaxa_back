""" Logs Cleanup

Revision ID: d3bfaa54d544
Revises: a9dd3c62b7b0
Create Date: 2024-10-10 07:14:48.871263
"""

# revision identifiers, used by Alembic.
revision = "d3bfaa54d544"
down_revision = "a9dd3c62b7b0"

from alembic import op


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

    op.execute(
        """
    ALTER TABLE obj_head SET (autovacuum_enabled = off);
    ALTER TABLE objectsclassifhisto SET (autovacuum_enabled = off);
    -- Save some time on inserts
    ALTER TABLE ONLY public.objectsclassifhisto
        DROP CONSTRAINT objectsclassifhisto_classif_who_fkey,
        DROP CONSTRAINT objectsclassifhisto_objid_fkey
    """
    )

    # Self-consistency in objectsclassifhisto
    # Fix taxo FK inconsistencies
    op.execute(
        """
    -- No classif_id, 777 lines as of 07/01/2024    
    delete from objectsclassifhisto where classif_id is null"""
    )
    op.execute(
        """
    -- Wrong classif_id, 8K lines as of 07/01/2024        
    delete from objectsclassifhisto where classif_id not in (SELECT id from taxonomy)"""
    )

    # Self-consistency in obj_head
    # Fix taxo FK inconsistencies
    op.execute(
        """
    -- Some 4K objects in PROD have an invalid classif_auto_id, for 'P' we need to recreate the fake prediction
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
    -- Some 4K objects in PROD have an invalid classif_auto_id, for 'V'/'D' we can just erase _auto*
    update obj_head
       set classif_auto_id=null,
           classif_auto_score=null,
           classif_auto_when=null
     where classif_qual in ('V','D')
       and classif_auto_id is not null
       and classif_auto_id not in (SELECT id from taxonomy)
    """
    )
    op.execute(
        """
    -- Some 1.8M objects in PROD have an inconsistent classif_auto_id, as for 'P' it should be classif_id.
    -- It's probably the consequence of legacy "revert to predicted' code which did not care about _auto fields
    -- or "import update predicted" before 2024 cleanup.
    update obj_head
       set classif_auto_id=classif_id
     where classif_qual = 'P'
       and classif_auto_id != classif_id
    """
    )

    # Consistency b/w object and its history, AKA dates hell!
    # Note: classif_auto_* columns are an embedded history for non-'P' states
    #       but _current_ values for 'P' state. All has to be consistent before migration.

    op.execute(
        """
    -- Some 'V' or 'D' objects in PROD have an inconsistent classif_auto_when, taking place after human validation.
    -- Maybe some version of EcoTaxa allowed to re-predict without state move. Delete the user-hidden 'P'.
    -- 4M objects
    update obj_head
       set classif_auto_id=null,
           classif_auto_score=null,
           classif_auto_when=null
     where classif_qual in ('V','D')
       and classif_auto_when > classif_when
    """
    )
    op.execute(
        """
    -- Some 'V' or 'D' objects in PROD have some history after the object.
    -- History should be strictly 'before the present', so remove history. We still have the data in obj_head.
    -- 4.8M history
    delete from objectsclassifhisto och
     using obj_head obh
     where obh.objid = och.objid 
       and obh.classif_when <= och.classif_date 
       and obh.classif_qual in ('V','D')
        """
    )
    op.execute(
        """
    -- Some 'P' objects in PROD have a prediction date before (or same as) a 'V' or 'D' in history.
    -- e.g. history says 'P' on 23/12, 'V' on 24/12, but in object there is 'P' on 23/12
    -- probably due to old 'reset to predicted' or 'revert' code. 
    -- 680K rows
    -- Warp them a bit in future but don't create too many new dates
    create temp table bad_p as
    select distinct obh.objid, obh.acquisid
      from obj_head obh
      join objectsclassifhisto och
           on och.objid = obh.objid 
           and och.classif_date >= obh.classif_auto_when
           and och.classif_qual != 'P'
     where obh.classif_qual='P';
    create temp table bad_p_acquis as
    select distinct acquisid
      from bad_p;
    create temp table bad_p_acquis_max as
    select bpa.acquisid, max(och.classif_date) + interval '1 hour' as acquis_max
      from bad_p_acquis bpa
      join obj_head obh on obh.acquisid = bpa.acquisid
      join objectsclassifhisto och on och.objid = obh.objid
     group by bpa.acquisid;
    update obj_head obh
       set classif_auto_when = bpam.acquis_max
      from bad_p bap
      join bad_p_acquis_max bpam on bpam.acquisid = bap.acquisid
     where obh.objid = bap.objid
        """
    )
    op.execute(
        """
    -- 'P' is freshest row, we have avoided duplicate due to volunteer copy above, cleanup.
    -- 763K history in PROD, some should be cured by above fixes    
    delete from objectsclassifhisto och 
     using obj_head obh 
     where obh.objid = och.objid 
       and obh.classif_auto_when = och.classif_date 
       and obh.classif_qual = 'P'
       and och.classif_qual = 'P'
     """
    )
    op.execute(
        """
    -- Some 47K objects in PROD have an implied historical P with exact same date as a log with P,
    -- but different produced classification or score. Remove the faulty history, it's eventually re-created OK next step.
    delete from objectsclassifhisto och
     using obj_head obh
     where och.classif_qual = 'P'
       and och.objid = obh.objid
       and och.classif_date = obh.classif_auto_when
       and (och.classif_id != obh.classif_auto_id
            or och.classif_score != obh.classif_auto_score)
        """
    )
    op.execute(
        """
    -- 'P' should have been historized when moving to 'V' or 'D', it was not always the case.
    -- 68M objects
    -- Note: We use a temp table as insert...select does not go parallel
    create temp table missing_ps as
    select obh.objid, obh.classif_auto_when, obh.classif_auto_id, 'A' as classif_type, 'P' as classif_qual, obh.classif_auto_score
      from obj_head obh 
      left join objectsclassifhisto och on och.objid=obh.objid and och.classif_date=obh.classif_auto_when
     where obh.classif_qual in ('V','D')
       and obh.classif_auto_when is not null
       and och.objid is null;
    insert into objectsclassifhisto (objid, classif_date, classif_id, classif_type, classif_qual, classif_score)
    select * from missing_ps;
    drop table missing_ps
    """
    )

    # Cleanup useless prediction history. Can't rewind to more than 'last prediction' as of today PROD.
    op.execute(
        """
    -- Remove consecutive predictions in history
    -- 1160M rows
    with curr_and_next as (select objid, classif_date, classif_qual,
                                  lead(classif_qual) over (partition by objid order by classif_date) as next_qual
                             from objectsclassifhisto och),
         both_are_p as (select objid, classif_date 
                          from curr_and_next 
                         where classif_qual = 'P' and next_qual = 'P')
    delete from objectsclassifhisto och
        using both_are_p
     where och.objid = both_are_p.objid
       and och.classif_date = both_are_p.classif_date                  
           """
    )

    with op.get_context().autocommit_block():
        op.execute(
            """
        vacuum full verbose analyze objectsclassifhisto
        """
        )

    op.execute(
        """
    -- Enforce the rule above "not 2 consecutive predictions". Current object is Predicted, and last history as well -> delete histo
    -- 129M rows
    create temp table pred_in_last as 
        (select p_and_last.objid, p_and_last.classif_date
           from (select objid, classif_date,
                        lead(classif_qual) over (partition by objid order by classif_date) as next_qual
                   from objectsclassifhisto och
                  where och.classif_qual = 'P') p_and_last
                   join obj_head obh
                     on obh.objid = p_and_last.objid
                        and obh.classif_qual = 'P'
                        and p_and_last.next_qual is null);
    analyze pred_in_last;
    delete from objectsclassifhisto och
     where (och.objid, och.classif_date) in (select objid, classif_date from pred_in_last);
    drop table pred_in_last
    """
    )

    op.create_foreign_key(None, "obj_head", "taxonomy", ["classif_id"], ["id"])
    # This one will be dropped with its column
    op.create_foreign_key(None, "obj_head", "taxonomy", ["classif_auto_id"], ["id"])

    with op.get_context().autocommit_block():
        op.execute(
            """
        vacuum full verbose analyze objectsclassifhisto
        """
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
    ALTER TABLE ONLY public.objectsclassifhisto
        ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users (id),
        ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
    ALTER TABLE obj_head SET (autovacuum_enabled = on);
    ALTER TABLE objectsclassifhisto SET (autovacuum_enabled = on)
    """
    )


# ### end Alembic commands ###


def downgrade():
    # There is no way back, we deleted 100s of million rows
    pass
    # ### end Alembic commands ###
