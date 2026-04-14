create table per_proj as select acquisid/1e7::int as projid, count(1) as nb from obj_head group by projid;

WITH stats AS (
    SELECT
        projid,
        nb,
        SUM(nb) OVER (ORDER BY projid) as running_total,
        SUM(nb) OVER () as total_global
    FROM per_proj
),
segments AS (
    SELECT
        projid,
        floor(running_total / (total_global / 16.0)) as bucket
    FROM stats
)
SELECT bucket, min(projid) as start_id, max(projid) as end_id
FROM segments
GROUP BY bucket
ORDER BY bucket;
