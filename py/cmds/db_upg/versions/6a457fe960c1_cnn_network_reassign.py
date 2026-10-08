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
-- SQL port of the "match by instrument" rules of new_cnns_for_ecotaxa.R, applied only to the projects
-- without CNN network (NULL or blank cnn_network_id) as they are in the DB at upgrade time.
-- Projects with a network keep it, and their CNN features, untouched.
-- Using the networks really available (MODELSAREA) and the instrument "clear" network, i.e. the only
-- available network whose name starts with the instrument id (case and punctuation apart), a project gets:
--  - the network chosen by the R rules, if available;
--  - else the clear network, if any;
--  - else nothing, it stays without network.
-- Every change is logged in projects_cnn_reassign_log (kept for audit/downgrade, to drop later).
CREATE TABLE projects_cnn_reassign_log (
    projid INTEGER NOT NULL PRIMARY KEY,
    instrument_id VARCHAR(32),
    old_cnn_network_id VARCHAR(50),
    r_cnn_network_id VARCHAR(50),
    new_cnn_network_id VARCHAR(50)
);

INSERT INTO projects_cnn_reassign_log (projid, instrument_id, old_cnn_network_id, r_cnn_network_id,
                                       new_cnn_network_id)
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
                    cnn_network_id AS old_cnn
               FROM projects
              WHERE NULLIF(btrim(cnn_network_id), '') IS NULL),
     r AS (SELECT prj.*,
                  CASE instrument_id
                      -- match by instrument
                      WHEN 'FlowCam' THEN 'flowcam'
                      WHEN 'IFCB' THEN 'ifcb'
                      WHEN 'ISIIS' THEN 'isiis'
                      WHEN 'PlanktoScope' THEN 'planktoscope_2022-09'
                      WHEN 'UVP5HD' THEN 'UVP5HD-2024-01'
                      WHEN 'UVP5SD' THEN 'UVP5SD-2024-01'
                      WHEN 'UVP6' THEN 'uvp6_beta_2022-01-26'
                      WHEN 'ZooCam' THEN 'zoocam_2022-04-06'
                      WHEN 'Zooscan' THEN 'zooscan'
                      END AS r_cnn
             FROM prj),
     new AS (SELECT r.*,
                    CASE
                        -- R choice available
                        WHEN r_cnn IN (SELECT network FROM avail) THEN r_cnn
                        -- else the clear one, if any
                        ELSE clear.network
                        END AS new_cnn
               FROM r
               LEFT JOIN clear ON clear.instrument_id = r.instrument_id)
SELECT projid,
       instrument_id,
       old_cnn,
       r_cnn,
       new_cnn
  FROM new
 WHERE new_cnn IS NOT NULL;

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
