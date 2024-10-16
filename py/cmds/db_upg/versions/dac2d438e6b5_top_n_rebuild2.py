"""top_n rebuild2

Revision ID: dac2d438e6b5
Revises: 565015aa8282
Create Date: 2024-10-13 06:27:46.624829

"""

# revision identifiers, used by Alembic.
revision = "dac2d438e6b5"
down_revision = "565015aa8282"

from alembic import op


def upgrade():
    #
    op.execute(
        """
-- Make space in the old table namespace
ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_pkey TO objectsclassifhisto_pkey_old;
-- Foreign-key constraints:
ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_classif_id_fkey TO objectsclassifhisto_classif_id_fkey_old;
ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_classif_who_fkey TO objectsclassifhisto_classif_who_fkey_old;
-- Dropped during obj_head rebuild
-- ALTER TABLE ONLY public.objectsclassifhisto
--     RENAME CONSTRAINT objectsclassifhisto_objid_fkey TO objectsclassifhisto_objid_fkey_old;
ALTER TABLE public.objectsclassifhisto
    RENAME TO objectsclassifhisto_old;

--
-- Based on pg_dump -s -t objectsclassifhisto as of 26 sep 2024
--
CREATE TABLE public.objectsclassifhisto
(
    objid         bigint                      NOT NULL,
    classif_date  timestamp without time zone NOT NULL,
    classif_score double precision,
    classif_id    integer                     NOT NULL,
    classif_who   integer,
    classif_qual  character(1)                NOT NULL
);
ALTER TABLE ONLY public.objectsclassifhisto
    ALTER COLUMN classif_date SET STATISTICS 10000;

INSERT INTO objectsclassifhisto (objid, classif_date, classif_qual, classif_id, classif_who, classif_score)
SELECT objid, classif_date, classif_qual, classif_id, classif_who, classif_score
FROM objectsclassifhisto_old;

ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_pkey PRIMARY KEY (objid, classif_date),
    ADD CONSTRAINT objectsclassifhisto_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES public.taxonomy (id) ON DELETE CASCADE,
    ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users (id),
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;

ALTER TABLE public.objectsclassifhisto
    OWNER TO postgres;
GRANT SELECT ON TABLE public.objectsclassifhisto TO zoo;
GRANT SELECT ON TABLE public.objectsclassifhisto TO readerole;

-- drop table objectsclassifhisto_old
ANALYSE objectsclassifhisto
    """
    )


def downgrade():
    #
    pass
