-- Fix for "red" nightly task due to missing predictions after a
-- subset and "Rest status to predicted" or "Edit or erase annotations massively"
create temp table problems_pred as select obh.*
    from obj_head obh
    left join prediction prd
       on prd.object_id = obh.objid
       and prd.classif_id = obh.classif_id
       and prd.score = obh.classif_score
    where obh.classif_qual = 'P'
      and prd.object_id is null;

DO $$
DECLARE
    cur_proj RECORD;
    new_training_id INTEGER;
BEGIN
    FOR cur_proj IN
        SELECT DISTINCT projid
        FROM objects
        WHERE objid IN (SELECT objid FROM problems_pred)
        ORDER BY projid
    LOOP
        -- Create a training entry for this project
        INSERT INTO training (projid, training_author, training_start, training_end, training_path)
        VALUES (cur_proj.projid, 1, NOW(), NOW(), 'fix_missing_pred in '||cur_proj.projid)
        RETURNING training_id INTO new_training_id;

        -- Create predictions from problems_pred for this project
        INSERT INTO prediction (object_id, training_id, classif_id, score)
        SELECT p.objid, new_training_id, p.classif_id, p.classif_score
        FROM problems_pred p
        JOIN objects o ON p.objid = o.objid
        WHERE o.projid = cur_proj.projid;

        RAISE NOTICE 'Project %: Created training % with % predictions',
            cur_proj.projid, new_training_id, (SELECT count(*) FROM problems_pred p JOIN objects o ON p.objid = o.objid WHERE o.projid = cur_proj.projid);
    END LOOP;
END $$;


