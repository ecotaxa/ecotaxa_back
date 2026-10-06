"""organizations ror

Revision ID: af45d71653e4
Revises: 890a5b01ab64
Create Date: 2026-09-30 11:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "af45d71653e4"
down_revision = "890a5b01ab64"

import re
from typing import List

from alembic import op

# Plain SQL only, so that offline mode (`alembic upgrade --sql`, QA/py/pg_files/upgrade_prod.sql)
# produces exactly what online mode runs. ROR ids are embedded, taken once from the reviewed
# edmo_matches.xlsx ("id_ror" column).
UPGRADE_SQL = r"""
-- ROR (https://ror.org/) references of organizations, from the "id_ror" column of the reviewed
-- edmo_matches.xlsx, added to "directories" as "ror:<id>", other directories kept.
-- Organizations merged by the EDMO normalisation (organizations_edmo_log) give their ROR to the survivor.
-- Traceability & downgrade: organizations_ror_log. Drop it once validated.

CREATE TEMP TABLE ror_match
(
    eco_id   INTEGER NOT NULL,
    eco_name VARCHAR NOT NULL,
    ror_id   VARCHAR NOT NULL
) ON COMMIT DROP;

INSERT INTO ror_match (eco_id, eco_name, ror_id)
VALUES
        (1, 'University of Ss Cyril and Methodius in Trnava Slovakia', '04xdyq509'),
        (24, 'Universidad de Las Palmas de Gran Canaria', '01teme464'),
        (36, 'Autonomous Baja California Sur University - UABCS', '05xwcq167'),
        (51, 'Max Delbrück Center for Molecular Medicine', '04p5ggc03'),
        (62, 'Bayerische Landesanstalt für Landwirtschaft Institut für Fischerei - LFL - IFI', '01grm4y17'),
        (75, 'South African Association for Marine Biological Research', '00wdk8w52'),
        (94, 'Shenzhen Institutes of Advanced Technology - SIAT', '04gh4er46'),
        (119, 'Universidade Federal do Paraná (UFPR)', '05syd6y78'),
        (128, 'Galway-Mayo Institute of Technology (GMIT)', '036501p19'),
        (146, 'Sanibel Captiva Conservation Foundation', '010tc4s75'),
        (175, 'Instituto de investigacion y formacion Agraria y Pesquera de Andalucia', '02w21g732'),
        (187, 'Research Centre for Experimental Marine Biology & Biotechnology University of the Basque Country', '000xsnr85'),
        (215, 'National Higher School of Advanced Techniques - ENSTA', '01m9r8618'),
        (222, 'St. Mary''s College of Maryland', '01y2d1w05'),
        (223, 'The University of the West Indies, St. Augustine, Trinidad and Tobago', '03fkc8c64'),
        (236, 'Andalusia Fisheries and Agriculture Research and Training Institute IFAPA', '02w21g732'),
        (340, 'Training and Research Centre on Mediterranean Environments - CEFREM', '01jt5ms28'),
        (359, 'Bauhaus-Universität Weimar', '033bb5z47'),
        (370, 'Gangneung-Wonju National University', '0461cvh40'),
        (389, 'Instituto Politécnico de Setúbal/Instituto Português do Mar e Atmosfera', '01bvjz807'),
        (389, 'Instituto Politécnico de Setúbal/Instituto Português do Mar e Atmosfera', '01sp7nd78'),
        (429, 'NORTHEASTERN REGIONAL ASSOCIATION OF COASTAL OCEAN OBSERVING SYSTEMS', '05ackpy69'),
        (434, 'Instituto de Estudos do Mar Almirante Paulo Moreira', '0033xm087'),
        (476, 'Consejo Nacional de Investigaciones Científicas y Técnicas', '03cqe8w59'),
        (490, 'Zagreb University - BIOL - PMF', '00mv6sv71'),
        (553, 'Marine Discovery Center, New Smyrna Beach, FL', '01h90nm51'),
        (597, 'Centre National des Sciences et de Medecine Vétérinaire de Dalaba-Rép. de Guinée', '02tpmfk70'),
        (599, 'Insular Research Centre and Environment Observatory - CRIOBE', '02tp7mm44'),
        (671, 'East Anglia University - British Antarctic Survey - BAS', '01rhff309'),
        (683, 'Technische Hochschule Mittelhessen', '02qdc9985'),
        (786, 'Institute of Hydrobiology, Biology Centre, Czech Academy of Sciences', '05pq4yn02'),
        (815, 'California Polytechnic State University San Luis Obispo', '001gpfp45'),
        (845, 'Centro Interdisciplinario de Ciencias Marinas (CICIMAR)', '01txgmm25'),
        (847, 'Swiss Federal Institute of Aquatic Science and Technology - EAWAG', '00pc48d59');

CREATE TABLE organizations_ror_log AS
SELECT org.id                                                        AS org_id,
       org.directories                                               AS old_directories,
       concat_ws(',',
                 nullif(btrim(org.directories), ''),
                 string_agg(DISTINCT 'ror:' || res.ror_id, ',')) AS new_directories
  FROM organizations org
  JOIN (SELECT DISTINCT coalesce(lgg.merged_into, mat.eco_id) AS org_id, mat.ror_id
          FROM ror_match mat
          LEFT JOIN organizations_edmo_log lgg ON lgg.org_id = mat.eco_id AND lgg.action = 'merge') res
       ON res.org_id = org.id
 WHERE NOT ('ror:' || res.ror_id = ANY (string_to_array(replace(coalesce(org.directories, ''), ' ', ''), ',')))
 GROUP BY org.id, org.directories;

UPDATE organizations org
   SET directories = lgg.new_directories
  FROM organizations_ror_log lgg
 WHERE org.id = lgg.org_id;
"""

DOWNGRADE_SQL = r"""
-- Remove the ROR references added by the upgrade, unless the directories were changed since.
UPDATE organizations org
   SET directories = lgg.old_directories
  FROM organizations_ror_log lgg
 WHERE org.id = lgg.org_id
   AND org.directories = lgg.new_directories;

DROP TABLE organizations_ror_log;
"""


def _statements(sql: str) -> List[str]:
    """Statements are separated by a blank line after their ';'"""
    return [
        a_stmt.strip().rstrip(";")
        for a_stmt in re.split(r";\n\s*\n", sql.strip() + "\n\n")
        if a_stmt.strip()
    ]


def upgrade():
    for a_stmt in _statements(UPGRADE_SQL):
        op.execute(a_stmt)


def downgrade():
    for a_stmt in _statements(DOWNGRADE_SQL):
        op.execute(a_stmt)
