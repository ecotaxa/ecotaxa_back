"""top_n rebuild1

Revision ID: 565015aa8282
Revises: 067cd670782d
Create Date: 2024-10-13 06:22:56.986138

"""

# revision identifiers, used by Alembic.
revision = "565015aa8282"
down_revision = "067cd670782d"

from alembic import op


def upgrade():
    # ###
    op.execute(
        """
-- Make space in the old table namespace
ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_pkey TO obj_head_pkey_old;
-- Indexes:
ALTER INDEX is_objectsacqclassifqual RENAME TO is_objectsacqclassifqual_old;
ALTER INDEX is_objectsacquisition RENAME TO is_objectsacquisition_old;
ALTER INDEX is_objectsdate RENAME TO is_objectsdate_old;
ALTER INDEX is_objectsdepth RENAME TO is_objectsdepth_old;
ALTER INDEX is_objectslatlong RENAME TO is_objectslatlong_old;
ALTER INDEX is_objectstime RENAME TO is_objectstime_old;
-- Foreign-key constraints:
ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_acquisid_fkey TO obj_head_acquisid_fkey_old;
ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_classif_id_fkey TO obj_head_classif_id_fkey_old;
ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_classif_who_fkey TO obj_head_classif_who_fkey_old;
-- Referenced by:
ALTER TABLE ONLY public.obj_cnn_features
    DROP CONSTRAINT obj_cnn_features_objcnnid_fkey;
ALTER TABLE ONLY public.obj_field
    DROP CONSTRAINT obj_field_objfid_fkey;
ALTER TABLE ONLY public.objectsclassifhisto
    DROP CONSTRAINT objectsclassifhisto_objid_fkey;
ALTER TABLE ONLY public.prediction
    DROP CONSTRAINT prediction_object_id_fkey;
ALTER TABLE ONLY public.prediction_histo
    DROP CONSTRAINT prediction_histo_object_id_fkey;

ALTER TABLE public.obj_head
    RENAME TO obj_head_old;

--
-- Based on pg_dump -s -t obj_head
--

CREATE TABLE public.obj_head
(
    objid              bigint                 NOT NULL,
    acquisid           integer                NOT NULL,
    classif_id         integer,
    objtime            time without time zone,
    latitude           double precision,
    longitude          double precision,
    depth_min          double precision,
    depth_max          double precision,
    objdate            date,
    classif_qual       character(1),
    sunpos             character(1),
    classif_date       timestamp without time zone,
    classif_score      double precision,
    classif_who        integer,
    orig_id            character varying(255) NOT NULL,
    object_link        character varying(255),
    complement_info    character varying
)
    WITH (autovacuum_vacuum_scale_factor = '0.01', fillfactor = '90');
ALTER TABLE ONLY public.obj_head
    ALTER COLUMN acquisid SET STATISTICS 10000;

ALTER TABLE public.obj_head
    OWNER TO postgres;
GRANT SELECT ON TABLE public.obj_head TO zoo;
GRANT SELECT ON TABLE public.obj_head TO readerole;

INSERT INTO public.obj_head(objid, acquisid, classif_id, objtime, latitude, longitude, depth_min, depth_max, objdate,
                            classif_qual, sunpos, classif_date, classif_who, classif_score, orig_id, object_link,
                            complement_info)
SELECT objid,
       acquisid,
       classif_id,
       objtime,
       latitude,
       longitude,
       depth_min,
       depth_max,
       objdate,
       classif_qual,
       sunpos,
       case when classif_qual = 'P' then classif_auto_when else classif_when end,
       classif_who,
       case when classif_qual = 'P' then classif_auto_score end,
       orig_id,
       object_link,
       complement_info
FROM obj_head_old
ORDER BY acquisid, classif_qual;

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_pkey PRIMARY KEY (objid),
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES public.acquisitions (acquisid) ON DELETE CASCADE,
    ADD CONSTRAINT obj_head_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES public.taxonomy (id),
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users (id);

CREATE INDEX is_objectsacqclassifqual ON public.obj_head USING btree (acquisid, classif_qual) INCLUDE (classif_id);
CREATE INDEX is_objectsdate ON public.obj_head USING btree (objdate) INCLUDE (acquisid);
CREATE INDEX is_objectsdepth ON public.obj_head USING btree (depth_max, depth_min) INCLUDE (acquisid);
CREATE INDEX is_objectslatlong ON public.obj_head USING btree (latitude, longitude) INCLUDE (acquisid);
CREATE INDEX is_objectstime ON public.obj_head USING btree (objtime) INCLUDE (acquisid);

ALTER TABLE public.obj_head
    CLUSTER ON is_objectsacqclassifqual;

ALTER TABLE ONLY public.obj_cnn_features
    ADD CONSTRAINT obj_cnn_features_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY public.obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
-- Done later during repack of objectsclassifhisto
-- ALTER TABLE ONLY public.objectsclassifhisto
--     ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY public.prediction
    ADD CONSTRAINT prediction_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY public.prediction_histo
    ADD CONSTRAINT prediction_histo_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.obj_head (objid) ON DELETE CASCADE;

CREATE STATISTICS obj_head_score_if_p ON classif_qual, classif_score FROM obj_head;
CREATE STATISTICS obj_head_user_if_v_d ON classif_qual, classif_who FROM obj_head;
CREATE STATISTICS obj_head_classif_if_qual ON classif_qual, classif_id FROM obj_head;

ANALYSE obj_head
    """
    )
    op.execute(
        """
    create or replace view objects as 
       select sam.projid, sam.sampleid, obh.objid, obh.latitude, obh.longitude,
              obh.objdate, obh.objtime, obh.depth_min, obh.depth_max,
              obh.classif_id, obh.classif_qual, obh.classif_who, 
              CASE WHEN obh.classif_qual in ('V', 'D') THEN obh.classif_date END AS classif_when,
              obh.classif_score AS classif_auto_score,
              CASE WHEN obh.classif_qual = 'P' THEN obh.classif_date END AS classif_auto_when,
              CASE WHEN obh.classif_qual = 'P' THEN obh.classif_id END AS classif_auto_id,
              NULL::integer AS classif_crossvalidation_id,
              obh.complement_info,
              NULL::double precision AS similarity,
              obh.sunpos,
              HASHTEXT(obh.orig_id) AS random_value,
              obh.acquisid, obh.object_link, obh.orig_id, obh.acquisid AS processid, 
              ofi.*
         from obj_head obh
         join acquisitions acq on obh.acquisid = acq.acquisid
         join samples sam on acq.acq_sample_id = sam.sampleid 
         left join obj_field ofi on obh.objid = ofi.objfid -- allow elimination by planner        """
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
