"""cnn network reassign

Revision ID: 6a457fe960c1
Revises: c593af18f13a
Create Date: 2026-10-07 16:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "6a457fe960c1"
down_revision = "c593af18f13a"

from typing import List

from alembic import op

from FS.MachineLearningModels import SavedModels
from helpers.AppConfig import Config

# Plain SQL only, so that offline mode (`alembic upgrade --sql`, QA/py/pg_files/upgrade_prod.sql)
# produces exactly what online mode runs. The available networks (MODELSAREA directory) are
# read when the SQL is produced.
UPGRADE_SQL = r"""
-- SQL port of new_cnns_for_ecotaxa.R, on the projects as they are in the DB at upgrade time.
-- Two fixes vs the R script:
--  - an empty cnn_network_id ('') is a missing one (R only saw NA as it read a CSV), so it gets a suggestion;
--  - 'zoocam', which does not exist, is really replaced by 'zoocam_2022-04-06' (in R the fix had no effect).
-- Then, using the networks really available (MODELSAREA) and the instrument "clear" network, i.e. the only
-- available network whose name starts with the instrument id (case and punctuation apart):
--  - a network chosen by the R rules but not available is not assigned: the clear network is, if any,
--    else the project keeps its current network;
--  - a project left without network gets the clear network, if any.
-- Every change is logged in projects_cnn_reassign_log (kept for audit/downgrade, to drop later).
CREATE TABLE projects_cnn_reassign_log (
    projid INTEGER NOT NULL PRIMARY KEY,
    instrument_id VARCHAR(32),
    old_cnn_network_id VARCHAR(50),
    r_cnn_network_id VARCHAR(50),
    new_cnn_network_id VARCHAR(50),
    erase_features BOOLEAN NOT NULL
);

INSERT INTO projects_cnn_reassign_log (projid, instrument_id, old_cnn_network_id, r_cnn_network_id,
                                       new_cnn_network_id, erase_features)
WITH avail(network) AS (VALUES {available}),
     clear AS (SELECT ins.instrument_id, min(avail.network) AS network
                 FROM instrument ins
                 JOIN avail
                   ON lower(regexp_replace(avail.network, '[^a-zA-Z0-9]', '', 'g'))
                          LIKE lower(regexp_replace(ins.instrument_id, '[^a-zA-Z0-9]', '', 'g')) || '%'
                WHERE regexp_replace(ins.instrument_id, '[^a-zA-Z0-9]', '', 'g') <> ''
                GROUP BY ins.instrument_id
               HAVING count(*) = 1),
     prj AS (SELECT projid,
                    instrument_id,
                    cnn_network_id                       AS old_cnn,
                    NULLIF(btrim(cnn_network_id), '')    AS cnn
               FROM projects),
     sug AS (SELECT prj.*,
                    CASE
                        -- fix mistakes
                        WHEN cnn = 'zoocam' THEN 'zoocam_2022-04-06'
                        WHEN cnn = 'LOKI_2022-05-17' THEN NULL
                        -- match by instrument
                        WHEN instrument_id = 'FlowCam' THEN 'flowcam'
                        WHEN instrument_id = 'IFCB' THEN 'ifcb'
                        WHEN instrument_id = 'ISIIS' THEN 'isiis'
                        WHEN instrument_id = 'PlanktoScope' THEN 'planktoscope_2022-09'
                        WHEN instrument_id = 'UVP5HD' THEN 'UVP5HD-2024-01'
                        WHEN instrument_id = 'UVP5SD' THEN 'UVP5SD-2024-01'
                        WHEN instrument_id = 'UVP6' THEN 'uvp6_beta_2022-01-26'
                        WHEN instrument_id = 'ZooCam' THEN 'zoocam_2022-04-06'
                        WHEN instrument_id = 'Zooscan' THEN 'zooscan'
                        END AS suggested_cnn
               FROM prj),
     r AS (SELECT sug.*,
                  CASE
                      -- replace
                      WHEN cnn IN ('uvp5ccelter_group1', 'uvp5ccelter_group2') THEN suggested_cnn
                      WHEN cnn = 'LOKI_2022-05-17' THEN NULL
                      WHEN cnn = 'zoocam' THEN suggested_cnn
                      -- keep current selection when it is made
                      WHEN cnn IS NOT NULL THEN cnn
                      ELSE suggested_cnn
                      END AS r_cnn
             FROM sug),
     new AS (SELECT r.*,
                    CASE
                        -- unchanged
                        WHEN r_cnn = cnn THEN cnn
                        -- R choice available
                        WHEN r_cnn IN (SELECT network FROM avail) THEN r_cnn
                        -- R choice not available: the clear one, else no change
                        WHEN r_cnn IS NOT NULL THEN COALESCE(clear.network, cnn)
                        -- no network: the clear one, if any
                        ELSE clear.network
                        END AS new_cnn
               FROM r
               LEFT JOIN clear ON clear.instrument_id = r.instrument_id)
SELECT projid,
       instrument_id,
       old_cnn,
       r_cnn,
       new_cnn,
       (cnn IS NOT NULL AND (new_cnn IS NULL OR new_cnn <> cnn)) AS erase_features
  FROM new
 WHERE new_cnn IS DISTINCT FROM cnn;

-- CNN features depend on the CNN network: delete them where it changes, as the app does
-- (BO.Prediction.DeepFeatures.delete_all). They are recomputed by the next prediction using deep features.
DO
$$
    DECLARE
        prj RECORD;
    BEGIN
        FOR prj IN SELECT projid FROM projects_cnn_reassign_log WHERE erase_features ORDER BY projid
            LOOP
                DELETE FROM obj_cnn_features_vector WHERE objcnnid <@ obj_in_prj(prj.projid);
            END LOOP;
    END
$$;

UPDATE projects prj
   SET cnn_network_id = log.new_cnn_network_id
  FROM projects_cnn_reassign_log log
 WHERE prj.projid = log.projid;
"""

DOWNGRADE_SQL = r"""
-- CNN network ids are restored, deleted CNN features are not (recomputed by predictions).
UPDATE projects prj
   SET cnn_network_id = log.old_cnn_network_id
  FROM projects_cnn_reassign_log log
 WHERE prj.projid = log.projid;

DROP TABLE projects_cnn_reassign_log;
"""


def upgrade_sql(networks: List[str]) -> str:
    """The upgrade SQL, for the given available networks."""
    assert len(networks) > 0, "No CNN network found in MODELSAREA, cannot reassign."
    available = ", ".join(
        "('%s')" % a_network.replace("'", "''") for a_network in sorted(networks)
    )
    # str.replace and not format(), the SQL has braces in it
    return UPGRADE_SQL.replace("{available}", available)


def upgrade():
    op.execute(upgrade_sql(SavedModels(Config()).list()))


def downgrade():
    op.execute(DOWNGRADE_SQL)
