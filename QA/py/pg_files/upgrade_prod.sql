
-- Table: public.user_preferences

-- DROP TABLE public.user_preferences;

CREATE TABLE public.user_preferences
(
    user_id integer NOT NULL,
    project_id integer NOT NULL,
    json_prefs character varying(4096) NOT NULL COLLATE pg_catalog."default",
    CONSTRAINT user_preferences_pkey PRIMARY KEY (user_id, project_id),
    CONSTRAINT user_preferences_project_id_fkey FOREIGN KEY (project_id)
        REFERENCES public.projects (projid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT user_preferences_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.user_preferences
    OWNER to postgres;

-- Table: public.worms

-- DROP TABLE public.worms;

CREATE TABLE public.worms
(
    aphia_id integer NOT NULL,
    url character varying(255) COLLATE pg_catalog."default",
    scientificname character varying(128) COLLATE pg_catalog."default",
    authority character varying(255) COLLATE pg_catalog."default",
    status character varying(24) COLLATE pg_catalog."default",
    unacceptreason character varying(150) COLLATE pg_catalog."default",
    taxon_rank_id smallint,
    rank character varying(18) COLLATE pg_catalog."default",
    valid_aphia_id integer,
    valid_name character varying(128) COLLATE pg_catalog."default",
    valid_authority character varying(128) COLLATE pg_catalog."default",
    parent_name_usage_id integer,
    kingdom character varying(128) COLLATE pg_catalog."default",
    phylum character varying(129) COLLATE pg_catalog."default",
    class_ character varying(130) COLLATE pg_catalog."default",
    "order" character varying(131) COLLATE pg_catalog."default",
    family character varying(132) COLLATE pg_catalog."default",
    genus character varying(133) COLLATE pg_catalog."default",
    citation character varying(1024) COLLATE pg_catalog."default",
    lsid character varying(257) COLLATE pg_catalog."default",
    is_marine boolean,
    is_brackish boolean,
    is_freshwater boolean,
    is_terrestrial boolean,
    is_extinct boolean,
    match_type character varying(16) COLLATE pg_catalog."default" NOT NULL,
    modified timestamp without time zone,
    all_fetched boolean,
    CONSTRAINT worms_pkey PRIMARY KEY (aphia_id)
)

TABLESPACE pg_default;

ALTER TABLE public.worms
    OWNER to postgres;

ALTER TABLE public.projects
    ADD COLUMN license character varying(16) COLLATE pg_catalog."default" NOT NULL DEFAULT 'Copyright'::character varying;

-- oceanomics/ecotaxa_dev#503

ALTER TABLE public.samples ALTER COLUMN sampleid SET DATA TYPE integer;
ALTER TABLE public.acquisitions ALTER COLUMN acquisid SET DATA TYPE integer;
ALTER TABLE public.process ALTER COLUMN processid SET DATA TYPE integer;

-- oceanomics/ecotaxa_dev#519


CREATE SEQUENCE public.collection_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.collection_id_seq
    OWNER TO postgres;

-- Table: public.collection

-- DROP TABLE public.collection;

CREATE TABLE public.collection
(
    id integer NOT NULL DEFAULT nextval('collection_id_seq'::regclass),
    title character varying COLLATE pg_catalog."default" NOT NULL,
    provider_user_id integer,
    contact_user_id integer,
    citation character varying COLLATE pg_catalog."default",
    license character varying(16) COLLATE pg_catalog."default",
    abstract character varying COLLATE pg_catalog."default",
    description character varying COLLATE pg_catalog."default",
    CONSTRAINT collection_pkey PRIMARY KEY (id),
    CONSTRAINT collection_contact_user_id_fkey FOREIGN KEY (contact_user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.collection
    OWNER to postgres;

-- Index: CollectionTitle

-- DROP INDEX public."CollectionTitle";

CREATE UNIQUE INDEX "CollectionTitle"
    ON public.collection USING btree
    (title COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

-- Table: public.collection_project

-- DROP TABLE public.collection_project;

CREATE TABLE public.collection_project
(
    collection_id integer NOT NULL,
    project_id integer NOT NULL,
    CONSTRAINT collection_project_pkey PRIMARY KEY (collection_id, project_id),
    CONSTRAINT collection_project_collection_id_fkey FOREIGN KEY (collection_id)
        REFERENCES public.collection (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT collection_project_project_id_fkey FOREIGN KEY (project_id)
        REFERENCES public.projects (projid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.collection_project
    OWNER to postgres;

-- Table: public.collection_user_role

-- DROP TABLE public.collection_user_role;

CREATE TABLE public.collection_user_role
(
    collection_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(1) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT collection_user_role_pkey PRIMARY KEY (collection_id, user_id, role),
    CONSTRAINT collection_user_role_collection_id_fkey FOREIGN KEY (collection_id)
        REFERENCES public.collection (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT collection_user_role_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.collection_user_role
    OWNER to postgres;

-- Table: public.collection_orga_role

-- DROP TABLE public.collection_orga_role;

CREATE TABLE public.collection_orga_role
(
    collection_id integer NOT NULL,
    organisation character varying(255) COLLATE pg_catalog."default" NOT NULL,
    role character varying(1) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT collection_orga_role_pkey PRIMARY KEY (collection_id, organisation, role),
    CONSTRAINT collection_orga_role_collection_id_fkey FOREIGN KEY (collection_id)
        REFERENCES public.collection (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.collection_orga_role
    OWNER to postgres;

INSERT INTO public.alembic_version(version_num) VALUES ('15cad3c0948e');

-- Generating line:
-- ecotaxa_front$ python manage.py db upgrade --sql 36bb704b9fc5:4bb7276e86de >> ../ecotaxa_back/QA/py/pg_files/upgrade_prod.sql
BEGIN;

-- Running upgrade 36bb704b9fc5 -> 4bb7276e86de

ALTER TABLE obj_head ALTER COLUMN acquisid SET NOT NULL;

ALTER TABLE obj_head ALTER COLUMN sampleid SET NOT NULL;

ALTER TABLE obj_head ALTER COLUMN processid SET NOT NULL;

UPDATE alembic_version SET version_num='4bb7276e86de' WHERE alembic_version.version_num = '36bb704b9fc5';

COMMIT;

BEGIN;

-- Running upgrade 4bb7276e86de -> cee3a33476db

begin;

create temp table obj_paths as
select distinct projid, sampleid, acquisid, processid
  from obj_head;
create unique index obj_paths$i on obj_paths(projid, sampleid, acquisid, processid);

update acquisitions acq set orig_id = '__DUMMY_ID2__'||sam.sampleid||'__'
  from samples sam
 where acq.orig_id is null
   and exists (select 1 from obj_paths oph
                where oph.projid = acq.projid
                  and oph.sampleid = sam.sampleid
                  and oph.acquisid = acq.acquisid);

update samples sam set orig_id = '__DUMMY_ID2__'||prj.projid||'__'
  from projects prj
 where sam.orig_id is null
   and exists (select 1 from obj_paths oph
                where oph.projid = sam.projid
                  and oph.sampleid = sam.sampleid);

drop table obj_paths;

commit;

ALTER TABLE acquisitions ALTER COLUMN orig_id SET NOT NULL;

ALTER TABLE obj_field ALTER COLUMN orig_id SET NOT NULL;

ALTER TABLE process ALTER COLUMN orig_id SET NOT NULL;

ALTER TABLE samples ALTER COLUMN orig_id SET NOT NULL;

UPDATE alembic_version SET version_num='cee3a33476db' WHERE alembic_version.version_num = '4bb7276e86de';

-- Running upgrade cee3a33476db -> 63d8b0d2196a

begin;
create temp table sample_remap
as select sam.sampleid as dst_id, array_agg(sam2.sampleid) as src_id from samples sam
 join samples sam2 on sam2.sampleid > sam.sampleid
                   and sam2.orig_id = sam.orig_id
                   and sam2.projid = sam.projid
                   -- (re) computed columns
                   -- and (sam2.latitude = sam.latitude or (sam2.latitude is null and sam.latitude is null))
                   -- and (sam2.longitude = sam.longitude or (sam2.longitude is null and sam.longitude is null))
                   and (sam2.dataportal_descriptor = sam.dataportal_descriptor or
                   (sam2.dataportal_descriptor is null and sam.dataportal_descriptor is null))
                   and (sam2.t01 = sam.t01 or (sam2.t01 is null and sam.t01 is null))
                   and (sam2.t02 = sam.t02 or (sam2.t02 is null and sam.t02 is null))
                   and (sam2.t03 = sam.t03 or (sam2.t03 is null and sam.t03 is null))
                   and (sam2.t04 = sam.t04 or (sam2.t04 is null and sam.t04 is null))
                   and (sam2.t05 = sam.t05 or (sam2.t05 is null and sam.t05 is null))
                   and (sam2.t06 = sam.t06 or (sam2.t06 is null and sam.t06 is null))
                   and (sam2.t07 = sam.t07 or (sam2.t07 is null and sam.t07 is null))
                   and (sam2.t08 = sam.t08 or (sam2.t08 is null and sam.t08 is null))
                   and (sam2.t09 = sam.t09 or (sam2.t09 is null and sam.t09 is null))
                   and (sam2.t10 = sam.t10 or (sam2.t10 is null and sam.t10 is null))
                   and (sam2.t11 = sam.t11 or (sam2.t11 is null and sam.t11 is null))
                   and (sam2.t12 = sam.t12 or (sam2.t12 is null and sam.t12 is null))
                   and (sam2.t13 = sam.t13 or (sam2.t13 is null and sam.t13 is null))
                   and (sam2.t14 = sam.t14 or (sam2.t14 is null and sam.t14 is null))
                   and (sam2.t15 = sam.t15 or (sam2.t15 is null and sam.t15 is null))
                   and (sam2.t16 = sam.t16 or (sam2.t16 is null and sam.t16 is null))
                   and (sam2.t17 = sam.t17 or (sam2.t17 is null and sam.t17 is null))
                   and (sam2.t18 = sam.t18 or (sam2.t18 is null and sam.t18 is null))
                   and (sam2.t19 = sam.t19 or (sam2.t19 is null and sam.t19 is null))
                   and (sam2.t20 = sam.t20 or (sam2.t20 is null and sam.t20 is null))
                   and (sam2.t21 = sam.t21 or (sam2.t21 is null and sam.t21 is null))
                   and (sam2.t22 = sam.t22 or (sam2.t22 is null and sam.t22 is null))
                   and (sam2.t23 = sam.t23 or (sam2.t23 is null and sam.t23 is null))
                   and (sam2.t24 = sam.t24 or (sam2.t24 is null and sam.t24 is null))
                   and (sam2.t25 = sam.t25 or (sam2.t25 is null and sam.t25 is null))
                   and (sam2.t26 = sam.t26 or (sam2.t26 is null and sam.t26 is null))
                   and (sam2.t27 = sam.t27 or (sam2.t27 is null and sam.t27 is null))
                   and (sam2.t28 = sam.t28 or (sam2.t28 is null and sam.t28 is null))
                   and (sam2.t29 = sam.t29 or (sam2.t29 is null and sam.t29 is null))
                   and (sam2.t30 = sam.t30 or (sam2.t30 is null and sam.t30 is null))
group by sam.sampleid;

update obj_head set sampleid = dst_id
  from sample_remap rmp
 where sampleid = any(src_id);

delete from samples
 using sample_remap rmp
 where sampleid = any(rmp.src_id);
commit;

begin;
create temp table acquis_remap
as
select acq.acquisid as dst_id, array_agg(acq2.acquisid) as src_id from acquisitions acq
 join acquisitions acq2 on acq2.acquisid > acq.acquisid
                   and acq2.projid = acq.projid
                   and acq2.orig_id = acq.orig_id
                   and (acq2.instrument = acq.instrument or (acq2.instrument is null and acq.instrument is null))
                   and (acq2.t01 = acq.t01 or (acq2.t01 is null and acq.t01 is null))
                   and (acq2.t02 = acq.t02 or (acq2.t02 is null and acq.t02 is null))
                   and (acq2.t03 = acq.t03 or (acq2.t03 is null and acq.t03 is null))
                   and (acq2.t04 = acq.t04 or (acq2.t04 is null and acq.t04 is null))
                   and (acq2.t05 = acq.t05 or (acq2.t05 is null and acq.t05 is null))
                   and (acq2.t06 = acq.t06 or (acq2.t06 is null and acq.t06 is null))
                   and (acq2.t07 = acq.t07 or (acq2.t07 is null and acq.t07 is null))
                   and (acq2.t08 = acq.t08 or (acq2.t08 is null and acq.t08 is null))
                   and (acq2.t09 = acq.t09 or (acq2.t09 is null and acq.t09 is null))
                   and (acq2.t10 = acq.t10 or (acq2.t10 is null and acq.t10 is null))
                   and (acq2.t11 = acq.t11 or (acq2.t11 is null and acq.t11 is null))
                   and (acq2.t12 = acq.t12 or (acq2.t12 is null and acq.t12 is null))
                   and (acq2.t13 = acq.t13 or (acq2.t13 is null and acq.t13 is null))
                   and (acq2.t14 = acq.t14 or (acq2.t14 is null and acq.t14 is null))
                   and (acq2.t15 = acq.t15 or (acq2.t15 is null and acq.t15 is null))
                   and (acq2.t16 = acq.t16 or (acq2.t16 is null and acq.t16 is null))
                   and (acq2.t17 = acq.t17 or (acq2.t17 is null and acq.t17 is null))
                   and (acq2.t18 = acq.t18 or (acq2.t18 is null and acq.t18 is null))
                   and (acq2.t19 = acq.t19 or (acq2.t19 is null and acq.t19 is null))
                   and (acq2.t20 = acq.t20 or (acq2.t20 is null and acq.t20 is null))
                   and (acq2.t21 = acq.t21 or (acq2.t21 is null and acq.t21 is null))
                   and (acq2.t22 = acq.t22 or (acq2.t22 is null and acq.t22 is null))
                   and (acq2.t23 = acq.t23 or (acq2.t23 is null and acq.t23 is null))
                   and (acq2.t24 = acq.t24 or (acq2.t24 is null and acq.t24 is null))
                   and (acq2.t25 = acq.t25 or (acq2.t25 is null and acq.t25 is null))
                   and (acq2.t26 = acq.t26 or (acq2.t26 is null and acq.t26 is null))
                   and (acq2.t27 = acq.t27 or (acq2.t27 is null and acq.t27 is null))
                   and (acq2.t28 = acq.t28 or (acq2.t28 is null and acq.t28 is null))
                   and (acq2.t29 = acq.t29 or (acq2.t29 is null and acq.t29 is null))
                   and (acq2.t30 = acq.t30 or (acq2.t30 is null and acq.t30 is null))
group by acq.acquisid;

update obj_head set acquisid = dst_id
  from acquis_remap rmp
 where acquisid = any(src_id);

delete from acquisitions
 using acquis_remap rmp
 where acquisid = any(rmp.src_id);
commit;

begin;
create temp table process_remap
as select prc.processid as dst_id, array_agg(prc2.processid) as src_id from process prc
 join process prc2 on prc2.processid > prc.processid
                   and prc2.projid = prc.projid
                   and prc2.orig_id = prc.orig_id
                   and (prc2.t01 = prc.t01 or (prc2.t01 is null and prc.t01 is null))
                   and (prc2.t02 = prc.t02 or (prc2.t02 is null and prc.t02 is null))
                   and (prc2.t03 = prc.t03 or (prc2.t03 is null and prc.t03 is null))
                   and (prc2.t04 = prc.t04 or (prc2.t04 is null and prc.t04 is null))
                   and (prc2.t05 = prc.t05 or (prc2.t05 is null and prc.t05 is null))
                   and (prc2.t06 = prc.t06 or (prc2.t06 is null and prc.t06 is null))
                   and (prc2.t07 = prc.t07 or (prc2.t07 is null and prc.t07 is null))
                   and (prc2.t08 = prc.t08 or (prc2.t08 is null and prc.t08 is null))
                   and (prc2.t09 = prc.t09 or (prc2.t09 is null and prc.t09 is null))
                   and (prc2.t10 = prc.t10 or (prc2.t10 is null and prc.t10 is null))
                   and (prc2.t11 = prc.t11 or (prc2.t11 is null and prc.t11 is null))
                   and (prc2.t12 = prc.t12 or (prc2.t12 is null and prc.t12 is null))
                   and (prc2.t13 = prc.t13 or (prc2.t13 is null and prc.t13 is null))
                   and (prc2.t14 = prc.t14 or (prc2.t14 is null and prc.t14 is null))
                   and (prc2.t15 = prc.t15 or (prc2.t15 is null and prc.t15 is null))
                   and (prc2.t16 = prc.t16 or (prc2.t16 is null and prc.t16 is null))
                   and (prc2.t17 = prc.t17 or (prc2.t17 is null and prc.t17 is null))
                   and (prc2.t18 = prc.t18 or (prc2.t18 is null and prc.t18 is null))
                   and (prc2.t19 = prc.t19 or (prc2.t19 is null and prc.t19 is null))
                   and (prc2.t20 = prc.t20 or (prc2.t20 is null and prc.t20 is null))
                   and (prc2.t21 = prc.t21 or (prc2.t21 is null and prc.t21 is null))
                   and (prc2.t22 = prc.t22 or (prc2.t22 is null and prc.t22 is null))
                   and (prc2.t23 = prc.t23 or (prc2.t23 is null and prc.t23 is null))
                   and (prc2.t24 = prc.t24 or (prc2.t24 is null and prc.t24 is null))
                   and (prc2.t25 = prc.t25 or (prc2.t25 is null and prc.t25 is null))
                   and (prc2.t26 = prc.t26 or (prc2.t26 is null and prc.t26 is null))
                   and (prc2.t27 = prc.t27 or (prc2.t27 is null and prc.t27 is null))
                   and (prc2.t28 = prc.t28 or (prc2.t28 is null and prc.t28 is null))
                   and (prc2.t29 = prc.t29 or (prc2.t29 is null and prc.t29 is null))
                   and (prc2.t30 = prc.t30 or (prc2.t30 is null and prc.t30 is null))
group by prc.processid;

update obj_head set processid = dst_id
  from process_remap rmp
 where processid = any(src_id);

delete from process
 using process_remap rmp
 where processid = any(rmp.src_id);
commit;

begin;
update samples sam
   set orig_id = orig_id || '_:' || (select count(1) from samples sam2
                                      where sam2.projid = sam.projid
                                        and sam2.orig_id = sam.orig_id
                                        and sam2.sampleid < sam.sampleid)
 where exists (select 1 from samples sam2
               where sam2.projid = sam.projid
                 and sam2.orig_id = sam.orig_id
                 and sam2.sampleid < sam.sampleid );

update acquisitions acq
   set orig_id = orig_id || '_:' || (select count(1) from acquisitions acq2
                                      where acq2.projid = acq.projid
                                        and acq2.orig_id = acq.orig_id
                                        and acq2.acquisid < acq.acquisid)
 where exists (select 1 from acquisitions acq2
               where acq2.projid = acq.projid
                 and acq2.orig_id = acq.orig_id
                 and acq2.acquisid < acq.acquisid );
commit;

CREATE UNIQUE INDEX "IS_AcquisitionsProjectOrigId" ON acquisitions (projid, orig_id);

DROP INDEX "IS_AcquisitionsProject";

CREATE UNIQUE INDEX "IS_SamplesProjectOrigId" ON samples (projid, orig_id);

DROP INDEX "IS_SamplesProject";

UPDATE alembic_version SET version_num='63d8b0d2196a' WHERE alembic_version.version_num = 'cee3a33476db';

COMMIT;

BEGIN;

BEGIN;

-- Running upgrade 63d8b0d2196a -> d3309bb7012e

begin;
delete from acquisitions
where acquisid in (
    select acquisid from acquisitions
    except
    select acquisid from obj_head
);

delete from process
where processid in (
    select processid from process
    except
    select processid from obj_head
);
commit;

begin;
create temp table tmp_acq_proc
as select distinct acquisid, processid, null::integer as acquisid_to, null::integer as processid_to from obj_head;
create unique index tmp_acq_proc$ap on tmp_acq_proc(acquisid, processid);
create unique index tmp_acq_proc$pa on tmp_acq_proc(processid, acquisid);

-- Create one new process per _extra_ acquisition in group
with procs_with_several_acqs as (select processid, min(acquisid) as min_acquisid
                                   from tmp_acq_proc
                                  group by processid
                                 having count(1) > 1)
update tmp_acq_proc tap
   set processid_to = nextval('seq_process')
  from procs_with_several_acqs pwsa
 where tap.processid = pwsa.processid
   and tap.acquisid > pwsa.min_acquisid;

insert into process (processid, projid, orig_id,
                     t01, t02, t03, t04, t05, t06, t07, t08, t09, t10,
                     t11, t12, t13, t14, t15, t16, t17, t18, t19, t20,
                     t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select tap.processid_to, prc.projid, prc.orig_id,
       prc.t01, prc.t02, prc.t03, prc.t04, prc.t05, prc.t06, prc.t07, prc.t08, prc.t09, prc.t10,
       prc.t11, prc.t12, prc.t13, prc.t14, prc.t15, prc.t16, prc.t17, prc.t18, prc.t19, prc.t20,
       prc.t21, prc.t22, prc.t23, prc.t24, prc.t25, prc.t26, prc.t27, prc.t28, prc.t29, prc.t30
  from process prc
  join tmp_acq_proc tap on tap.processid = prc.processid and tap.processid_to is not null;

with procs_to_remap as (select acquisid, processid, processid_to
                                                  from tmp_acq_proc
                                                 where processid_to is not null)
update obj_head obh
   set processid=rmp.processid_to
  from procs_to_remap rmp
 where obh.acquisid = rmp.acquisid
   and obh.processid = rmp.processid;

-- Create one new acquisition per _extra_ process in group
with acqs_with_several_procs as (select acquisid, min(processid) as min_processid
                                   from tmp_acq_proc
                                  group by acquisid
                                 having count(1) > 1)
update tmp_acq_proc tap
   set acquisid_to = nextval('seq_acquisitions')
  from acqs_with_several_procs awsp
 where tap.acquisid = awsp.acquisid
   and tap.processid > awsp.min_processid;

insert into acquisitions (acquisid, projid,
                          orig_id,
                          instrument,
                          t01, t02, t03, t04, t05, t06, t07, t08, t09, t10,
                          t11, t12, t13, t14, t15, t16, t17, t18, t19, t20,
                          t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select tap.acquisid_to, acq.projid,
       acq.orig_id || '_:' || (select count(1) from tmp_acq_proc tap2
                                where tap2.acquisid = tap.acquisid
                                  and tap2.processid < tap.processid),
       acq.instrument,
       acq.t01, acq.t02, acq.t03, acq.t04, acq.t05, acq.t06, acq.t07, acq.t08, acq.t09, acq.t10,
       acq.t11, acq.t12, acq.t13, acq.t14, acq.t15, acq.t16, acq.t17, acq.t18, acq.t19, acq.t20,
       acq.t21, acq.t22, acq.t23, acq.t24, acq.t25, acq.t26, acq.t27, acq.t28, acq.t29, acq.t30
  from acquisitions acq
  join tmp_acq_proc tap on tap.acquisid = acq.acquisid and tap.acquisid_to is not null;

-- Apply the change to objects where needed
with acqs_to_remap as (select acquisid, processid, acquisid_to
                         from tmp_acq_proc
                        where acquisid_to is not null)
update obj_head obh
   set acquisid=rmp.acquisid_to
  from acqs_to_remap rmp
 where obh.acquisid = rmp.acquisid
   and obh.processid = rmp.processid;

commit;

drop view objects;

DROP INDEX is_objectsprocess;

ALTER TABLE obj_head DROP CONSTRAINT obj_head_processid_fkey;

ALTER TABLE obj_head DROP COLUMN processid;

ALTER TABLE process DROP CONSTRAINT process_pkey;

-- Just in case, warp IDs to negative, if any remapping fails it will remain as such
update process prc set processid = -processid;

-- copy IDs from acquisitions to corresponding (now unique) process
update process prc
   set processid = coalesce(tap.acquisid_to, tap.acquisid)
  from tmp_acq_proc tap
 where prc.processid = -coalesce(tap.processid_to, tap.processid);

ALTER TABLE process ADD CONSTRAINT process_pkey PRIMARY KEY (processid);

commit;

create view objects as
                  select oh.*, oh.acquisid as processid, ofi.*
                    from obj_head oh
                    join obj_field ofi on oh.objid=ofi.objfid;

UPDATE alembic_version SET version_num='d3309bb7012e' WHERE alembic_version.version_num = '63d8b0d2196a';

COMMIT;

-- Running upgrade d3309bb7012e -> 08fdc2b6bce0

begin;

create temp table notok_objects as
select obh.objid from obj_head obh
  join acquisitions acq on acq.acquisid = obh.acquisid
 where acq.projid != obh.projid or obh.projid is null
 union all
select obh.objid from obj_head obh
  join samples sam on sam.sampleid = obh.sampleid
 where sam.projid != obh.projid or obh.projid is null;

delete from images where objid in (select * from notok_objects);

delete from obj_head where objid in (select * from notok_objects);

-- Initial state of relations
drop table if exists acq2sam;
create temp table acq2sam as
select distinct obh.sampleid, obh.acquisid, obh.projid
  from obj_head obh;

-- Need to duplicate the acquisitions attached to several samples
drop table if exists acqs2duplicate;
create temp table acqs2duplicate as
select acq.acquisid, acq.orig_id as acq_orig_id
  from acq2sam a2s
  join acquisitions acq on acq.acquisid = a2s.acquisid
  join samples sam on sam.sampleid = a2s.sampleid
 group by acq.acquisid
having count(sam.sampleid) > 1;

-- The relations to transform
drop table if exists rels2fork;
create temp table rels2fork as
select acq.acquisid, null::integer as acquisid_to, sam.sampleid
  from acquisitions acq
  join acqs2duplicate a2d on a2d.acquisid = acq.acquisid
  join acq2sam a2s on a2s.acquisid = acq.acquisid
  join samples sam on sam.sampleid = a2s.sampleid;
create index rels2fork$as on rels2fork(acquisid, sampleid);

-- Give IDs for all new acquisitions, i.e. all but the 'original' one
update rels2fork r2f
   set acquisid_to = nextval('seq_acquisitions')
 where r2f.sampleid != (select min(sampleid)
                          from rels2fork r2fs
                         where r2fs.acquisid=r2f.acquisid);

-- Duplicate acquisitions as many times as needed
insert into acquisitions (acquisid, projid,
                          orig_id,
                          instrument,
                          t01, t02, t03, t04, t05, t06, t07, t08, t09, t10,
                          t11, t12, t13, t14, t15, t16, t17, t18, t19, t20,
                          t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select r2f.acquisid_to, acq.projid,
       acq.orig_id || '@' || sam.orig_id,
       acq.instrument,
       acq.t01, acq.t02, acq.t03, acq.t04, acq.t05, acq.t06, acq.t07, acq.t08, acq.t09, acq.t10,
       acq.t11, acq.t12, acq.t13, acq.t14, acq.t15, acq.t16, acq.t17, acq.t18, acq.t19, acq.t20,
       acq.t21, acq.t22, acq.t23, acq.t24, acq.t25, acq.t26, acq.t27, acq.t28, acq.t29, acq.t30
  from acquisitions acq
  join rels2fork r2f on r2f.acquisid = acq.acquisid and r2f.acquisid_to is not null
  join samples sam on sam.sampleid = r2f.sampleid;

-- Mark the original as well
update acquisitions acq
   set orig_id = acq.orig_id || '@' || sam.orig_id
  from rels2fork r2f
  join samples sam on sam.sampleid = r2f.sampleid
 where r2f.acquisid = acq.acquisid and r2f.acquisid_to is null;

-- Duplicate processes as there is a 1<->1 relationship b/w acquisitions and process
insert into process (processid, projid, orig_id,
                     t01, t02, t03, t04, t05, t06, t07, t08, t09, t10,
                     t11, t12, t13, t14, t15, t16, t17, t18, t19, t20,
                     t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select r2f.acquisid_to, prc.projid,
       prc.orig_id || '@' || sam.orig_id,
       prc.t01, prc.t02, prc.t03, prc.t04, prc.t05, prc.t06, prc.t07, prc.t08, prc.t09, prc.t10,
       prc.t11, prc.t12, prc.t13, prc.t14, prc.t15, prc.t16, prc.t17, prc.t18, prc.t19, prc.t20,
       prc.t21, prc.t22, prc.t23, prc.t24, prc.t25, prc.t26, prc.t27, prc.t28, prc.t29, prc.t30
  from process prc
  join rels2fork r2f on r2f.acquisid = prc.processid and r2f.acquisid_to is not null
  join samples sam on sam.sampleid = r2f.sampleid;

-- Mark original process as well
update process prc
   set orig_id = prc.orig_id || '@' || sam.orig_id
  from rels2fork r2f
  join samples sam on sam.sampleid = r2f.sampleid
 where r2f.acquisid = prc.processid and r2f.acquisid_to is null;

-- Speed up update by removing checks during update
DROP INDEX is_objectsacquisition;

ALTER TABLE obj_head DROP CONSTRAINT obj_head_acquisid_fkey;

-- Make objects point to new acquisitions+process pairs
update obj_head obh
   set acquisid=r2f.acquisid_to
  from rels2fork r2f
 where r2f.acquisid_to is not null
   and obh.acquisid = r2f.acquisid
   and obh.sampleid = r2f.sampleid;

-- Re-create checks
CREATE INDEX is_objectsacquisition
    ON obj_head USING btree
    (acquisid ASC NULLS LAST)
    TABLESPACE pg_default;

ALTER TABLE obj_head
    CLUSTER ON is_objectsacquisition;

ALTER TABLE obj_head
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid)
    REFERENCES acquisitions (acquisid) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;

COMMIT;;

begin;

create temp table obj_path
    as select projid, sampleid, acquisid, count(objid) as cnt
  from obj_head
 group by projid, sampleid, acquisid;

create index obj_path$acq on obj_path(acquisid) include (sampleid, projid);

ALTER TABLE acquisitions ADD COLUMN acq_sample_id INTEGER;

-- Get rid of empty acquisitions as we don't know their parent - 14 of them in production DB
delete from acquisitions
 where acquisid not in (select acquisid from obj_path);

-- Link acquisitions to their parent
update acquisitions acq
   set acq_sample_id = (select sampleid
                          from obj_path obp
                         where obp.acquisid = acq.acquisid);

-- Add constraints that we had to exclude during creation
ALTER TABLE acquisitions ALTER COLUMN acq_sample_id SET NOT NULL;

ALTER TABLE acquisitions
    ADD CONSTRAINT acquisitions_sampleid_fkey FOREIGN KEY (acq_sample_id)
    REFERENCES samples (sampleid) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;

COMMIT;;

UPDATE alembic_version SET version_num='08fdc2b6bce0' WHERE alembic_version.version_num = 'd3309bb7012e';

-- Running upgrade 08fdc2b6bce0 -> 6f57c8aa715d

delete from process
     where processid not in (select acquisid from acquisitions);;

DROP INDEX "IS_AcquisitionsProjectOrigId";

ALTER TABLE acquisitions DROP CONSTRAINT acquisitions_projid_fkey;

ALTER TABLE acquisitions DROP COLUMN projid;

DROP INDEX "IS_ProcessProject";

ALTER TABLE process DROP CONSTRAINT process_projid_fkey;

ALTER TABLE process DROP COLUMN projid;

ALTER TABLE process ADD FOREIGN KEY(processid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE ON UPDATE CASCADE;

UPDATE alembic_version SET version_num='6f57c8aa715d' WHERE alembic_version.version_num = '08fdc2b6bce0';

COMMIT;

-- Running upgrade c30b923293e9 -> f4ea49253597, Contact person
ALTER TABLE projectspriv ADD COLUMN extra VARCHAR(1);

COMMIT;

-- Running upgrade f4ea49253597 -> a74a857fe352

drop view objects;

DROP INDEX is_objectsdate;

DROP INDEX is_objectsdepth;

DROP INDEX is_objectstime;

DROP INDEX is_objectsampleclassif;

DROP INDEX is_objectsprojclassifqual;

DROP INDEX is_objectsprojectonly;

DROP INDEX is_objectsprojrandom;

CREATE INDEX is_objectsdate ON obj_head (objdate, acquisid);

CREATE INDEX is_objectsdepth ON obj_head (depth_max, depth_min, acquisid);

CREATE INDEX is_objectstime ON obj_head (objtime, acquisid);

CREATE INDEX is_objectsacqclassifqual ON obj_head (acquisid, classif_id, classif_qual);

CREATE INDEX is_objectsacqrandom ON obj_head (acquisid, random_value, classif_qual);

CREATE INDEX is_objectfieldsorigid ON obj_field (orig_id);

ALTER TABLE obj_head DROP CONSTRAINT obj_head_sampleid_fkey;

ALTER TABLE obj_head DROP CONSTRAINT obj_head_projid_fkey;

ALTER TABLE obj_head DROP COLUMN projid;

ALTER TABLE obj_head DROP COLUMN sampleid;

create view objects as
                  select sam.projid, sam.sampleid, obh.*, obh.acquisid as processid, ofi.*
                    from obj_head obh
                    join acquisitions acq on obh.acquisid = acq.acquisid
                    join samples sam on acq.acq_sample_id = sam.sampleid
                    left join obj_field ofi on obh.objid=ofi.objfid;;

UPDATE alembic_version SET version_num='a74a857fe352' WHERE alembic_version.version_num = 'f4ea49253597';

COMMIT;

-- Running upgrade a74a857fe352 -> da78c15a7c21

drop view objects;

create temp table img_issues
as select img.imgid, img.objid, img.imgrank, null::integer as nextrank
from images img
 where exists(select 1 from images img2 where
              img2.objid=img.objid
              and img2.imgrank=img.imgrank
              and img2.imgid != img.imgid);

update img_issues imi
   set nextrank = imgrank + (select count(*)
                    from images img2
                   where img2.objid = imi.objid
                     and img2.imgrank <= imi.imgrank
                     and img2.imgid < imi.imgid);

update images img
   set imgrank = nextrank
  from img_issues imi
 where imi.imgid = img.imgid
   and imi.nextrank != imi.imgrank;;

DROP INDEX "IS_ImagesObjects";

CREATE UNIQUE INDEX is_imageobjrank ON images (objid, imgrank);

ALTER TABLE obj_head DROP COLUMN img0id;

ALTER TABLE obj_head DROP COLUMN imgcount;

create view objects as
                  select sam.projid, sam.sampleid, obh.*, obh.acquisid as processid, ofi.*
                    from obj_head obh
                    join acquisitions acq on obh.acquisid = acq.acquisid
                    join samples sam on acq.acq_sample_id = sam.sampleid
                    left join obj_field ofi on obh.objid = ofi.objfid; -- allow elimination by planner;

UPDATE alembic_version SET version_num='da78c15a7c21' WHERE alembic_version.version_num = 'a74a857fe352';

COMMIT;

-- Running upgrade da78c15a7c21 -> 271c5fddefbf

drop view objects;

ALTER TABLE obj_head ADD COLUMN object_link VARCHAR(255);

ALTER TABLE obj_head ADD COLUMN orig_id VARCHAR(255);

DO $$
DECLARE
  acq_rec RECORD;
  cnt integer = 0;
  row_count integer;
BEGIN
create temp table origs as select objfid, orig_id, object_link from obj_field ;
create unique index origs_id on origs(objfid);
FOR acq_rec IN SELECT acquisid FROM acquisitions ORDER BY acquisid DESC
LOOP
    update obj_head obh
       set orig_id = org.orig_id,
           object_link = org.object_link
      from origs org
     where org.objfid = obh.objid
       and obh.objid  IN (SELECT objid FROM obj_head WHERE acquisid = acq_rec.acquisid)
       and obh.orig_id is null;
  GET DIAGNOSTICS row_count = ROW_COUNT;
  RAISE NOTICE 'Done %, % lines',acq_rec.acquisid,row_count;
  cnt = cnt + row_count;
  IF cnt > 100000
  THEN
    COMMIT; RAISE NOTICE 'Commit'; cnt = 0;
  END IF;
END LOOP;
END;
$$;

ALTER TABLE obj_head ALTER COLUMN orig_id SET NOT NULL;

ALTER TABLE obj_field DROP COLUMN orig_id;

ALTER TABLE obj_field DROP COLUMN object_link;

-- If the system is needed up during upgrade:
-- ALTER TABLE obj_field ALTER COLUMN orig_id DROP NOT NULL;

-- create view objects as
--                   select sam.projid, sam.sampleid, obh.*, obh.acquisid as processid, ofi.n01,ofi.n02,ofi.n03,ofi.n04,ofi.n05,ofi.n06,ofi.n07,ofi.n08,ofi.n09,ofi.n10,ofi.n11,ofi.n12,ofi.n13,ofi.n14,ofi.n15,ofi.n16,ofi.n17,ofi.n18,ofi.n19,ofi.n20,ofi.n21,ofi.n22,ofi.n23,ofi.n24,ofi.n25,ofi.n26,ofi.n27,ofi.n28,ofi.n29,ofi.n30,ofi.n31,ofi.n32,ofi.n33,ofi.n34,ofi.n35,ofi.n36,ofi.n37,ofi.n38,ofi.n39,ofi.n40,ofi.n41,ofi.n42,ofi.n43,ofi.n44,ofi.n45,ofi.n46,ofi.n47,ofi.n48,ofi.n49,ofi.n50,ofi.n51,ofi.n52,ofi.n53,ofi.n54,ofi.n55,ofi.n56,ofi.n57,ofi.n58,ofi.n59,ofi.n60,ofi.n61,ofi.n62,ofi.n63,ofi.n64,ofi.n65,ofi.n66,ofi.n67,ofi.n68,ofi.n69,ofi.n70,ofi.n71,ofi.n72,ofi.n73,ofi.n74,ofi.n75,ofi.n76,ofi.n77,ofi.n78,ofi.n79,ofi.n80,ofi.n81,ofi.n82,ofi.n83,ofi.n84,ofi.n85,ofi.n86,ofi.n87,ofi.n88,ofi.n89,ofi.n90,ofi.n91,ofi.n92,ofi.n93,ofi.n94,ofi.n95,ofi.n96,ofi.n97,ofi.n98,ofi.n99,ofi.n100,ofi.n101,ofi.n102,ofi.n103,ofi.n104,ofi.n105,ofi.n106,ofi.n107,ofi.n108,ofi.n109,ofi.n110,ofi.n111,ofi.n112,ofi.n113,ofi.n114,ofi.n115,ofi.n116,ofi.n117,ofi.n118,ofi.n119,ofi.n120,ofi.n121,ofi.n122,ofi.n123,ofi.n124,ofi.n125,ofi.n126,ofi.n127,ofi.n128,ofi.n129,ofi.n130,ofi.n131,ofi.n132,ofi.n133,ofi.n134,ofi.n135,ofi.n136,ofi.n137,ofi.n138,ofi.n139,ofi.n140,ofi.n141,ofi.n142,ofi.n143,ofi.n144,ofi.n145,ofi.n146,ofi.n147,ofi.n148,ofi.n149,ofi.n150,ofi.n151,ofi.n152,ofi.n153,ofi.n154,ofi.n155,ofi.n156,ofi.n157,ofi.n158,ofi.n159,ofi.n160,ofi.n161,ofi.n162,ofi.n163,ofi.n164,ofi.n165,ofi.n166,ofi.n167,ofi.n168,ofi.n169,ofi.n170,ofi.n171,ofi.n172,ofi.n173,ofi.n174,ofi.n175,ofi.n176,ofi.n177,ofi.n178,ofi.n179,ofi.n180,ofi.n181,ofi.n182,ofi.n183,ofi.n184,ofi.n185,ofi.n186,ofi.n187,ofi.n188,ofi.n189,ofi.n190,ofi.n191,ofi.n192,ofi.n193,ofi.n194,ofi.n195,ofi.n196,ofi.n197,ofi.n198,ofi.n199,ofi.n200,ofi.n201,ofi.n202,ofi.n203,ofi.n204,ofi.n205,ofi.n206,ofi.n207,ofi.n208,ofi.n209,ofi.n210,ofi.n211,ofi.n212,ofi.n213,ofi.n214,ofi.n215,ofi.n216,ofi.n217,ofi.n218,ofi.n219,ofi.n220,ofi.n221,ofi.n222,ofi.n223,ofi.n224,ofi.n225,ofi.n226,ofi.n227,ofi.n228,ofi.n229,ofi.n230,ofi.n231,ofi.n232,ofi.n233,ofi.n234,ofi.n235,ofi.n236,ofi.n237,ofi.n238,ofi.n239,ofi.n240,ofi.n241,ofi.n242,ofi.n243,ofi.n244,ofi.n245,ofi.n246,ofi.n247,ofi.n248,ofi.n249,ofi.n250,ofi.n251,ofi.n252,ofi.n253,ofi.n254,ofi.n255,ofi.n256,ofi.n257,ofi.n258,ofi.n259,ofi.n260,ofi.n261,ofi.n262,ofi.n263,ofi.n264,ofi.n265,ofi.n266,ofi.n267,ofi.n268,ofi.n269,ofi.n270,ofi.n271,ofi.n272,ofi.n273,ofi.n274,ofi.n275,ofi.n276,ofi.n277,ofi.n278,ofi.n279,ofi.n280,ofi.n281,ofi.n282,ofi.n283,ofi.n284,ofi.n285,ofi.n286,ofi.n287,ofi.n288,ofi.n289,ofi.n290,ofi.n291,ofi.n292,ofi.n293,ofi.n294,ofi.n295,ofi.n296,ofi.n297,ofi.n298,ofi.n299,ofi.n300,ofi.n301,ofi.n302,ofi.n303,ofi.n304,ofi.n305,ofi.n306,ofi.n307,ofi.n308,ofi.n309,ofi.n310,ofi.n311,ofi.n312,ofi.n313,ofi.n314,ofi.n315,ofi.n316,ofi.n317,ofi.n318,ofi.n319,ofi.n320,ofi.n321,ofi.n322,ofi.n323,ofi.n324,ofi.n325,ofi.n326,ofi.n327,ofi.n328,ofi.n329,ofi.n330,ofi.n331,ofi.n332,ofi.n333,ofi.n334,ofi.n335,ofi.n336,ofi.n337,ofi.n338,ofi.n339,ofi.n340,ofi.n341,ofi.n342,ofi.n343,ofi.n344,ofi.n345,ofi.n346,ofi.n347,ofi.n348,ofi.n349,ofi.n350,ofi.n351,ofi.n352,ofi.n353,ofi.n354,ofi.n355,ofi.n356,ofi.n357,ofi.n358,ofi.n359,ofi.n360,ofi.n361,ofi.n362,ofi.n363,ofi.n364,ofi.n365,ofi.n366,ofi.n367,ofi.n368,ofi.n369,ofi.n370,ofi.n371,ofi.n372,ofi.n373,ofi.n374,ofi.n375,ofi.n376,ofi.n377,ofi.n378,ofi.n379,ofi.n380,ofi.n381,ofi.n382,ofi.n383,ofi.n384,ofi.n385,ofi.n386,ofi.n387,ofi.n388,ofi.n389,ofi.n390,ofi.n391,ofi.n392,ofi.n393,ofi.n394,ofi.n395,ofi.n396,ofi.n397,ofi.n398,ofi.n399,ofi.n400,ofi.n401,ofi.n402,ofi.n403,ofi.n404,ofi.n405,ofi.n406,ofi.n407,ofi.n408,ofi.n409,ofi.n410,ofi.n411,ofi.n412,ofi.n413,ofi.n414,ofi.n415,ofi.n416,ofi.n417,ofi.n418,ofi.n419,ofi.n420,ofi.n421,ofi.n422,ofi.n423,ofi.n424,ofi.n425,ofi.n426,ofi.n427,ofi.n428,ofi.n429,ofi.n430,ofi.n431,ofi.n432,ofi.n433,ofi.n434,ofi.n435,ofi.n436,ofi.n437,ofi.n438,ofi.n439,ofi.n440,ofi.n441,ofi.n442,ofi.n443,ofi.n444,ofi.n445,ofi.n446,ofi.n447,ofi.n448,ofi.n449,ofi.n450,ofi.n451,ofi.n452,ofi.n453,ofi.n454,ofi.n455,ofi.n456,ofi.n457,ofi.n458,ofi.n459,ofi.n460,ofi.n461,ofi.n462,ofi.n463,ofi.n464,ofi.n465,ofi.n466,ofi.n467,ofi.n468,ofi.n469,ofi.n470,ofi.n471,ofi.n472,ofi.n473,ofi.n474,ofi.n475,ofi.n476,ofi.n477,ofi.n478,ofi.n479,ofi.n480,ofi.n481,ofi.n482,ofi.n483,ofi.n484,ofi.n485,ofi.n486,ofi.n487,ofi.n488,ofi.n489,ofi.n490,ofi.n491,ofi.n492,ofi.n493,ofi.n494,ofi.n495,ofi.n496,ofi.n497,ofi.n498,ofi.n499,ofi.n500,ofi.t01,ofi.t02,ofi.t03,ofi.t04,ofi.t05,ofi.t06,ofi.t07,ofi.t08,ofi.t09,ofi.t10,ofi.t11,ofi.t12,ofi.t13,ofi.t14,ofi.t15,ofi.t16,ofi.t17,ofi.t18,ofi.t19,ofi.t20
--                     from obj_head obh
--                     join acquisitions acq on obh.acquisid = acq.acquisid
--                     join samples sam on acq.acq_sample_id = sam.sampleid
--                     left join obj_field ofi on obh.objid = ofi.objfid; -- allow elimination by planner;

create view objects as
                  select sam.projid, sam.sampleid, obh.*, obh.acquisid as processid, ofi.*
                    from obj_head obh
                    join acquisitions acq on obh.acquisid = acq.acquisid
                    join samples sam on acq.acq_sample_id = sam.sampleid
                    left join obj_field ofi on obh.objid = ofi.objfid; -- allow elimination by planner;

UPDATE alembic_version SET version_num='271c5fddefbf' WHERE alembic_version.version_num = 'da78c15a7c21';

COMMIT;

-- Running upgrade 271c5fddefbf -> 21bb404620d5

CREATE TABLE image_file (
    path VARCHAR NOT NULL,
    state CHAR DEFAULT '?' NOT NULL,
    digest_type CHAR DEFAULT '?' NOT NULL,
    digest BYTEA,
    PRIMARY KEY (path)
);

CREATE INDEX is_phy_image_file ON image_file (digest_type, digest);

CREATE INDEX is_image_file ON images (file_name);

ALTER TABLE users ADD COLUMN mail_status CHAR DEFAULT ' ';

ALTER TABLE users ADD COLUMN mail_status_date TIMESTAMP WITHOUT TIME ZONE;

UPDATE alembic_version SET version_num='21bb404620d5' WHERE alembic_version.version_num = '271c5fddefbf';

COMMIT;

-- Running upgrade 21bb404620d5 -> 910b679215ca

ALTER TABLE collection ADD COLUMN external_id VARCHAR NOT NULL;

ALTER TABLE collection ADD COLUMN external_id_system VARCHAR NOT NULL;

UPDATE alembic_version SET version_num='910b679215ca' WHERE alembic_version.version_num = '21bb404620d5';


COMMIT;

-- Running upgrade 21bb404620d5 -> dae002b5d15a, Job table & collection permalink

CREATE TABLE job (
    id SERIAL NOT NULL,
    owner_id INTEGER NOT NULL,
    type VARCHAR(80) NOT NULL,
    params VARCHAR,
    state VARCHAR(1),
    step INTEGER,
    progress_pct INTEGER,
    progress_msg VARCHAR,
    messages VARCHAR,
    inside VARCHAR,
    question VARCHAR,
    reply VARCHAR,
    result VARCHAR,
    creation_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_on TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES users (id)
);

ALTER TABLE collection ADD COLUMN short_title VARCHAR(64);

ALTER TABLE collection ALTER COLUMN external_id SET NOT NULL;

ALTER TABLE collection ALTER COLUMN external_id_system SET NOT NULL;

CREATE UNIQUE INDEX "CollectionShortTitle" ON collection (short_title);

UPDATE alembic_version SET version_num='dae002b5d15a' WHERE alembic_version.version_num = '21bb404620d5';

COMMIT;

-- Running upgrade dae002b5d15a -> 00601700d281

ALTER TABLE images ALTER COLUMN file_name SET NOT NULL;

ALTER TABLE images ALTER COLUMN height SET NOT NULL;

ALTER TABLE images ALTER COLUMN imgrank SET NOT NULL;

ALTER TABLE images ALTER COLUMN orig_file_name SET NOT NULL;

ALTER TABLE images ALTER COLUMN width SET NOT NULL;

UPDATE alembic_version SET version_num='00601700d281' WHERE alembic_version.version_num = 'dae002b5d15a';

COMMIT;

-- INFO  [alembic.runtime.migration] Running upgrade 00601700d281 -> a4c0d0c48e5a, empty message
-- Running upgrade 00601700d281 -> a4c0d0c48e5a

CREATE TABLE taxo_change_log (
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    why VARCHAR(1) NOT NULL,
    impacted INTEGER NOT NULL,
    occurred_on TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (from_id, to_id, project_id),
    FOREIGN KEY(from_id) REFERENCES taxonomy (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (projid) ON DELETE CASCADE,
    FOREIGN KEY(to_id) REFERENCES taxonomy (id) ON DELETE CASCADE
);

UPDATE alembic_version SET version_num='a4c0d0c48e5a' WHERE alembic_version.version_num = '00601700d281';

COMMIT;

-- INFO  [alembic.runtime.migration] Running upgrade a4c0d0c48e5a -> beaa3e8e4033, empty message
-- Running upgrade a4c0d0c48e5a -> beaa3e8e4033

ALTER TABLE projects ADD COLUMN description VARCHAR;

BEGIN;
UPDATE projects
   SET description = projtype;
COMMIT;;

ALTER TABLE projects DROP COLUMN projtype;

UPDATE alembic_version SET version_num='beaa3e8e4033' WHERE alembic_version.version_num = 'a4c0d0c48e5a';

COMMIT;

-- Running upgrade beaa3e8e4033 -> a173f0289de1

DROP INDEX "IS_TempTaxoIdFinal";

DROP INDEX "IS_TempTaxoParent";

DROP TABLE temp_taxo;

DROP TABLE part_histopart_det;

DROP TABLE part_projects_res;

DROP INDEX is_part_samples_prj;

DROP INDEX is_part_samples_sampleid;

DROP TABLE part_histopart_reduit;

DROP TABLE part_histocat_lst;

DROP INDEX is_part_projects_projid;

DROP TABLE part_ctd;

DROP TABLE part_histocat;

DROP TABLE part_samples;

DROP TABLE part_projects;

ALTER TABLE samples ALTER COLUMN projid SET NOT NULL;

update acquisitions acq
set orig_id = orig_id || '_' || (select count(1) from acquisitions acq2
where acq2.acq_sample_id = acq.acq_sample_id and acq2.orig_id = acq.orig_id and acq2.acquisid <= acq.acquisid)
where exists (select 1 from acquisitions acq2
where acq2.acq_sample_id = acq.acq_sample_id and acq2.orig_id = acq.orig_id and acq2.acquisid != acq.acquisid);;

CREATE UNIQUE INDEX "IS_AcquisOrigId" ON acquisitions (acq_sample_id, orig_id);

delete from projectspriv where member is null;;

ALTER TABLE projectspriv ALTER COLUMN member SET NOT NULL;

ALTER TABLE projectspriv DROP CONSTRAINT projectspriv_member_fkey;

ALTER TABLE projectspriv ADD FOREIGN KEY(member) REFERENCES users (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='a173f0289de1' WHERE alembic_version.version_num = 'beaa3e8e4033';

-- Running upgrade a173f0289de1 -> 088904e6b78e

CREATE UNIQUE INDEX "CollectionShortTitle" ON collection (short_title);

delete from process where processid in (select processid from process except select acquisid from acquisitions);

ALTER TABLE process ADD FOREIGN KEY(processid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='088904e6b78e' WHERE alembic_version.version_num = 'a173f0289de1';

-- Running upgrade 088904e6b78e -> ffb69f8124f6

CREATE TABLE instrument (
    instrument_id VARCHAR(32) NOT NULL,
    name VARCHAR(255),
    bodc_url VARCHAR(255),
    PRIMARY KEY (instrument_id)
);

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('CytoBuoy', 'CytoSense flow cytometer', 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1209/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('IFCB', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1588/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('CPICS', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1582/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('UVP 5', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1577/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('UVP 6', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('VPR', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1584/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('LISST-Holo', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1585/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('Zoocam', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1587/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('Loki', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1586/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('FlowCam', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1583/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('FastCam', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1580/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('Zooscan', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1581/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('PlanktoScope', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1579/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('ISIIS', NULL, 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1561/');

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('AMNIS', 'AMNIS Imaging Flow Cytometer', NULL);

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('camera', 'Generic camera', NULL);

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('microscope', 'Generic microscope', NULL);

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('scanner', 'Generic scanner', NULL);

INSERT INTO instrument (instrument_id, name, bodc_url) VALUES ('?', 'Unknown instrument', NULL);

ALTER TABLE projects ADD COLUMN instrument_id VARCHAR(32) DEFAULT '?' NOT NULL;

ALTER TABLE projects ALTER COLUMN instrument_id DROP DEFAULT;

ALTER TABLE projects ADD FOREIGN KEY(instrument_id) REFERENCES instrument (instrument_id);

UPDATE alembic_version SET version_num='8ac7e3c29305' WHERE alembic_version.version_num = '088904e6b78e';

COMMIT;

-- Running upgrade 8ac7e3c29305 -> 521c25353fa0, new report tables

CREATE TABLE projects_variables (
    project_id INTEGER NOT NULL,
    subsample_coef VARCHAR,
    total_water_volume VARCHAR,
    individual_volume VARCHAR,
    PRIMARY KEY (project_id),
    FOREIGN KEY(project_id) REFERENCES projects (projid) ON DELETE CASCADE
);

ALTER TABLE obj_field ADD COLUMN acquis_id INTEGER;

CREATE INDEX obj_field_acquisid_objfid_idx ON obj_field (acquis_id, objfid);

update obj_field set acquis_id = (select acquisid from obj_head where objid = objfid) where acquis_id is null;

UPDATE alembic_version SET version_num='521c25353fa0' WHERE alembic_version.version_num = '8ac7e3c29305';

-- Cluster for perfs - not from Alembic

cluster obj_field using obj_field_acquisid_objfid_idx;

-- Running upgrade 521c25353fa0 -> 34d91185174c, Taxo recast AKA remapping storage

CREATE TABLE taxo_recast (
    recast_id INTEGER GENERATED ALWAYS AS IDENTITY,
    collection_id INTEGER,
    project_id INTEGER,
    operation VARCHAR(16) NOT NULL,
    transforms JSONB NOT NULL,
    documentation JSONB NOT NULL,
    PRIMARY KEY (recast_id),
    FOREIGN KEY(collection_id) REFERENCES collection (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (projid) ON DELETE CASCADE
);

UPDATE alembic_version SET version_num='34d91185174c' WHERE alembic_version.version_num = '521c25353fa0';

COMMIT;


-- Running upgrade  34d91185174c -> 1b1beb672279 , users validation
CREATE TABLE user_password_reset (
    user_id INTEGER NOT NULL,
    temp_password VARCHAR,
    creation_date TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (user_id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
ALTER TABLE users ADD COLUMN status_admin_comment VARCHAR(255);
ALTER TABLE users ADD COLUMN status_date TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE users ALTER active DROP DEFAULT;
ALTER TABLE users ALTER active TYPE SMALLINT
    USING
    CASE
    WHEN active =false THEN 0 ELSE 1
    END;
ALTER TABLE users ALTER active SET DEFAULT 1;
ALTER TABLE users RENAME COLUMN active TO status ;
ALTER TABLE users ALTER mail_status DROP DEFAULT;
ALTER TABLE users ALTER mail_status TYPE BOOLEAN
USING
CASE
WHEN mail_status ='V' THEN true
WHEN mail_status = 'W' then false
ELSE NULL
END;
ALTER TABLE users ALTER mail_status SET DEFAULT NULL;
-------------add 30 free cols to samples
DO
$$
BEGIN
    FOR  colnames
    in 31..60
    LOOP
     EXECUTE 'ALTER TABLE samples ADD COLUMN t' || colnames || ' VARCHAR(250);';
    END LOOP;
END
$$;

UPDATE alembic_version SET version_num='1b1beb672279' WHERE alembic_version.version_num = '34d91185174c';

COMMIT;

-- Manual upgrades 17 feb 2024
--
-- Based on a pg_dump -t obj_head from production DB on the 9th of Feb 2024
--
--drop table public.obj_head_new;

create table public.obj_head_new
(
    objid              bigint       not null,
    acquisid           integer      not null,
    classif_id         integer,
    objtime            time without time zone,
    latitude           double precision,
    longitude          double precision,
    depth_min          double precision,
    depth_max          double precision,
    objdate            date,
    classif_qual       char,
    sunpos             char,
    classif_when       timestamp without time zone,
    classif_who        integer,
    classif_auto_id    integer,
    classif_auto_when  timestamp without time zone,
    classif_auto_score double precision,
    orig_id            varchar(255) not null,
    object_link        varchar(255),
    complement_info    varchar
)
WITH (autovacuum_vacuum_scale_factor='0.01', fillfactor='90');
ALTER TABLE ONLY public.obj_head_new ALTER COLUMN acquisid SET STATISTICS 10000;

alter table public.obj_head_new
    owner to postgres;

--
-- Name: obj_head obj_head_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head_new
    ADD CONSTRAINT obj_head_pkey2 PRIMARY KEY (objid);

--
-- Name: TABLE obj_head; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.obj_head_new TO readerole;
GRANT SELECT ON TABLE public.obj_head_new TO zoo;
GRANT SELECT ON TABLE public.obj_head_new TO repuser;

DO
$$
    DECLARE
        chunk     integer = 1000000;
        total_row_count integer = 0;
        nb_chunks integer = 0;
        row_count integer;
        acq_rec record;
    BEGIN
        FOR acq_rec IN (SELECT acquisid FROM acquisitions ORDER BY acquisid)
            LOOP
                insert into obj_head_new (objid, acquisid, classif_id,
                                       objtime, latitude, longitude, objdate, depth_min, depth_max,
                                       classif_qual, sunpos, classif_who, classif_when,
                                       classif_auto_score, classif_auto_when, classif_auto_id, complement_info,
                                       orig_id, object_link)
                select objid,
                       acquisid,
                       classif_id,
                       objtime,
                       latitude,
                       longitude,
                       objdate,
                       depth_min,
                       depth_max,
                       classif_qual,
                       sunpos,
                       classif_who,
                       classif_when,
                       classif_auto_score,
                       classif_auto_when,
                       classif_auto_id,
                       complement_info,
                       orig_id,
                       object_link
                from obj_head
                where acquisid = acq_rec.acquisid;
                GET DIAGNOSTICS row_count = ROW_COUNT;
                total_row_count = total_row_count + row_count;
                IF total_row_count / chunk > nb_chunks
                THEN
                    nb_chunks = total_row_count / chunk;
                    RAISE NOTICE '%: Done % lines',current_time,total_row_count;
                    COMMIT;
                END IF ;
            END LOOP;
    END;
$$;

ANALYSE obj_head_new;

--
-- Name: is_objectsacqclassifqual; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsacqclassifqual RENAME TO is_objectsacqclassifqual_old;
CREATE INDEX is_objectsacqclassifqual ON public.obj_head_new USING btree (acquisid) include (classif_qual, classif_id);

--
-- Name: is_objectsacqrandom; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsacqrandom RENAME TO is_objectsacqrandom_old;
-- CREATE INDEX is_objectsacqrandom ON public.obj_head_new USING btree (acquisid, hashtext(orig_id), classif_qual);

--
-- Name: is_objectsacquisition; Type: INDEX; Schema: public; Owner: postgres
--

ALTER INDEX is_objectsacquisition RENAME TO is_objectsacquisition_old;
CREATE INDEX is_objectsacquisition ON public.obj_head_new USING btree (acquisid) ;

ALTER TABLE public.obj_head_new CLUSTER ON is_objectsacquisition;

--
-- Name: is_objectsdate; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsdate RENAME TO is_objectsdate_old;
CREATE INDEX is_objectsdate ON public.obj_head_new USING btree (objdate) include (acquisid);


--
-- Name: is_objectsdepth; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsdepth RENAME TO is_objectsdepth_old;
CREATE INDEX is_objectsdepth ON public.obj_head_new USING btree (depth_max, depth_min) include (acquisid);


--
-- Name: is_objectslatlong; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectslatlong RENAME TO is_objectslatlong_old;
CREATE INDEX is_objectslatlong ON public.obj_head_new USING btree (latitude, longitude) include (acquisid);


--
-- Name: is_objectstime; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX  is_objectstime RENAME TO is_objectstime_old;
CREATE INDEX is_objectstime ON public.obj_head_new USING btree (objtime) include (acquisid);

--
-- Name: obj_head obj_head_acquisid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_acquisid_fkey TO obj_head_acquisid_fkey_old;
ALTER TABLE ONLY public.obj_head_new
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES public.acquisitions(acquisid) ON DELETE CASCADE;

--
-- Name: obj_head obj_head_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_classif_who_fkey TO obj_head_classif_who_fkey_old;
ALTER TABLE ONLY public.obj_head_new
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);

ANALYSE obj_head_new;

--
-- Name: objectsclassifhisto objectsclassifhisto_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.objectsclassifhisto
    DROP CONSTRAINT objectsclassifhisto_objid_fkey;
ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head_new(objid) ON DELETE CASCADE;


--
-- Name: images images_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.images
    DROP CONSTRAINT images_objid_fkey;
ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head_new(objid);

--
-- Name: obj_cnn_features obj_cnn_features_objcnnid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.obj_cnn_features
    DROP CONSTRAINT obj_cnn_features_objcnnid_fkey;
ALTER TABLE ONLY public.obj_cnn_features
    ADD CONSTRAINT obj_cnn_features_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES public.obj_head_new(objid) ON DELETE CASCADE;

--
-- Name: obj_field obj_field_objfid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.obj_field
    DROP CONSTRAINT obj_field_objfid_fkey;
ALTER TABLE ONLY public.obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES public.obj_head_new(objid) ON DELETE CASCADE;

ALTER TABLE obj_head RENAME TO obj_head_old;

ALTER TABLE ONLY public.obj_head_old
    RENAME CONSTRAINT obj_head_pkey TO obj_head_pkey_old;

ALTER TABLE obj_head_new RENAME TO obj_head;

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_pkey2 TO obj_head_pkey;

drop view obj_prj;

drop table obj_head_old;

---

--
-- Based on a pg_dump -t objectsclassifhisto from production DB on the 9th of Feb 2024
--

-- drop table public.objectsclassifhisto_new;

create table public.objectsclassifhisto_new
(
    objid         bigint                      not null,
    classif_date  timestamp without time zone not null,
    classif_id    integer                     not null,
    classif_type  character(1),
    classif_qual  character(1),
    classif_score double precision,
    classif_who   integer
);

ALTER TABLE ONLY public.objectsclassifhisto_new ALTER COLUMN classif_date SET STATISTICS 10000;


ALTER TABLE public.objectsclassifhisto_new OWNER TO postgres;

--
-- Name: TABLE objectsclassifhisto; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.objectsclassifhisto_new TO readerole;
GRANT SELECT ON TABLE public.objectsclassifhisto_new TO zoo;
GRANT SELECT ON TABLE public.objectsclassifhisto_new TO repuser;

DO
$$
    DECLARE
        cp_objid  integer = 0;
        next_cp_objid integer = 1;
        chunk     integer = 1000000;
    BEGIN
        WHILE next_cp_objid IS NOT NULL
            LOOP
                with done as (insert into objectsclassifhisto_new (objid,
                                                  classif_date,
                                                  classif_id,
                                                  classif_type,
                                                  classif_qual,
                                                  classif_score,
                                                  classif_who)
                select objid,
                       classif_date,
                       classif_id,
                       classif_type,
                       classif_qual,
                       classif_score,
                       classif_who
                from objectsclassifhisto
                where objid > cp_objid and classif_id is not null
                order by objid
                limit chunk
                returning objid) select max(objid) into next_cp_objid from done;
                RAISE NOTICE '%: Done up to %',current_time,next_cp_objid;
                COMMIT;
                cp_objid = next_cp_objid;
            END LOOP;
    END;
$$;

ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_pkey TO objectsclassifhisto_pkey_old;
--
-- Name: objectsclassifhisto objectsclassifhisto_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto_new
    ADD CONSTRAINT objectsclassifhisto_pkey PRIMARY KEY (objid, classif_date);


ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_classif_who_fkey TO objectsclassifhisto_classif_who_fkey_old;

--
-- Name: objectsclassifhisto objectsclassifhisto_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto_new
    ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);

--
-- Name: objectsclassifhisto objectsclassifhisto_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_objid_fkey TO objectsclassifhisto_objid_fkey_old;

ALTER TABLE ONLY public.objectsclassifhisto_new
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head(objid) ON DELETE CASCADE;

ALTER TABLE public.objectsclassifhisto RENAME TO objectsclassifhisto_old;

ALTER TABLE public.objectsclassifhisto_new RENAME TO objectsclassifhisto;

drop table objectsclassifhisto_old;

---

--
-- Name: objects; Type: VIEW; Schema: public; Owner: postgres
--

CREATE OR REPLACE VIEW public.objects AS
 SELECT sam.projid,
    sam.sampleid,
    obh.objid,
    obh.latitude,
    obh.longitude,
    obh.objdate,
    obh.objtime,
    obh.depth_min,
    obh.depth_max,
    obh.classif_id,
    obh.classif_qual,
    obh.classif_who,
    obh.classif_when,
    obh.classif_auto_id,
    obh.classif_auto_score,
    obh.classif_auto_when,
    NULL::integer AS classif_crossvalidation_id,
    obh.complement_info,
    NULL::double precision AS similarity,
    obh.sunpos,
    HASHTEXT(obh.orig_id) AS random_value,
    obh.acquisid,
    obh.object_link,
    obh.orig_id,
    obh.acquisid AS processid,
    ofi.objfid,
    ofi.n01,
    ofi.n02,
    ofi.n03,
    ofi.n04,
    ofi.n05,
    ofi.n06,
    ofi.n07,
    ofi.n08,
    ofi.n09,
    ofi.n10,
    ofi.n11,
    ofi.n12,
    ofi.n13,
    ofi.n14,
    ofi.n15,
    ofi.n16,
    ofi.n17,
    ofi.n18,
    ofi.n19,
    ofi.n20,
    ofi.n21,
    ofi.n22,
    ofi.n23,
    ofi.n24,
    ofi.n25,
    ofi.n26,
    ofi.n27,
    ofi.n28,
    ofi.n29,
    ofi.n30,
    ofi.n31,
    ofi.n32,
    ofi.n33,
    ofi.n34,
    ofi.n35,
    ofi.n36,
    ofi.n37,
    ofi.n38,
    ofi.n39,
    ofi.n40,
    ofi.n41,
    ofi.n42,
    ofi.n43,
    ofi.n44,
    ofi.n45,
    ofi.n46,
    ofi.n47,
    ofi.n48,
    ofi.n49,
    ofi.n50,
    ofi.n51,
    ofi.n52,
    ofi.n53,
    ofi.n54,
    ofi.n55,
    ofi.n56,
    ofi.n57,
    ofi.n58,
    ofi.n59,
    ofi.n60,
    ofi.n61,
    ofi.n62,
    ofi.n63,
    ofi.n64,
    ofi.n65,
    ofi.n66,
    ofi.n67,
    ofi.n68,
    ofi.n69,
    ofi.n70,
    ofi.n71,
    ofi.n72,
    ofi.n73,
    ofi.n74,
    ofi.n75,
    ofi.n76,
    ofi.n77,
    ofi.n78,
    ofi.n79,
    ofi.n80,
    ofi.n81,
    ofi.n82,
    ofi.n83,
    ofi.n84,
    ofi.n85,
    ofi.n86,
    ofi.n87,
    ofi.n88,
    ofi.n89,
    ofi.n90,
    ofi.n91,
    ofi.n92,
    ofi.n93,
    ofi.n94,
    ofi.n95,
    ofi.n96,
    ofi.n97,
    ofi.n98,
    ofi.n99,
    ofi.n100,
    ofi.n101,
    ofi.n102,
    ofi.n103,
    ofi.n104,
    ofi.n105,
    ofi.n106,
    ofi.n107,
    ofi.n108,
    ofi.n109,
    ofi.n110,
    ofi.n111,
    ofi.n112,
    ofi.n113,
    ofi.n114,
    ofi.n115,
    ofi.n116,
    ofi.n117,
    ofi.n118,
    ofi.n119,
    ofi.n120,
    ofi.n121,
    ofi.n122,
    ofi.n123,
    ofi.n124,
    ofi.n125,
    ofi.n126,
    ofi.n127,
    ofi.n128,
    ofi.n129,
    ofi.n130,
    ofi.n131,
    ofi.n132,
    ofi.n133,
    ofi.n134,
    ofi.n135,
    ofi.n136,
    ofi.n137,
    ofi.n138,
    ofi.n139,
    ofi.n140,
    ofi.n141,
    ofi.n142,
    ofi.n143,
    ofi.n144,
    ofi.n145,
    ofi.n146,
    ofi.n147,
    ofi.n148,
    ofi.n149,
    ofi.n150,
    ofi.n151,
    ofi.n152,
    ofi.n153,
    ofi.n154,
    ofi.n155,
    ofi.n156,
    ofi.n157,
    ofi.n158,
    ofi.n159,
    ofi.n160,
    ofi.n161,
    ofi.n162,
    ofi.n163,
    ofi.n164,
    ofi.n165,
    ofi.n166,
    ofi.n167,
    ofi.n168,
    ofi.n169,
    ofi.n170,
    ofi.n171,
    ofi.n172,
    ofi.n173,
    ofi.n174,
    ofi.n175,
    ofi.n176,
    ofi.n177,
    ofi.n178,
    ofi.n179,
    ofi.n180,
    ofi.n181,
    ofi.n182,
    ofi.n183,
    ofi.n184,
    ofi.n185,
    ofi.n186,
    ofi.n187,
    ofi.n188,
    ofi.n189,
    ofi.n190,
    ofi.n191,
    ofi.n192,
    ofi.n193,
    ofi.n194,
    ofi.n195,
    ofi.n196,
    ofi.n197,
    ofi.n198,
    ofi.n199,
    ofi.n200,
    ofi.n201,
    ofi.n202,
    ofi.n203,
    ofi.n204,
    ofi.n205,
    ofi.n206,
    ofi.n207,
    ofi.n208,
    ofi.n209,
    ofi.n210,
    ofi.n211,
    ofi.n212,
    ofi.n213,
    ofi.n214,
    ofi.n215,
    ofi.n216,
    ofi.n217,
    ofi.n218,
    ofi.n219,
    ofi.n220,
    ofi.n221,
    ofi.n222,
    ofi.n223,
    ofi.n224,
    ofi.n225,
    ofi.n226,
    ofi.n227,
    ofi.n228,
    ofi.n229,
    ofi.n230,
    ofi.n231,
    ofi.n232,
    ofi.n233,
    ofi.n234,
    ofi.n235,
    ofi.n236,
    ofi.n237,
    ofi.n238,
    ofi.n239,
    ofi.n240,
    ofi.n241,
    ofi.n242,
    ofi.n243,
    ofi.n244,
    ofi.n245,
    ofi.n246,
    ofi.n247,
    ofi.n248,
    ofi.n249,
    ofi.n250,
    ofi.n251,
    ofi.n252,
    ofi.n253,
    ofi.n254,
    ofi.n255,
    ofi.n256,
    ofi.n257,
    ofi.n258,
    ofi.n259,
    ofi.n260,
    ofi.n261,
    ofi.n262,
    ofi.n263,
    ofi.n264,
    ofi.n265,
    ofi.n266,
    ofi.n267,
    ofi.n268,
    ofi.n269,
    ofi.n270,
    ofi.n271,
    ofi.n272,
    ofi.n273,
    ofi.n274,
    ofi.n275,
    ofi.n276,
    ofi.n277,
    ofi.n278,
    ofi.n279,
    ofi.n280,
    ofi.n281,
    ofi.n282,
    ofi.n283,
    ofi.n284,
    ofi.n285,
    ofi.n286,
    ofi.n287,
    ofi.n288,
    ofi.n289,
    ofi.n290,
    ofi.n291,
    ofi.n292,
    ofi.n293,
    ofi.n294,
    ofi.n295,
    ofi.n296,
    ofi.n297,
    ofi.n298,
    ofi.n299,
    ofi.n300,
    ofi.n301,
    ofi.n302,
    ofi.n303,
    ofi.n304,
    ofi.n305,
    ofi.n306,
    ofi.n307,
    ofi.n308,
    ofi.n309,
    ofi.n310,
    ofi.n311,
    ofi.n312,
    ofi.n313,
    ofi.n314,
    ofi.n315,
    ofi.n316,
    ofi.n317,
    ofi.n318,
    ofi.n319,
    ofi.n320,
    ofi.n321,
    ofi.n322,
    ofi.n323,
    ofi.n324,
    ofi.n325,
    ofi.n326,
    ofi.n327,
    ofi.n328,
    ofi.n329,
    ofi.n330,
    ofi.n331,
    ofi.n332,
    ofi.n333,
    ofi.n334,
    ofi.n335,
    ofi.n336,
    ofi.n337,
    ofi.n338,
    ofi.n339,
    ofi.n340,
    ofi.n341,
    ofi.n342,
    ofi.n343,
    ofi.n344,
    ofi.n345,
    ofi.n346,
    ofi.n347,
    ofi.n348,
    ofi.n349,
    ofi.n350,
    ofi.n351,
    ofi.n352,
    ofi.n353,
    ofi.n354,
    ofi.n355,
    ofi.n356,
    ofi.n357,
    ofi.n358,
    ofi.n359,
    ofi.n360,
    ofi.n361,
    ofi.n362,
    ofi.n363,
    ofi.n364,
    ofi.n365,
    ofi.n366,
    ofi.n367,
    ofi.n368,
    ofi.n369,
    ofi.n370,
    ofi.n371,
    ofi.n372,
    ofi.n373,
    ofi.n374,
    ofi.n375,
    ofi.n376,
    ofi.n377,
    ofi.n378,
    ofi.n379,
    ofi.n380,
    ofi.n381,
    ofi.n382,
    ofi.n383,
    ofi.n384,
    ofi.n385,
    ofi.n386,
    ofi.n387,
    ofi.n388,
    ofi.n389,
    ofi.n390,
    ofi.n391,
    ofi.n392,
    ofi.n393,
    ofi.n394,
    ofi.n395,
    ofi.n396,
    ofi.n397,
    ofi.n398,
    ofi.n399,
    ofi.n400,
    ofi.n401,
    ofi.n402,
    ofi.n403,
    ofi.n404,
    ofi.n405,
    ofi.n406,
    ofi.n407,
    ofi.n408,
    ofi.n409,
    ofi.n410,
    ofi.n411,
    ofi.n412,
    ofi.n413,
    ofi.n414,
    ofi.n415,
    ofi.n416,
    ofi.n417,
    ofi.n418,
    ofi.n419,
    ofi.n420,
    ofi.n421,
    ofi.n422,
    ofi.n423,
    ofi.n424,
    ofi.n425,
    ofi.n426,
    ofi.n427,
    ofi.n428,
    ofi.n429,
    ofi.n430,
    ofi.n431,
    ofi.n432,
    ofi.n433,
    ofi.n434,
    ofi.n435,
    ofi.n436,
    ofi.n437,
    ofi.n438,
    ofi.n439,
    ofi.n440,
    ofi.n441,
    ofi.n442,
    ofi.n443,
    ofi.n444,
    ofi.n445,
    ofi.n446,
    ofi.n447,
    ofi.n448,
    ofi.n449,
    ofi.n450,
    ofi.n451,
    ofi.n452,
    ofi.n453,
    ofi.n454,
    ofi.n455,
    ofi.n456,
    ofi.n457,
    ofi.n458,
    ofi.n459,
    ofi.n460,
    ofi.n461,
    ofi.n462,
    ofi.n463,
    ofi.n464,
    ofi.n465,
    ofi.n466,
    ofi.n467,
    ofi.n468,
    ofi.n469,
    ofi.n470,
    ofi.n471,
    ofi.n472,
    ofi.n473,
    ofi.n474,
    ofi.n475,
    ofi.n476,
    ofi.n477,
    ofi.n478,
    ofi.n479,
    ofi.n480,
    ofi.n481,
    ofi.n482,
    ofi.n483,
    ofi.n484,
    ofi.n485,
    ofi.n486,
    ofi.n487,
    ofi.n488,
    ofi.n489,
    ofi.n490,
    ofi.n491,
    ofi.n492,
    ofi.n493,
    ofi.n494,
    ofi.n495,
    ofi.n496,
    ofi.n497,
    ofi.n498,
    ofi.n499,
    ofi.n500,
    ofi.t01,
    ofi.t02,
    ofi.t03,
    ofi.t04,
    ofi.t05,
    ofi.t06,
    ofi.t07,
    ofi.t08,
    ofi.t09,
    ofi.t10,
    ofi.t11,
    ofi.t12,
    ofi.t13,
    ofi.t14,
    ofi.t15,
    ofi.t16,
    ofi.t17,
    ofi.t18,
    ofi.t19,
    ofi.t20
   FROM (((public.obj_head obh
     JOIN public.acquisitions acq ON ((obh.acquisid = acq.acquisid)))
     JOIN public.samples sam ON ((acq.acq_sample_id = sam.sampleid)))
     LEFT JOIN public.obj_field ofi ON ((obh.objid = ofi.objfid)));


ALTER TABLE public.objects OWNER TO postgres;

--
-- Name: TABLE objects; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.objects TO zoo;
GRANT SELECT ON TABLE public.objects TO readerole;

-- Running upgrade 1b1beb672279 -> 52a9d347f2b2

DROP INDEX "IS_AcquisOrigId";

CREATE UNIQUE INDEX is_acquis_sample_orig_id ON acquisitions (acq_sample_id, orig_id) INCLUDE (acquisid);

DROP INDEX "IS_SamplesProjectOrigId";

CREATE UNIQUE INDEX is_samples_project_orig_id ON samples (projid, orig_id) INCLUDE (sampleid);

UPDATE alembic_version SET version_num='52a9d347f2b2' WHERE alembic_version.version_num = '1b1beb672279';

COMMIT;

-- Running upgrade 52a9d347f2b2 -> 4e25988b1e56

DROP TABLE temp_tasks;

CREATE TABLE images_new (
    imgid bigint NOT NULL,
    objid bigint NOT NULL,
    imgrank smallint NOT NULL,
    width smallint NOT NULL,
    height smallint NOT NULL,
    orig_file_name character varying(255) NOT NULL,
    thumb_width smallint,
    thumb_height smallint
);

ALTER TABLE images_new OWNER TO postgres;

DO
$$
    DECLARE
        chunk     integer = 1000000;
        total_row_count integer = 0;
        nb_chunks integer = 0;
        row_count integer;
        acq_rec record;
    BEGIN
        FOR acq_rec IN (SELECT acquisid FROM acquisitions ORDER BY acquisid)
            LOOP
                insert into images_new (imgid, objid, imgrank,
                                       orig_file_name, width, height,
                                       thumb_width, thumb_height)
                select imgid, img.objid,
                       case when imgrank > 32767 then 32767 else imgrank end,
                       orig_file_name,
                       case when width > 32767 then 32767-width else width end,
                       height,
                       thumb_width, thumb_height
                from images img
                join obj_head obh on img.objid = obh.objid
                where obh.acquisid = acq_rec.acquisid
                order by img.objid, img.imgrank;
                GET DIAGNOSTICS row_count = ROW_COUNT;
                total_row_count = total_row_count + row_count;
                IF total_row_count / chunk > nb_chunks
                THEN
                    nb_chunks = total_row_count / chunk;
                    RAISE NOTICE '%: Done % lines',current_time,total_row_count;
                    -- COMMIT; -- No commit inside Alembic
                END IF ;
            END LOOP;
    END;
$$;

ALTER TABLE ONLY images_new
    ADD CONSTRAINT images_pkey_new PRIMARY KEY (objid, imgrank);

ANALYSE images_new;

ALTER TABLE images RENAME TO images_old;

ALTER TABLE images_new RENAME TO images;

ALTER INDEX images_pkey RENAME TO images_pkey_old;

ALTER INDEX images_pkey_new RENAME TO images_pkey;

DROP TABLE image_file;

CREATE TABLE image_file (
    imgid BIGINT NOT NULL,
    ext CHAR(3) DEFAULT '?' NOT NULL,
    state CHAR DEFAULT '?' NOT NULL,
    digest_type CHAR DEFAULT '?' NOT NULL,
    digest BYTEA,
    PRIMARY KEY (imgid)
);

ALTER TABLE image_file OWNER TO postgres;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO zoo;

UPDATE alembic_version SET version_num='4e25988b1e56' WHERE alembic_version.version_num = '52a9d347f2b2';

-- Running upgrade 4e25988b1e56 -> 0a3132f436fb
ALTER TABLE users ADD COLUMN orcid VARCHAR(20) DEFAULT NULL;
UPDATE alembic_version SET version_num='0a3132f436fb' WHERE alembic_version.version_num = '4e25988b1e56';

-- Running upgrade 0a3132f436fb -> a9dd3c62b7b0

CREATE TABLE obj_cnn_features_vector (
    objcnnid BIGINT NOT NULL,
    features VECTOR(50),
    PRIMARY KEY (objcnnid),
    FOREIGN KEY(objcnnid) REFERENCES obj_head (objid) ON DELETE CASCADE
);

INSERT INTO obj_cnn_features_vector (objcnnid, features)
        SELECT objcnnid, ARRAY[cnn01, cnn02, cnn03, cnn04, cnn05, cnn06, cnn07, cnn08, cnn09, cnn10,
        cnn11, cnn12, cnn13, cnn14, cnn15, cnn16, cnn17, cnn18, cnn19, cnn20,
        cnn21, cnn22, cnn23, cnn24, cnn25, cnn26, cnn27, cnn28, cnn29, cnn30,
        cnn31, cnn32, cnn33, cnn34, cnn35, cnn36, cnn37, cnn38, cnn39, cnn40,
        cnn41, cnn42, cnn43, cnn44, cnn45, cnn46, cnn47, cnn48, cnn49, cnn50]::vector
        FROM obj_cnn_features;

GRANT SELECT ON obj_cnn_features_vector TO readerole;

DROP TABLE obj_cnn_features;

UPDATE alembic_version SET version_num='a9dd3c62b7b0' WHERE alembic_version.version_num = '0a3132f436fb';

COMMIT;

BEGIN;
------------Running upgrade a9dd3c62b7b0->647290b6c4fc
ALTER TABLE projects ADD COLUMN access VARCHAR(1) NOT NULL DEFAULT '';
ALTER TABLE projects ADD COLUMN formulae VARCHAR(1000) DEFAULT NULL;
UPDATE alembic_version SET version_num='647290b6c4fc'; WHERE alembic_version.version_num = 'a9dd3c62b7b0';


-- Running upgrade a9dd3c62b7b0 -> d3bfaa54d544

ALTER TABLE obj_head SET (autovacuum_enabled = off);
    ALTER TABLE objectsclassifhisto SET (autovacuum_enabled = off);
    -- Save some time on inserts
    ALTER TABLE ONLY public.objectsclassifhisto
        DROP CONSTRAINT objectsclassifhisto_classif_who_fkey,
        DROP CONSTRAINT objectsclassifhisto_objid_fkey;

-- No classif_id, 777 lines as of 07/01/2024
    delete from objectsclassifhisto where classif_id is null;

-- Wrong classif_id, 8K lines as of 07/01/2024
    delete from objectsclassifhisto where classif_id not in (SELECT id from taxonomy);

-- Some 4K objects in PROD have an invalid classif_auto_id, for 'P' we need to recreate the fake prediction
    update obj_head
       set classif_auto_id=classif_id,
           classif_auto_score=coalesce(classif_auto_score, 1),
           classif_auto_when=coalesce(classif_auto_when,'01/01/1970')
     where classif_qual = 'P'
       and classif_auto_id is not null
       and classif_auto_id not in (SELECT id from taxonomy);

-- Some 4K objects in PROD have an invalid classif_auto_id, for 'V'/'D' we can just erase _auto*
    update obj_head
       set classif_auto_id=null,
           classif_auto_score=null,
           classif_auto_when=null
     where classif_qual in ('V','D')
       and classif_auto_id is not null
       and classif_auto_id not in (SELECT id from taxonomy);

-- Some 1.8M objects in PROD have an inconsistent classif_auto_id, as for 'P' it should be classif_id.
    -- It's probably the consequence of legacy "revert to predicted' code which did not care about _auto fields
    -- or "import update predicted" before 2024 cleanup.
    update obj_head
       set classif_auto_id=classif_id
     where classif_qual = 'P'
       and classif_auto_id != classif_id;

-- Some 'V' or 'D' objects in PROD have an inconsistent classif_auto_when, taking place after human validation.
    -- Maybe some version of EcoTaxa allowed to re-predict without state move. Delete the user-hidden 'P'.
    -- 4M objects
    update obj_head
       set classif_auto_id=null,
           classif_auto_score=null,
           classif_auto_when=null
     where classif_qual in ('V','D')
       and classif_auto_when > classif_when;

-- Some 'V' or 'D' objects in PROD have some history after the object.
    -- History should be strictly 'before the present', so remove history. We still have the data in obj_head.
    -- 4.8M history
    delete from objectsclassifhisto och
     using obj_head obh
     where obh.objid = och.objid
       and obh.classif_when <= och.classif_date
       and obh.classif_qual in ('V','D');

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
     where obh.objid = bap.objid;

-- 'P' is freshest row, we have avoided duplicate due to volunteer copy above, cleanup.
    -- 763K history in PROD, some should be cured by above fixes
    delete from objectsclassifhisto och
     using obj_head obh
     where obh.objid = och.objid
       and obh.classif_auto_when = och.classif_date
       and obh.classif_qual = 'P'
       and och.classif_qual = 'P';

-- Some 47K objects in PROD have an implied historical P with exact same date as a log with P,
    -- but different produced classification or score. Remove the faulty history, it's eventually re-created OK next step.
    delete from objectsclassifhisto och
     using obj_head obh
     where och.classif_qual = 'P'
       and och.objid = obh.objid
       and och.classif_date = obh.classif_auto_when
       and (och.classif_id != obh.classif_auto_id
            or och.classif_score != obh.classif_auto_score);

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
    drop table missing_ps;

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
       and och.classif_date = both_are_p.classif_date;

COMMIT;

vacuum full verbose analyze objectsclassifhisto;

BEGIN;

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
    drop table pred_in_last;

ALTER TABLE obj_head ADD FOREIGN KEY(classif_id) REFERENCES taxonomy (id);

ALTER TABLE obj_head ADD FOREIGN KEY(classif_auto_id) REFERENCES taxonomy (id);

COMMIT;

vacuum full verbose analyze objectsclassifhisto;

BEGIN;

ALTER TABLE objectsclassifhisto ADD FOREIGN KEY(classif_id) REFERENCES taxonomy (id) ON DELETE CASCADE;

ALTER TABLE ONLY public.objectsclassifhisto
        ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users (id),
        ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
    ALTER TABLE obj_head SET (autovacuum_enabled = on);
    ALTER TABLE objectsclassifhisto SET (autovacuum_enabled = on);

UPDATE alembic_version SET version_num='d3bfaa54d544' WHERE alembic_version.version_num = 'a9dd3c62b7b0';

COMMIT;

BEGIN;

-- Running upgrade d3bfaa54d544 -> 067cd670782d

CREATE TABLE training (
    training_id SERIAL NOT NULL,
    projid INTEGER,
    training_author INTEGER NOT NULL,
    training_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    training_end TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    training_path VARCHAR(80) NOT NULL,
    PRIMARY KEY (training_id),
    FOREIGN KEY(training_author) REFERENCES users (id),
    FOREIGN KEY(projid) REFERENCES projects (projid) ON DELETE CASCADE
);

CREATE UNIQUE INDEX trn_projid_start ON training (projid, training_start);

CREATE TABLE prediction (
    object_id BIGINT NOT NULL,
    training_id INTEGER NOT NULL,
    classif_id INTEGER NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (object_id, classif_id),
    FOREIGN KEY(classif_id) REFERENCES taxonomy (id) ON DELETE CASCADE,
    FOREIGN KEY(object_id) REFERENCES obj_head (objid) ON DELETE CASCADE,
    FOREIGN KEY(training_id) REFERENCES training (training_id) ON DELETE CASCADE
);

CREATE INDEX is_prediction_training ON prediction (training_id);

CREATE TABLE prediction_histo (
    object_id BIGINT NOT NULL,
    training_id INTEGER NOT NULL,
    classif_id INTEGER NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (training_id, object_id, classif_id),
    FOREIGN KEY(classif_id) REFERENCES taxonomy (id) ON DELETE CASCADE,
    FOREIGN KEY(object_id) REFERENCES obj_head (objid) ON DELETE CASCADE,
    FOREIGN KEY(training_id) REFERENCES training (training_id) ON DELETE CASCADE
);

CREATE INDEX is_prediction_histo_object ON prediction_histo (object_id);

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
    WHERE och.classif_qual = 'P';

create index on mig_obj_prj (projid, objid);
    ALTER TABLE mig_obj_prj SET (autovacuum_enabled = off);
    analyze mig_obj_prj;

-- Grouped writes of previous prediction tasks, per project & date
    create UNLOGGED table mig_unq_classif_per_proj as
    SELECT projid, classif_auto_when, count(objid) as nb_objs
    from mig_obj_prj
    group by projid, classif_auto_when;

-- Look for start and end dates of prediction tasks
    -- assuming that 5 minutes have elapsed b/w 2 tasks on same project (time for human to read a bit the result)
    create UNLOGGED table mig_classif_chunks_per_proj as
    SELECT case when delta_prev > '44 sec' then 'B' end as B,
       case when delta_next > '44 sec' then 'E' end as E,
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
    where (delta_next > '44 sec'
    or delta_prev > '44 sec')
    order by projid, classif_auto_when;

-- Reconstituted (approximately) old tasks
    create UNLOGGED table mig_classif_tasks as
    SELECT projid,
       classif_auto_when as begin_date,
       (SELECT classif_auto_when
        from mig_classif_chunks_per_proj mcc2
        where mcc2.classif_auto_when >= mcc.classif_auto_when
          and mcc2.projid = mcc.projid
          and mcc2.delta_next > '44 sec'
        order by mcc2.classif_auto_when
        limit 1) as end_date
    from mig_classif_chunks_per_proj mcc
    where delta_prev > '44 sec';

create unique index on mig_classif_tasks (projid, begin_date, end_date);
    analyze mig_classif_tasks;

-- Each task becomes a training.
    -- Note that some old tasks have the _same_ begin_date for different projects.
    insert into training (projid, training_author, training_start, training_end, training_path)
    select mct.projid, 1, mct.begin_date, mct.end_date, 'Migrated ' || current_date
      from mig_classif_tasks mct;

analyze training;

create UNLOGGED table mig_obj_prj2 as select mop.*, trn.training_id
                    from mig_obj_prj mop
                             join training trn on mop.projid = trn.projid and
                                                  mop.classif_auto_when between trn.training_start and trn.training_end;
    create index on mig_obj_prj2 (projid, objid);
    create unique index on mig_obj_prj2 (objid, classif_auto_when); -- An object could not be moved state twice at same time
    analyze mig_obj_prj2;
    ALTER TABLE mig_obj_prj2 SET (autovacuum_enabled = off);

COMMIT;

vacuum full verbose mig_obj_prj2;

BEGIN;

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
$$;

analyze prediction;
    analyze prediction_histo;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole;

UPDATE alembic_version SET version_num='067cd670782d' WHERE alembic_version.version_num = 'd3bfaa54d544';

COMMIT;

BEGIN;

-- Running upgrade 067cd670782d -> 565015aa8282

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
ALTER TABLE ONLY public.obj_cnn_features_vector
    DROP CONSTRAINT obj_cnn_features_vector_objcnnid_fkey;
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
CREATE INDEX is_obj_head_acquisid_objid ON public.obj_head USING btree (acquisid, objid);
CREATE INDEX is_objectsdate ON public.obj_head USING btree (objdate) INCLUDE (acquisid);
CREATE INDEX is_objectsdepth ON public.obj_head USING btree (depth_max, depth_min) INCLUDE (acquisid);
CREATE INDEX is_objectslatlong ON public.obj_head USING btree (latitude, longitude) INCLUDE (acquisid);
CREATE INDEX is_objectstime ON public.obj_head USING btree (objtime) INCLUDE (acquisid);


ALTER TABLE public.obj_head
    CLUSTER ON is_obj_head_acquisid_objid;

ALTER TABLE ONLY public.obj_cnn_features_vector
    ADD CONSTRAINT obj_cnn_features_vector_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES public.obj_head (objid) ON DELETE CASCADE;
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

ANALYSE obj_head;

drop view objects;
    create view objects as
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
         left join obj_field ofi on obh.objid = ofi.objfid; -- allow elimination by planner
    grant select on objects to zoo;
    grant select on objects to readerole;

UPDATE alembic_version SET version_num='565015aa8282' WHERE alembic_version.version_num = '067cd670782d';

COMMIT;

BEGIN;

-- Running upgrade 565015aa8282 -> dac2d438e6b5

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
ANALYSE objectsclassifhisto;

UPDATE alembic_version SET version_num='dac2d438e6b5' WHERE alembic_version.version_num = '565015aa8282';

COMMIT;

BEGIN;

-- Running upgrade dac2d438e6b5 -> 4045b161563b

delete from images
     where objid in (select images.objid
                       from images
                       left join obj_head on images.objid = obj_head.objid
                      where obj_head.objid is null);;

CREATE INDEX is_phy_image_file ON image_file (digest_type, digest);

ALTER TABLE images ADD FOREIGN KEY(objid) REFERENCES obj_head (objid);

UPDATE alembic_version SET version_num='4045b161563b' WHERE alembic_version.version_num = 'dac2d438e6b5';

COMMIT;

BEGIN;

-- Running upgrade 4045b161563b -> 032dfb7159d5

DROP TABLE dropped_process_26032024;

DROP TABLE objectsclassifhisto_old;

DROP TABLE proj_with_incon;

DROP INDEX mig_obj_prj2_objid_classif_auto_when_idx;

DROP INDEX mig_obj_prj2_projid_objid_idx;

DROP TABLE mig_obj_prj2;

DROP INDEX is_objectsacqclassifqual_old;

DROP INDEX is_objectsacquisition_old;

DROP INDEX is_objectsdate_old;

DROP INDEX is_objectsdepth_old;

DROP INDEX is_objectslatlong_old;

DROP INDEX is_objectstime_old;

DROP TABLE obj_head_old;

DROP INDEX mig_obj_prj_projid_objid_idx;

DROP TABLE mig_obj_prj;

DROP INDEX mig_classif_tasks_projid_begin_date_end_date_idx;

DROP TABLE mig_classif_tasks;

DROP TABLE dropped_samples_26032024;

DROP TABLE dropped_acquisitions_26032024;

DROP TABLE mig_states_04_10_2024;

DROP TABLE mig_classif_chunks_per_proj;

DROP TABLE mig_unq_classif_per_proj;

UPDATE alembic_version SET version_num='032dfb7159d5' WHERE alembic_version.version_num = '4045b161563b';
COMMIT;
BEGIN;

-- Running upgrade 032dfb7159d5 -> f38a881a1f6c

SET LOCAL maintenance_work_mem = '8GB';
SET LOCAL max_parallel_maintenance_workers = 8;
CREATE INDEX obj_cnn_features_vector_hv_ivfflat_l2_5k_idx ON obj_cnn_features_vector
 USING ivfflat ((features::halfvec(50)) halfvec_l2_ops) WITH (lists = 5000);

UPDATE alembic_version SET version_num='f38a881a1f6c' WHERE alembic_version.version_num = '032dfb7159d5';

COMMIT;

BEGIN;
-- Running upgrade f38a881a1f6c -> 78b24e7ba52b

ALTER TABLE projects ADD COLUMN access VARCHAR(1);
-- PUBLIC="1" when visible=True and no license
UPDATE projects SET access='1' WHERE visible=true AND (license='' OR license IS NULL);
-- OPEN ="2"  when visible=True and license = CC
UPDATE projects SET access='2' WHERE visible=true AND license!='' AND LOWER(license)!='copyright';

-- PRIVATE="0" when copyright or visible=False
UPDATE projects SET access='0' WHERE visible=false OR LOWER(license)='copyright';
ALTER TABLE projects ALTER COLUMN access SET NOT NULL;
ALTER TABLE projects ADD COLUMN formulae VARCHAR;

UPDATE alembic_version SET version_num='78b24e7ba52b' WHERE alembic_version.version_num = 'f38a881a1f6c';

COMMIT;
BEGIN;

-- Running upgrade 78b24e7ba52b -> e6dda08ff48b

CREATE TABLE organizations (
    id INTEGER SERIAL NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    directories VARCHAR(2000),
     PRIMARY KEY (id),
);

ALTER TABLE users ADD COLUMN type VARCHAR(10);

UPDATE users SET type='user';
ALTER TABLE users ALTER COLUMN type SET NOT NULL;

UPDATE users SET organisation='NULL' WHERE organisation IS NULL;
UPDATE users SET organisation=(SELECT TRIM(organisation) from users as u1 WHERE u1.id=users.id) ;
INSERT INTO organizations (name) SELECT DISTINCT organisation FROM users WHERE organisation IS NOT NULL;
ALTER TABLE users ADD CONSTRAINT users_organisation FOREIGN KEY(organisation) REFERENCES organizations(name);

UPDATE alembic_version SET version_num='e6dda08ff48b' WHERE alembic_version.version_num = '78b24e7ba52b';

COMMIT;
BEGIN;

-- INFO  [alembic.runtime.migration] Running upgrade e6dda08ff48b -> 9f8174c268da, organization_id
-- Running upgrade e6dda08ff48b -> 9f8174c268da

ALTER TABLE collection_orga_role ADD COLUMN organization_id INTEGER ;

ALTER TABLE collection_orga_role ADD CONSTRAINT collection_organization_fkey FOREIGN KEY(organization_id) REFERENCES organizations (id);
INSERT INTO organizations (name) SELECT DISTINCT organisation FROM collection_orga_role WHERE organisation IS NOT NULL AND NOT EXISTS (SELECT organizations.id FROM organizations  WHERE organisation=organizations.name);
UPDATE collection_orga_role SET organization_id=subquery.id FROM(SELECT id,name FROM organizations) AS subquery WHERE subquery.name LIKE collection_orga_role.organisation;
ALTER TABLE users ADD COLUMN organization_id INTEGER;
UPDATE users SET organization_id=subquery.id FROM(SELECT id,name FROM organizations) AS subquery WHERE subquery.name LIKE users.organisation;
ALTER TABLE users DROP CONSTRAINT users_organisation;
ALTER TABLE users ADD CONSTRAINT user_organization_fkey FOREIGN KEY(organization_id) REFERENCES organizations (id);
ALTER TABLE collection_orga_role ALTER COLUMN organization_id SET NOT NULL;
ALTER TABLE collection_orga_role DROP COLUMN organisation;
ALTER TABLE users DROP COLUMN organisation;
UPDATE alembic_version SET version_num='9f8174c268da' WHERE alembic_version.version_num = 'e6dda08ff48b';

COMMIT;

BEGIN;

-- INFO  [alembic.runtime.migration] Running upgrade 9f8174c268da -> fc9fb059120c, remove_project_description
-- Running upgrade 9f8174c268da -> fc9fb059120c
UPDATE projects SET comments = CONCAT(description,' Comments: ',comments);

UPDATE alembic_version SET version_num='fc9fb059120c' WHERE alembic_version.version_num = '9f8174c268da';

COMMIT;

-- Running upgrade fc9fb059120c -> 08807338f98d
BEGIN;

DROP INDEX worms_pp;

DROP TABLE worms;

ALTER TABLE taxonomy ADD COLUMN aphia_id INTEGER;

ALTER TABLE taxonomy ADD COLUMN rank VARCHAR(24);

DROP INDEX "IS_TaxonomySource";

CREATE INDEX "IS_TaxonomyAphiaId" ON taxonomy (aphia_id);

ALTER TABLE taxonomy DROP COLUMN id_source;

UPDATE alembic_version SET version_num='08807338f98d' WHERE alembic_version.version_num = 'fc9fb059120c';

COMMIT;
BEGIN;

-- Running upgrade 08807338f98d -> 287303b6d65c

ALTER TABLE collection_orga_role ADD COLUMN display_order INTEGER;

ALTER TABLE collection_user_role ADD COLUMN display_order INTEGER;

UPDATE alembic_version SET version_num='287303b6d65c' WHERE alembic_version.version_num = '08807338f98d';

COMMIT;


BEGIN;

-- Running upgrade 287303b6d65c -> ca50a945b178

ALTER TABLE taxo_recast ALTER COLUMN operation TYPE VARCHAR(32);

ALTER TABLE taxo_recast ADD FOREIGN KEY(project_id) REFERENCES projects (projid) ON DELETE CASCADE;

ALTER TABLE taxo_recast ADD FOREIGN KEY(collection_id) REFERENCES collection (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='ca50a945b178' WHERE alembic_version.version_num = '287303b6d65c';

COMMIT;

-- Running upgrade ca50a945b178 -> 9bf6b31796a2

CREATE INDEX is_acquis_sample ON acquisitions (acq_sample_id) INCLUDE (acquisid);

CREATE INDEX is_samples_project ON samples (projid) INCLUDE (sampleid);

UPDATE alembic_version SET version_num='9bf6b31796a2' WHERE alembic_version.version_num = 'ca50a945b178';

COMMIT;

-- Running upgrade 9bf6b31796a2 -> acf6f3fcb35c

CREATE TABLE user_quality (
    user_id INTEGER NOT NULL,
    password_strong BOOLEAN NOT NULL,
    check_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT user_quality_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

UPDATE alembic_version SET version_num='acf6f3fcb35c' WHERE alembic_version.version_num = '9bf6b31796a2';

COMMIT;

-- Running upgrade acf6f3fcb35c -> 5d49f4994e0c

DROP VIEW IF EXISTS objects;

DROP INDEX is_objectsacqclassifqual;

CREATE UNIQUE INDEX is_objectsacqclassifqual ON obj_head (acquisid, objid) INCLUDE (classif_qual, classif_id);

DROP INDEX is_obj_head_acquisid_objid;

DROP INDEX obj_field_acquisid_objfid_idx;

ALTER TABLE obj_field ALTER COLUMN acquis_id TYPE BIGINT;

CREATE UNIQUE INDEX obj_field_acquisid_objfid_idx ON obj_field (acquis_id, objfid) INCLUDE (n01, n02, n03, n04);

ALTER TABLE acquisitions DROP CONSTRAINT acquisitions_sampleid_fkey;

ALTER TABLE samples ALTER COLUMN sampleid TYPE BIGINT;

ALTER TABLE acquisitions ALTER COLUMN acq_sample_id TYPE BIGINT;

ALTER TABLE acquisitions ADD FOREIGN KEY(acq_sample_id) REFERENCES samples (sampleid) ON UPDATE CASCADE;

ALTER TABLE images DROP CONSTRAINT images_objid_fkey;

ALTER TABLE images ADD FOREIGN KEY(objid) REFERENCES obj_head (objid) ON UPDATE CASCADE;

ALTER TABLE obj_head DROP CONSTRAINT obj_head_acquisid_fkey;

ALTER TABLE acquisitions ALTER COLUMN acquisid TYPE BIGINT;

ALTER TABLE obj_head ALTER COLUMN acquisid TYPE BIGINT;

ALTER TABLE obj_head ADD FOREIGN KEY(acquisid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE obj_cnn_features_vector DROP CONSTRAINT obj_cnn_features_vector_objcnnid_fkey;

ALTER TABLE obj_cnn_features_vector ADD FOREIGN KEY(objcnnid) REFERENCES obj_head (objid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE obj_field DROP CONSTRAINT obj_field_objfid_fkey;

ALTER TABLE obj_field ADD FOREIGN KEY(objfid) REFERENCES obj_head (objid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE objectsclassifhisto DROP CONSTRAINT objectsclassifhisto_objid_fkey;

ALTER TABLE objectsclassifhisto ADD FOREIGN KEY(objid) REFERENCES obj_head (objid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE prediction DROP CONSTRAINT prediction_object_id_fkey;

ALTER TABLE prediction ADD FOREIGN KEY(object_id) REFERENCES obj_head (objid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE prediction_histo DROP CONSTRAINT prediction_histo_object_id_fkey;

ALTER TABLE prediction_histo ADD FOREIGN KEY(object_id) REFERENCES obj_head (objid) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE process DROP CONSTRAINT process_processid_fkey;

ALTER TABLE process ALTER COLUMN processid TYPE BIGINT;

ALTER TABLE process ADD FOREIGN KEY(processid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE ON UPDATE CASCADE;

CREATE OR REPLACE FUNCTION obj_in_prj(prj_id int)
RETURNS int8range AS $$
  SELECT int8range(
    prj_id * 100000000::bigint,
    (prj_id + 1) * 100000000::bigint,
    '[)'
  );
$$ LANGUAGE sql IMMUTABLE;

GRANT EXECUTE ON FUNCTION obj_in_prj(int) TO PUBLIC;;

CREATE OR REPLACE FUNCTION acq_in_prj(prj_id int)
RETURNS int8range AS $$
  SELECT int8range(
    prj_id * 10000000::bigint,
    (prj_id + 1) * 10000000::bigint,
    '[)'
  );
$$ LANGUAGE sql IMMUTABLE;

GRANT EXECUTE ON FUNCTION acq_in_prj(int) TO PUBLIC;;

CREATE OR REPLACE VIEW objects AS
SELECT prj.projid,
       sam.sampleid,
       obh.objid,
       obh.latitude,
       obh.longitude,
       obh.objdate,
       obh.objtime,
       obh.depth_min,
       obh.depth_max,
       obh.classif_id,
       obh.classif_qual,
       obh.classif_who,
       CASE WHEN obh.classif_qual IN ('V', 'D') THEN obh.classif_date END AS classif_when,
       obh.classif_score                                                  AS classif_auto_score,
       CASE WHEN obh.classif_qual = 'P' THEN obh.classif_date END         AS classif_auto_when,
       CASE WHEN obh.classif_qual = 'P' THEN obh.classif_id END           AS classif_auto_id,
       NULL::integer                                                      AS classif_crossvalidation_id,
       obh.complement_info,
       NULL::double precision                                             AS similarity,
       obh.sunpos,
       HASHTEXT(obh.orig_id)                                              AS random_value,
       obh.acquisid,
       obh.object_link,
       obh.orig_id,
       obh.acquisid                                                       AS processid,
       ofi.*
    FROM projects prj
    JOIN samples sam ON sam.projid = prj.projid
    JOIN acquisitions acq ON acq.acq_sample_id = sam.sampleid
    JOIN obj_head obh ON obh.acquisid = acq.acquisid AND obh.objid <@ obj_in_prj(prj.projid)
    LEFT JOIN obj_field ofi ON obh.objid = ofi.objfid;

UPDATE alembic_version SET version_num='5d49f4994e0c' WHERE alembic_version.version_num = 'acf6f3fcb35c';

COMMIT;

BEGIN;

-- Running upgrade 5d49f4994e0c -> e68bf28d2613

ALTER TABLE projects RENAME formulae TO formulae_old;

ALTER TABLE projects ADD COLUMN formulae JSONB;

-- SQL port of BO.Project._formulae_str_to_dict(), to backfill "formulae" from the
-- legacy "formulae_old" string (dict-like keys, no reliable separator between
-- entries: blank, \r, \r\n or nothing at all -- and "none", any case, meaning null).
DO $$
    DECLARE
        keys_pattern CONSTANT text := 'subsample_coef|total_water_volume|individual_volume';
        ws CONSTANT text := E' \t\n\r\x0B\x0C';
        -- SQL port of BO.Project.DEFAULT_FORMULAE: historical default formulae,
        -- not real user customizations, blanked out on read.
        default_formulae CONSTANT text[] := ARRAY[
            'total_water_volume/1000',
            '1/subsampling_coefficient',
            '4/3 * math.pi * (math.sqrt(area/math.pi)*pixel_size)**3',
            '4/3 * math.pi * (major_axis * pixel_size) * (minor_axis * pixel_size)**2',
            '4/3 * pi * (major_axis * pixel_size) * (minor_axis * pixel_size)^2'
        ];
        r RECORD;
        raw text;
        normalized text;
        chunk text;
        a_key text;
        a_val text;
        sep_pos int;
        result jsonb;
    BEGIN
        FOR r IN SELECT projid, formulae_old FROM projects WHERE formulae_old IS NOT NULL
            LOOP
                raw := btrim(r.formulae_old, ws);
                IF raw = '' OR lower(raw) = 'none' THEN
                    CONTINUE; -- formulae stays NULL, already the column default
                END IF;
                normalized := regexp_replace(raw, '\s*(' || keys_pattern || '):', ';\1:', 'g');
                result := '{}'::jsonb;
                FOR chunk IN SELECT unnest(string_to_array(normalized, ';'))
                    LOOP
                        chunk := btrim(chunk, ws);
                        IF chunk = '' THEN
                            CONTINUE;
                        END IF;
                        sep_pos := position(':' IN chunk);
                        IF sep_pos = 0 THEN
                            a_key := chunk;
                            a_val := '';
                        ELSE
                            a_key := substring(chunk FROM 1 FOR sep_pos - 1);
                            a_val := btrim(substring(chunk FROM sep_pos + 1), ws);
                        END IF;
                        IF a_val = ANY(default_formulae) THEN
                            a_val := '';
                        END IF;
                        IF a_val = '' OR lower(a_val) = 'none' THEN
                            CONTINUE; -- drop the key: empty, default or "none" value
                        END IF;
                        result := result || jsonb_build_object(a_key, a_val);
                    END LOOP;
                IF result = '{}'::jsonb THEN
                    result := NULL;
                END IF;
                UPDATE projects SET formulae = result WHERE projid = r.projid;
            END LOOP;
    END
$$;

UPDATE alembic_version SET version_num='e68bf28d2613' WHERE alembic_version.version_num = '5d49f4994e0c';

COMMIT;

BEGIN;

-- Running upgrade e68bf28d2613 -> c593af18f13a

UPDATE alembic_version SET version_num='c593af18f13a' WHERE alembic_version.version_num = 'e68bf28d2613';

COMMIT;

BEGIN;

-- Running upgrade c593af18f13a -> 890a5b01ab64

-- Organizations: EDMO (https://edmo.seadatanet.org/) reference in "directories" as "edmo:<id>",
-- EDMO name as organization name, and merge of organizations sharing the same EDMO id.
-- Matches come from the reviewed edmo_matches.xlsx: "manmatch" (an EDMO id) when filled,
-- else "imatch" = k meaning EDMO id "id_k" and name "name_k". NULL EDMO name: EDMO id only in
-- "manmatch", the organization keeps its name.
-- Traceability & downgrade: organizations_edmo_bak, users_organization_edmo_bak,
-- collection_orga_role_edmo_bak and organizations_edmo_log. Drop them once validated.

CREATE TABLE organizations_edmo_bak AS SELECT * FROM organizations;

CREATE TABLE users_organization_edmo_bak AS SELECT id, organization_id FROM users;

CREATE TABLE collection_orga_role_edmo_bak AS SELECT * FROM collection_orga_role;

CREATE OR REPLACE FUNCTION pg_temp.edmo_norm(nam TEXT) RETURNS TEXT
    LANGUAGE sql IMMUTABLE AS
$$ SELECT lower(regexp_replace(btrim(nam), '\s+', ' ', 'g')) $$;

CREATE TEMP TABLE edmo_match
(
    eco_id    INTEGER,
    eco_name  VARCHAR NOT NULL,
    edmo_id   INTEGER NOT NULL,
    edmo_name VARCHAR
) ON COMMIT DROP;

INSERT INTO edmo_match (eco_id, eco_name, edmo_id, edmo_name)
VALUES
        (2, 'Takuvik', 5318, 'Takuvik Joint Laboratory'),
        (4, 'Leibniz-Institute of Freshwater Ecology and Inland Fisheries (IGB)', 2200, 'Leibniz Institute of Freshwater Ecology and Inland Fisheries'),
        (6, 'Maine University - Umaine', 3827, 'University of Maine'),
        (15, 'Seoul National University', 3736, 'Seoul National University'),
        (18, 'Sun Yat-Sen University', 5545, 'Sun Yat Sen University'),
        (20, 'MARE - Marine and Environmental Sciences Centre', 5075, 'Polytechnic of Leiria'),
        (21, 'Max Planck Institute for Marine Microbiology', 5435, 'Max Planck Institute for Marine Microbiology'),
        (25, 'Santa Catarina Federal University - UFSC', 5213, 'Federal University of Santa Catarina'),
        (26, 'University of Illinois at Chicago', 3649, 'University of Illinois at Chicago'),
        (28, 'Rosenstiel School of Marine and Atmospheric Sciences - RSMAS', 1382, 'Rosenstiel School of Marine and Atmospheric Science , University of Miami'),
        (32, 'University of Hawai''i at Manoa', 1389, 'School of Ocean and Earth Science and Technology, University of Hawai''i at Manoa'),
        (34, 'Louisiana Universities Marine Consortium - LUMCON', 3106, 'Louisiana Universities Marine Consortium'),
        (37, 'University of Konstanz', 3198, 'University of Konstanz Limnological Institute'),
        (42, 'Russian Federal Research Institute', 760, 'Russian Federal Research Institute of Fishery and Oceanography'),
        (45, 'University of South Florida', 3838, 'University of South Florida'),
        (47, 'Universidad de Granada', 1744, NULL),
        (49, 'NUI Galway', 774, 'University of Galway'),
        (53, 'University of Technology Sydney', 4328, 'University of Technology, Sydney'),
        (54, 'Ghent University', 2581, NULL),
        (56, 'National Oceanography Centre - NOC', 17, 'National Oceanography Centre (Southampton)'),
        (57, 'Colgate University', 3530, 'Colgate University'),
        (59, 'Institut Mediterraneen d''Oceanographie (MIO, CNRS, IRD, AMU)', 3078, 'Mediterranean Institute of Oceanography (Marseille)'),
        (61, 'Sorbonne University - SU', 4962, 'Sorbonne University'),
        (63, 'university of maryland', 3828, 'University of Maryland'),
        (64, 'University of Washington', 3839, 'University of Washington'),
        (65, 'University of the South Pacific', 4358, 'The University of the South Pacific'),
        (66, 'University of Dubrovnik', 1335, 'Institute For Marine And Coastal Research, University Of Dubrovnik'),
        (67, 'PLOCAN', 3497, 'Oceanic Platform of the Canary Islands'),
        (69, 'Scripps University', 1390, 'Scripps Institution of Oceanography'),
        (71, 'Hokkaido University', 3094, 'Hokkaido University Graduate School of Environmental Science and Faculty of Environmental Earth Science'),
        (72, 'Polar research institute of China', 5789, 'Polar Research Institute of China'),
        (74, 'Maine University - UMaine', 3827, 'University of Maine'),
        (76, 'Vlaams Instituut voor de Zee', 422, 'Flanders Marine Institute'),
        (77, 'Institut Méditerranéen d''Océanologie', 3078, 'Mediterranean Institute of Oceanography (Marseille)'),
        (78, 'Fisheries and Marine Institute at Memorial University of Newfoundland - MIMUN', 2759, 'Memorial University of Newfoundland, Fisheries and Marine Institute'),
        (80, 'University of Auckland', 2249, 'University of Auckland, Leigh Marine Laboratory'),
        (81, 'Massachusetts Institute of Technology - MIT', 3804, 'Massachusetts Institute of Technology'),
        (83, 'NOAA SEFSC', 3121, NULL),
        (84, 'Sea Education Association', 3183, 'Sea Education Association'),
        (85, 'Thünen Institute for Sea Fisheries', 1570, 'Thünen-Institute of Sea Fisheries'),
        (86, 'Heinrich Heine University', 3484, 'Heinrich-Heine-University Düsseldorf'),
        (87, 'Cyprus Subsea Consulting and Services Ltd', 5516, 'Cyprus Subsea Consulting and Services'),
        (90, 'GEOMAR Helmholtz Centre for Ocean Research Kiel', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (93, 'UCSD', 3790, 'University of California, San Diego'),
        (95, 'Somerset Wildlife Trust', 5037, 'Somerset Wildlife Trust'),
        (97, 'Essex Wildlife Trust', 5347, 'Essex Wildlife Trust'),
        (100, 'Center for Mathematical Modeling', 5171, 'University of Chile'),
        (101, 'University of Edinburgh', 4945, 'University of Edinburgh'),
        (102, 'Lund university', 5373, 'Lund University, Department of Biology'),
        (103, 'Bermuda Institute of Ocean Sciences - BIOS', 1383, 'Bermuda Institute of Ocean Sciences'),
        (106, 'Parc naturel marin du golfe du Lion', 4869, 'Marine Natural Park of Lion Gulf'),
        (108, 'University of Hawaii at Manoa', 1389, 'School of Ocean and Earth Science and Technology, University of Hawai''i at Manoa'),
        (109, 'NOAA', 1433, 'National Oceanic and Atmospheric Administration'),
        (110, 'University of Texas at Austin', 4475, 'The University of Texas at Austin'),
        (113, 'Lancashire Wildlife Trust', 667, 'The Wildlife Trust for Lancashire, Manchester and North Merseyside (Charity No. 229325)'),
        (117, 'Centro Ciências do Mar', 2516, 'University of Algarve, Marine Sciences Centre'),
        (118, 'Charles University', 5611, 'Charles University'),
        (120, 'University of Malaya', 3026, 'University of Malaya, Institute of Biological Sciences'),
        (122, 'Ocean Sciences Institute of Rimouski - ISMER', 3361, 'University of Quebec at Rimouski, Institut des Sciences de la Mer'),
        (125, 'University of New Brunswick', 5114, 'University of New Brunswick, Saint John Campus, Department of Biological Sciences'),
        (126, 'Ifremer Boulogne-sur-Mer', 542, 'IFREMER, Fisheries English Channel North sea (Boulogne-sur-mer)'),
        (127, 'LOV, SU', 4962, 'Sorbonne University'),
        (129, 'Las Palmas de Gran Canaria University - ULPGC', 1398, 'University of Las Palmas de Gran Canaria. Faculty of Marine Science.'),
        (130, 'Earth Rearch Institude, UCSB', 3820, 'University of California, Santa Barbara'),
        (133, 'University of Southampton', 4457, 'University of Southampton'),
        (134, 'European Bioinformatics Institute - EMBL', 5931, 'European Molecular Biology Laboratory - European Bioinformatics Institute'),
        (135, 'Marine Biological Association of the UK', 45, 'Marine Biological Association of the United Kingdom'),
        (137, 'Washington University - WUSTL', 3842, 'Washington University in St. Louis'),
        (138, 'University of Geneva', 2434, 'University of Geneva, Institute of Environmental Sciences'),
        (139, 'Bigelow Laboratory for Ocean Sciences', 1555, 'Bigelow Laboratory for Ocean Sciences'),
        (141, 'University of Delaware School of Marine Science and Policy', 3825, 'University of Delaware'),
        (147, 'Southern Mississippi University - USM', 3837, 'University of Southern Mississippi'),
        (148, 'Weizmann Institute of Science', 5766, 'Weismann Institute of Science'),
        (150, 'U. Miami CIMAS / NOAA AOML', 1799, 'Atlantic Oceanographic and Meteorological Laboratory , National Oceanic and Atmospheric Administration'),
        (151, 'University of Gdansk', 576, 'University of Gdansk, Institute of Oceanography'),
        (153, 'Ocean Systems Laboratory, Inc.', 92, 'Heriot-Watt University, Ocean Systems Laboratory'),
        (154, 'NOAA-AOML', 1799, 'Atlantic Oceanographic and Meteorological Laboratory , National Oceanic and Atmospheric Administration'),
        (155, 'Rhode Island University - URI', 3833, 'University of Rhode Island'),
        (156, 'université laval', 2076, 'Université Laval'),
        (157, 'Institut des sciences de la mer de Rimouski', 3361, 'University of Quebec at Rimouski, Institut des Sciences de la Mer'),
        (160, 'Universidad de Concepcion', 1991, 'Universidad de Concepcion, Conception University'),
        (161, 'Istanbul University - IU', 802, 'Istanbul University, Institute of Marine Science and Management'),
        (163, 'United Nations Educational, Scientific and Cultural Organization - UNESCO', 4959, 'United Nations Educational ( SCIENTIFIC AND CULTURAL ORGANIZATION -UNESCO)'),
        (164, 'Jet Propulsion Laboratory, California Institute of Technology', 3797, 'California Institute of Technology'),
        (166, 'South African Environmental Observation Network', 4639, 'South African Environmental Observation Network'),
        (167, 'Leibniz Institut für Ostseeforschung Warnemünde', 100, 'Leibniz Institute for Baltic Sea Research Warnemünde'),
        (168, 'Latvian Institute of Aquatic Ecology', 698, 'Latvian Institute of Aquatic Ecology'),
        (169, 'California University of Berkeley - UCB', 3818, 'University of California, Berkeley'),
        (172, 'Sorbonne University - OEM - SU', 4962, 'Sorbonne University'),
        (173, 'universidad de valparaíso', 3728, 'Pontificia Universidad Católica de Valparaíso'),
        (174, 'Prince William Sound Science Center', 3606, 'Prince William Sound Science Center'),
        (177, 'Georgia Institute of Technology', 3075, 'Georgia Institute of Technology'),
        (179, 'University of Queensland', 3025, 'University of Queensland'),
        (180, 'Heriot-Watt University', 1551, 'Herriot-Wyatt University'),
        (182, 'eth zurich', 5230, 'ETH Zürich'),
        (185, 'Plymouth Marine Laboratory', 47, 'Plymouth Marine Laboratory'),
        (186, 'Sorbonne Universite', 4962, 'Sorbonne University'),
        (188, 'Jacobs University Bremen', 2305, 'Jacobs University Bremen, School of Engineering and Science'),
        (191, 'University of Manchester', 5117, 'University of Manchester, School of Archaeology'),
        (192, 'Qatar University', 5840, 'Environmental Science Center, Qatar University'),
        (193, 'Global Biodiversity Information Facility (GBIF)', 2421, NULL),
        (194, 'Institute of Marine Ecosystem and Fishery Science - IMF, University of Hamburg', 4989, 'Institute of Marine Ecosystem and Fishery Science, University of Hamburg'),
        (195, 'institut national des sciences et technologies de la mer', 1232, 'Institut National des Sciences et Technologies de la Mer'),
        (197, 'Institute of Marine Research, IMR, Norway', 566, 'Institute of Marine Research'),
        (200, 'Observatory of Universe Sciences Pytheas Institute - OSU', 3925, 'Pythéas Institute, OSU'),
        (201, 'HCMR', 3051, 'Hellenic Centre for Marine Research (HCMR)'),
        (202, 'university of geneve', 2434, 'University of Geneva, Institute of Environmental Sciences'),
        (203, 'Hydroptic', 5541, 'Hydroptic'),
        (204, 'Western Washington University', 3843, 'Western Washington University'),
        (205, 'International Research Institute of Stavanger - IRIS', 1747, 'International Research Institute of Stavanger'),
        (206, 'OKEANOS, Univerity of the Azores', 5450, 'University of Azores, Institute of Marine Sciences'),
        (211, 'NIWA', 3191, 'National Institute of Water and Atmospheric Research'),
        (212, 'Mediterranean Institute of Oceanology - MIO', 3078, 'Mediterranean Institute of Oceanography (Marseille)'),
        (213, 'Dauphin Island Sea Lab', 3769, 'Dauphin Island Sea Lab'),
        (214, 'Stanford University', 3812, 'Stanford University'),
        (219, 'Université du Littoral et de la Cote d''Opale', 2910, NULL),
        (225, 'University of Tromsø', 1636, 'University of Tromsø'),
        (227, 'Oceanological Observatory of Banyuls sur Mer - OOB', 1015, 'Oceanologic Observatory of Banyuls, University of Paris VI, OSU'),
        (228, 'Oceanographic center of Cadiz', 1406, 'IEO-CSIC, Cadiz Oceanographic Centre'),
        (230, 'Ifremer Nantes - IFREMER', 1913, 'Ifremer Centre de Nantes'),
        (232, 'Toulon University', 4625, 'Mediterranean Institute Of Oceanography (Toulon)'),
        (233, 'INSTITUOI ESPAÑOL DE OCEANOGRAFÍA', 353, NULL),
        (237, 'université de la Rochelle', 3134, 'University of La Rochelle'),
        (238, 'Bordeaux University', 2884, 'University of Bordeaux'),
        (241, 'Commonwealth Scientific and Industrial Research Organisation - CSIRO', 3945, 'Commonwealth Scientific and Industrial Research Organisation'),
        (243, 'okeanos', 5388, 'Okeanos'),
        (245, 'University of New Hampshire', 3831, 'University of New Hampshire'),
        (246, 'University of Connecticut', 3824, 'University of Connecticut'),
        (248, 'Japan Agency for Marine-Earth Science and Technology (JAMSTEC)', 1537, 'Japan Agency for Marine-Earth Science and Technology'),
        (250, 'University of Liverpool', 2748, NULL),
        (253, 'Geomar Helmholtz Center for Ocean Research Kiel', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (254, 'CCHDO', 3790, 'University of California, San Diego'),
        (255, 'Hokkaido University - Graduate School of Fisheries Sciences', 3094, 'Hokkaido University Graduate School of Environmental Science and Faculty of Environmental Earth Science'),
        (262, 'Texas A&M University at Galveston', 3814, 'Texas A&M University'),
        (264, 'university of hull', 4455, 'University of Hull'),
        (268, 'University sao paulo', 1782, 'University of Sao Paulo'),
        (269, 'University of Louisiana at Lafayette', 3650, 'University of Louisiana at Lafayette'),
        (277, 'Stony Brook University', 3813, 'Stony Brook University'),
        (280, 'University of California Santa Cruz', 3821, 'University of California, Santa Cruz'),
        (282, 'MARBEC', 5039, 'MARBEC Montpellier'),
        (283, 'MARUM', 1568, 'Center for Marine Environmental Sciences, University of Bremen'),
        (286, 'National Research Council of Italy', 4809, 'National Research Council of Italy, Institute for Marine and Coastal Environment, Capo Granitola'),
        (289, 'National Institute for Environmental Studies', 4528, 'National Institute for Environmental Studies'),
        (290, 'Sao Paulo University - USP', 1782, 'University of Sao Paulo'),
        (291, 'Department of Forestry, Fisheries and Environment', 5195, 'Department of Environment Fisheries and Forest'),
        (295, 'Universidade de São Paulo', 1782, 'University of Sao Paulo'),
        (297, 'Oceanographic Laboratory of Villefranche sur Mer - LOV', 490, NULL),
        (299, 'University of Nevada Reno', 3659, 'University of Nevada, Reno'),
        (300, 'Leibniz Centre for Tropical Marine Research - ZMT', 4884, 'Leibniz Centre for Tropical Marine Research'),
        (303, 'Sea Watch Foundation', 2560, 'Sea Watch Foundation'),
        (304, 'INRH INSTITUT NATIONAL DE RECHERCHE HALIEUTIQUE', 691, 'National Institute of Fisheries Research'),
        (305, 'Alberta University', 4162, 'University of Alberta'),
        (306, 'national taiwan ocean university', 5032, 'National Taiwan University Institute of Oceanography'),
        (310, 'Scottish Assosceation for Marine Science', 44, 'Scottish Association for Marine Science'),
        (312, 'STAZIONE ZOOLOGICA ANTON DORHN', 237, 'Stazione Zoologica Anton Dohrn of Naples'),
        (313, 'Developmental Biology Laboratory of Villefranche sur Mer - LBDV', 529, 'Developmental Biology Research Laboratory of Villefranche'),
        (317, 'Geomar Kiel', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (321, 'University of Maine', 3827, 'University of Maine'),
        (323, 'Pernambuco Federal University - UFPE', 5842, 'Universidade Federal de Pernambuco'),
        (324, 'Louisiana Lafayette University - ULL', 3650, 'University of Louisiana at Lafayette'),
        (326, 'Shannon Point Marine Center', 3843, 'Western Washington University'),
        (327, 'Thünen Institute', 1570, 'Thünen-Institute of Sea Fisheries'),
        (328, 'University of Cape Town', 1781, 'University of Cape Town, Department of Oceanography'),
        (329, 'KENT WILDLIFE TRUST', 3203, 'Kent Wildlife Trust'),
        (333, 'marine biological association of the united kingdom', 45, 'Marine Biological Association of the United Kingdom'),
        (334, 'Woods Hole Oceanographic Institution - WHOI', 3844, 'Woods Hole Oceanographic Institution'),
        (337, 'Institute of Marine Sciences - ICM', 2157, 'Institute of Marine Sciences, Mediterranean Marine and Environmental Research Centre, Department of Marine Science'),
        (338, 'Helmholtz-Zentrum Geesthacht Centre for Materials and Coastal Research - HZG', 2842, 'Helmholtz-Zentrum Geesthacht, Centre for Materials and Coastal Research'),
        (339, 'McGill University', 4156, 'McGill University'),
        (342, 'Duke University', 3798, 'Duke University'),
        (345, 'Uni Heidelberg', 3433, 'University of Heidelberg'),
        (348, 'Center for Marine Biology, University of São Paulo', 1782, 'University of Sao Paulo'),
        (349, 'The First Institute of Oceanography.MNR', 4640, NULL),
        (352, 'San Francisco State University', 3810, 'San Francisco State University'),
        (353, 'Universidad de Valparaíso', 3728, 'Pontificia Universidad Católica de Valparaíso'),
        (360, 'National Institute of Polar Research', 4368, 'National Institute of Polar Research'),
        (363, 'Princeton University', 3809, 'Princeton University'),
        (367, 'VIMS', 3157, 'Virginia Institute of Marine Science'),
        (373, 'Plymouth University', 2922, 'University of Plymouth'),
        (374, 'Marine Scotland Science - MSS', 4335, 'Marine Scotland Science, Freshwater Laboratory'),
        (375, 'Universidade Federal do Rio Grande', 3169, 'Federal University of Rio Grande Institute of Oceanography'),
        (378, 'The University of South Florida', 3838, 'University of South Florida'),
        (381, 'University Hamburg', 3323, 'University of Hamburg'),
        (382, 'EMBRC-ERIC', 5669, NULL),
        (383, 'Gothenburg University - GU', 3984, 'University of Gothenburg'),
        (384, 'Svalbard University - UNIS', 1420, NULL),
        (386, 'deltares', 1528, 'Deltares'),
        (387, 'Akvaplan-niva AS', 1410, 'Akvaplan-NIVA AS'),
        (388, 'Universidad de Vigo', 2163, 'University of Vigo'),
        (391, 'Stareso', 4501, NULL),
        (394, 'CNRS - Sorbonne University', 4962, 'Sorbonne University'),
        (395, 'Roscoff Biological Station - SBR', 521, 'Roscoff Marine Station, Sorbonne Université and CNRS'),
        (396, 'The University of Texas', 4475, 'The University of Texas at Austin'),
        (399, 'Federal University of Pernambuco', 5842, 'Universidade Federal de Pernambuco'),
        (400, 'university of miami', 3829, 'University of Miami'),
        (401, 'Akvaplan-niva', 1410, 'Akvaplan-NIVA AS'),
        (403, 'Swedish Meteorological and Hydrological Institute - SMHI', 545, 'Swedish Meteorological and Hydrological Institute'),
        (404, 'NIOZ Royal Netherlands Institute for Sea Research', 630, 'Royal Netherlands Institute for Sea Research'),
        (409, 'University of Bremen', 1157, 'University of Bremen'),
        (410, 'Florida Atlantic University', 3543, 'Florida Atlantic University'),
        (416, 'South Florida University - College of Marine Science - USF', 1462, 'University of South Florida, College of Marine Science'),
        (417, 'Woods Hole Oceanographic Institution', 3844, 'Woods Hole Oceanographic Institution'),
        (418, 'University of Cantabria', 5162, 'University of Cantabria'),
        (419, 'Ocean University of China', 4540, 'Ocean University of China, Department of Ocean Engineering'),
        (422, 'University College Dublin', 775, 'University College Dublin'),
        (426, 'Hebrew University of Jerusalem', 5764, 'The Hebrew University of Jerusalem'),
        (427, 'University of Wisconsin - Madison', 3840, 'University of Wisconsin-Madison'),
        (430, 'Havforskningsinstituttet', 4827, 'Institute of Marine Research Tromsø'),
        (432, 'Arctic and Antarctic Reseach Institute', 684, 'Arctic and Antarctic Research Institute, Roshydromet (Saint-Petersburg)'),
        (435, 'UC Davis', 3645, 'University of California, Davis'),
        (436, 'Norwegian Institute for Water Research, University of Oslo', 778, 'University of Oslo'),
        (437, 'National Taiwan University', 5032, 'National Taiwan University Institute of Oceanography'),
        (444, 'hereon', 5403, 'Helmholtz-Zentrum Hereon GmbH'),
        (447, 'University of Oxford', 2499, NULL),
        (449, 'University of South Carolina', 3835, 'University of South Carolina'),
        (450, 'Queens university belfast', 4943, 'The Queen''s University of Belfast'),
        (452, 'SINTEF', 1547, 'SINTEF'),
        (454, 'Flanders Marine Institute - VLIZ', 422, 'Flanders Marine Institute'),
        (457, 'SBR', 521, 'Roscoff Marine Station, Sorbonne Université and CNRS'),
        (459, 'ulpgc', 5269, 'ULPGC, ECOAQUA Institute, University of Las Palmas de Gran Canaria'),
        (461, 'Ifremer', 1054, 'Ifremer Head Office'),
        (462, 'Manitoba University', 6071, 'University of Manitoba'),
        (463, 'NTNU', 1419, 'Norwegian University of Science and Technology'),
        (467, 'Rutgers University - RU', 1435, 'Rutgers, The State University of New Jersey, Institute of Marine and Coastal Sciences'),
        (468, 'National Oceanic and Atmospheric Administration', 1433, 'National Oceanic and Atmospheric Administration'),
        (469, 'Memorial University of Newfoundland', 2649, 'Memorial University of Newfoundland, Ocean Sciences Centre'),
        (471, 'DFO', 5370, 'Fisheries and Oceans Canada'),
        (475, 'European Molecular Biology Laboratory - EMBL', 5931, 'European Molecular Biology Laboratory - European Bioinformatics Institute'),
        (477, 'università ca'' foscari di venezia', 5052, 'Ca'' Foscari University of Venice'),
        (479, 'Anton Dohrn Zoological Station - SZN', 237, 'Stazione Zoologica Anton Dohrn of Naples'),
        (481, 'Korea Institute of Ocean Science and Technology', 3332, 'Korea Institute Of Ocean Science & Technology'),
        (482, 'Technical University of Denmark, National Institute of Aquatic Resources (DTU Aqua)', 2195, 'DTU Aqua, National Institute of Aquatic Resources, Technical University of Denmark'),
        (483, 'Universidade da Madeira', 3028, 'University of Madeira, Marine Biological Station of Funchal'),
        (484, 'ALSEAMAR', 5241, 'ALSEAMAR'),
        (486, 'University of Bristol', 1475, NULL),
        (489, 'Sea Institute of Villefranche sur Mer - IMEV', 5041, NULL),
        (490, 'Zagreb University - BIOL - PMF', 707, 'Andrija Mohorovicic Geophysical Institute, University of Zagreb'),
        (493, 'Department Fisheries and Oceans', 5370, 'Fisheries and Oceans Canada'),
        (499, 'Hub Ocean', 5937, 'HUB Ocean'),
        (500, 'Buenos Aires University - UBA', 6064, 'National Scientific and Technical Research Council, Center for Marine and Atmospheric Research, University of Buenos Aires'),
        (501, 'University of Rhode Island, Graduate School of Oceanography', 1445, 'University of Rhode Island, Graduate School of Oceanography'),
        (502, 'Helmholtz Centre for Environmental Research - UFZ', 1152, 'Helmholtz Centre for Environmental Research GmbH - UFZ'),
        (505, 'Dalhousie University', 2279, 'Dalhousie University, Department of Oceanography'),
        (506, 'Naval Research Lab', 3578, 'Naval Research Laboratory'),
        (507, 'First Institute of Oceanology', 1482, 'Institute of Oceanology, Chinese Academy of Sciences'),
        (511, 'Zhejiang Ocean University', 5199, 'Zhejiang University, Ocean College'),
        (514, 'Klaipeda university', 5014, 'Marine Research Institute of Klaipeda University'),
        (515, 'Brown University', 3796, 'Brown University'),
        (516, 'Maryland University - Center for Environmental Science - UMCES', 3226, 'University of Maryland Center for Environmental Science, Horn Point Laboratory'),
        (517, 'Akvaplan Niva AS', 1410, 'Akvaplan-NIVA AS'),
        (520, 'Cumbria Wildlife Trust', 666, 'Cumbria Wildlife Trust'),
        (521, 'University of Cádiz', 1394, 'University of Cadiz. Faculty of Marine and Environmental Science'),
        (522, 'University of Rennes 1', 1910, NULL),
        (523, 'CSIC - Institut de Ciències del Mar', 1672, 'CSIC, Central Organisation'),
        (524, 'SYSU University', 5545, 'Sun Yat Sen University'),
        (526, 'University of Victoria', 2262, 'University of Victoria, School of Earth and Ocean Sciences'),
        (527, 'Moss Landing Marine Laboratories - MLML', 3107, 'Moss Landing Marine Laboratories'),
        (530, 'Takuvik at Laval University - ULaval', 5318, 'Takuvik Joint Laboratory'),
        (532, 'University of the Sunshine Coast', 4323, 'University of the Sunshine Coast'),
        (534, 'University of Pretoria', 3170, 'University of Pretoria Department of Zoology and Entomology'),
        (535, 'Ludwig Maximilian University of Munich - LMU', 2308, 'Ludwig-Maximilians-University of Munich'),
        (537, 'University of Tasmania', 4324, 'University of Tasmania'),
        (539, 'University of Maryland Center for Environmental Science - Horn Point Laboratory', 3226, 'University of Maryland Center for Environmental Science, Horn Point Laboratory'),
        (540, 'Okinawa Institute of Science and Technology - OIST', 3734, 'Okinawa Institute of Science and Technology'),
        (541, 'Old Dominion University', 3806, 'Old Dominion University'),
        (544, 'National Institute of Water and Atmospheric Research - NIWA', 3191, 'National Institute of Water and Atmospheric Research'),
        (546, 'Natural History Museum, University of Oslo', 778, 'University of Oslo'),
        (549, 'Sorbonne Université', 4962, 'Sorbonne University'),
        (555, 'California University of Santa Cruz - UCSC', 3821, 'University of California, Santa Cruz'),
        (558, 'Oregon State University - OSU', 3807, 'Oregon State University'),
        (559, 'University of the Western Cape', 1750, 'University of Western Cape'),
        (561, 'université cheikh anta diop dakar', 6163, NULL),
        (562, 'Université de Bretagne Occidentale', 1893, NULL),
        (564, 'Curtin University', 4027, 'Curtin University'),
        (565, 'University of Aberdeen', 2949, 'University of Aberdeen, Institute of Biological and Environmental Sciences'),
        (567, 'CSIC', 1672, 'CSIC, Central Organisation'),
        (570, 'Fisheries and Oceans Canada / Memorial University', 5370, 'Fisheries and Oceans Canada'),
        (571, 'Bangor University', 1468, 'Bangor University School of Ocean Sciences'),
        (574, 'French Agency for Biodiversity - AFB', 4845, 'French Agency for Biodiversity (Brest)'),
        (575, 'California University of Los Angeles - UCLA', 3646, 'University of California, Los Angeles'),
        (576, 'University of British Columbia', 2220, 'University of British Columbia, Department of Earth, Ocean and Atmospheric Sciences'),
        (582, 'Ban-lab of USP', 1782, 'University of Sao Paulo'),
        (585, 'Institute of Oceanology Polish Academy of Sciences - IO PAN', 195, 'Institute of Oceanology, Polish Academy of Sciences'),
        (587, 'Finnish Environment Institute - SYKE', 1104, 'Finnish Environment Institute'),
        (588, 'Weizmann Institute of Sciences', 5766, 'Weismann Institute of Science'),
        (589, 'University of Dalhousie', 2279, 'Dalhousie University, Department of Oceanography'),
        (590, 'Oregon State University', 3807, 'Oregon State University'),
        (591, 'University of Helsinki', 1098, 'Department of Biological and Environmental Sciences, Aquatic Sciences, University of Helsinki'),
        (593, 'University of Madeira', 3028, 'University of Madeira, Marine Biological Station of Funchal'),
        (600, 'Texas A&M Corpus Christi', 3814, 'Texas A&M University'),
        (601, 'Université de La Rochelle', 3134, 'University of La Rochelle'),
        (603, 'GEOMAR', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (604, 'Virginia Institute of Marine Science - VIMS', 3157, 'Virginia Institute of Marine Science'),
        (606, 'University of Oldenburg', 1769, 'University of Oldenburg'),
        (608, 'CREOCEAN', 1047, 'CREOCEAN'),
        (611, 'Tokai University', 3295, 'Tokai University School of Marine Science and Technology'),
        (613, 'Faroese Marine Research Institute', 3084, 'Faroe Marine Research Institute'),
        (615, 'Aarhus University', 5580, 'Aarhus University'),
        (617, 'U.S. Geological Survey', 1566, 'U.S. Geological Survey'),
        (618, 'Savannah State University', 3811, 'Savannah State University'),
        (619, 'Ifremer Sete', 721, 'Ifremer, Station de Sete'),
        (621, 'MBARI', 3115, NULL),
        (622, 'University College London', 2109, NULL),
        (625, 'Korea Polar Research Institute', 3735, 'Korea Polar Research Institute'),
        (628, 'Essex wildlife trust', 5347, 'Essex Wildlife Trust'),
        (630, 'National Research and Innovation Agency (BRIN)', 6148, NULL),
        (632, 'Marine Institute Ireland', 396, 'Marine Institute'),
        (638, 'California University of Santa Barbara - UCSB', 3820, 'University of California, Santa Barbara'),
        (639, 'Takuvik / University Laval', 5318, 'Takuvik Joint Laboratory'),
        (642, 'Institute of oceanography and limnology of Israel', 963, 'Israel Oceanographic and Limnological Research'),
        (643, 'Queen Mary University of London', 2950, 'Queen Mary University of London School of Biological and Chemical Sciences'),
        (644, 'Ifremer Nantes', 1913, 'Ifremer Centre de Nantes'),
        (646, 'agrocampus-ouest', 1911, 'Ecole Supérieure d''Agronomie, Agrocampus Ouest'),
        (647, 'lund university', 5373, 'Lund University, Department of Biology'),
        (648, 'The Marine Biological Association', 45, 'Marine Biological Association of the United Kingdom'),
        (649, 'Universitad de las Islas Baleares', 334, 'Baleares Islands University. Environmental Biology Department.'),
        (650, 'La Rochelle University', 3134, 'University of La Rochelle'),
        (652, 'Institute of Marine Research', 566, 'Institute of Marine Research'),
        (653, 'Alaska Fairbanks University - UAF', 5828, 'University of Alaska Fairbanks, Institute of Marine Science'),
        (654, 'CUNY Queens College', 3607, 'Queens College'),
        (655, 'UC Santa Barbara', 3820, 'University of California, Santa Barbara'),
        (656, 'GEOMAR Kiel', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (658, 'Spanish Institute of Oceanography - IEO', 353, NULL),
        (660, 'Ben Gurion University', 4492, 'Ben-Gurion University of the Negev, Faculty of Natural Sciences, Geological And Environmental Sciences'),
        (661, 'VLIZ', 422, 'Flanders Marine Institute'),
        (662, 'Texas A&M University - TAMU', 3814, 'Texas A&M University'),
        (663, 'University of Salzburg', 3022, 'University of Salzburg'),
        (666, 'University of Haifa', 4897, 'University of Haifa'),
        (669, 'University of Delaware', 3825, 'University of Delaware'),
        (670, 'university of California Santa Barbara', 3820, 'University of California, Santa Barbara'),
        (674, 'Alfred Wegener Institute - AWI', 1368, 'Alfred Wegener Institute Helmholtz Centre for Polar and Marine Research'),
        (677, 'Swansea University', 4054, 'Swansea University, College of Science'),
        (678, 'Stazione Zoologica Anton Dohrn', 237, 'Stazione Zoologica Anton Dohrn of Naples'),
        (679, 'Marine and Environmental Science Centre', 4880, 'Marine and Environmental Sciences Centre, Faculty of Sciences of the University of Lisbon'),
        (680, 'Scripps Institution of Oceanography', 1390, 'Scripps Institution of Oceanography'),
        (682, 'Swedish University of Agricultural Sciences', 189, 'Swedish University of Agricultural Sciences'),
        (688, 'University of Hawaii', 3826, 'University of Hawaii'),
        (691, 'TEL AVIV UNIVERSITY', 5750, 'Tel Aviv University, Faculty of Engineering'),
        (692, 'Cyprus Subsea', 5516, 'Cyprus Subsea Consulting and Services'),
        (694, 'Universidade federal de Pernambuco', 5842, 'Universidade Federal de Pernambuco'),
        (695, 'Atlantic Technical University', 773, 'Atlantic Technological University'),
        (697, 'Max Planck Institute for Chemistry', 2318, 'Max Planck Institute for Chemistry (Mainz)'),
        (701, 'Quebec University of Rimouski - UQAR', 3361, 'University of Quebec at Rimouski, Institut des Sciences de la Mer'),
        (703, 'The Hebrew University of Jerusalem; The interuniversity Institute for Marine Sciences in Eilat', 5764, 'The Hebrew University of Jerusalem'),
        (704, 'Bayworld Centre for Research & Education', 3499, 'Bayworld Centre for Research & Education'),
        (705, 'CNRS - Mediterranean Institute of Oceanology MIO', 3078, 'Mediterranean Institute of Oceanography (Marseille)'),
        (706, 'National Institute of Marine Sciences and Technics - Intechmer', 1916, NULL),
        (707, 'Stockholm University', 623, 'Stockholm University, Department of Ecology, Environment and Plant Sciences'),
        (708, 'Northeastern University', 3592, 'Northeastern University'),
        (710, 'Hellenic Center for Marine Research', 3051, 'Hellenic Centre for Marine Research (HCMR)'),
        (714, 'UniversidadeFederaldeSãoPaulo', 1782, 'University of Sao Paulo'),
        (716, 'New York University', 3158, 'Center for Atmosphere Ocean Science, New York University'),
        (718, 'University of Rhode Island', 3833, 'University of Rhode Island'),
        (720, 'EPFL', 4830, 'Swiss Federal Institute of Technology in Lausanne'),
        (722, 'Vlaams Instituut voor de Zee (VLIZ)', 422, 'Flanders Marine Institute'),
        (723, 'Tokyo University of Marine Science and Technology', 5788, 'Tokyo University of Marine Science and Technology'),
        (724, 'ULCO', 2910, NULL),
        (725, 'IPMA - Portuguese Institute for the Ocean and Atmosphere', 3288, 'Portuguese Institute for Sea and Atmosphere'),
        (727, 'UiT the Arctic University of Norway', 5354, 'Arctic University of Norway'),
        (728, 'University of Sevilla', 2165, 'Sevilla University'),
        (729, 'Universidad de Murcia', 350, NULL),
        (731, 'Huntsman Marine Science Centre', 4764, 'Huntsman Marine Science Centre, Atlantic Reference Centre'),
        (732, 'Atlantic Technological University', 773, 'Atlantic Technological University'),
        (733, 'Bar-Ilan University', 5765, 'Bar-Ilan University'),
        (734, 'University of California Berkeley', 3818, 'University of California, Berkeley'),
        (735, 'University of Colorado Boulder', 3823, 'University of Colorado at Boulder'),
        (737, 'Xiamen University - XMU', 2401, 'Xiamen University, State Key Laboratory of Marine Environmental Science'),
        (738, 'National Institute of Fisheries Research - INIP', 582, 'National Institute of Fisheries Research Instituto Nacional de Investigação Agrária e das Pescas Former IPIMAR'),
        (740, 'USGS', 1566, 'U.S. Geological Survey'),
        (741, 'Uni Konstanz', 3198, 'University of Konstanz Limnological Institute'),
        (742, 'University of Sao Paulo', 1782, 'University of Sao Paulo'),
        (744, 'Arizona State University', 3517, 'Arizona State University'),
        (745, 'Institute of Marine Sciences, Okeanos', 5450, 'University of Azores, Institute of Marine Sciences'),
        (747, 'University of Oslo', 778, 'University of Oslo'),
        (750, 'University of Bergen', 544, 'University of Bergen'),
        (751, 'Université du Québec à Montréal', 3720, 'Université du Québec à Montréal'),
        (752, 'Fisheries and Oceans Canada', 5370, 'Fisheries and Oceans Canada'),
        (755, 'The John Hopkins University', 5295, 'John Hopkins University'),
        (757, 'Ecole Normale Supérieure - ENS', 4763, 'Ecole Normale Superieure'),
        (758, 'University of Georgia', 3815, 'The University of Georgia'),
        (760, 'university of bristol', 1475, NULL),
        (761, 'Columbia University', 3533, 'Columbia University'),
        (763, 'Federal University of Pernambuco (UFPE)', 5842, 'Universidade Federal de Pernambuco'),
        (766, 'Second Institute of Oceanography, MNR', 3335, 'Second Institute of Oceanography, Ministry of Natural Resources'),
        (767, 'Florida Fish and Wildlife Commission - Fish and Wildlife Research Institute', 3544, 'Florida Fish & Wildlife Conservation Commission'),
        (774, 'University of North Carolina at Chapel Hill', 1563, 'University of North Carolina at Chapel Hill, Department of Marine Sciences'),
        (776, 'SOCIB', 3410, NULL),
        (777, 'SUN YAT-SEN UNIVERSITY', 5545, 'Sun Yat Sen University'),
        (779, 'National Institute of Oceanography and Geophysics - OGS', 120, 'National Institute of Oceanography and Applied Geophysics - OGS, Division of Oceanography'),
        (780, 'MARUM, Bremen University', 1568, 'Center for Marine Environmental Sciences, University of Bremen'),
        (783, 'Institut de la Mer de Villefranche', 5041, NULL),
        (785, 'Kent Wildlife Trust', 3203, 'Kent Wildlife Trust'),
        (786, 'Institute of Hydrobiology, Biology Centre, Czech Academy of Sciences', 2952, 'Czech Academy of Sciences, Institute of Microbiology, Department of Autotrophic Microorganisms'),
        (787, 'University of Southern Denmark', 744, 'University of Southern Denmark, Institute of Biology'),
        (792, 'Sherbrooke University', 4441, 'Sherbrooke University'),
        (795, 'Universidade Estadual do Norte Fluminense', 4870, 'Universidade Estadual do Norte Fluminense Darcy Ribeiro'),
        (797, 'Florida State University - FSU', 2716, 'Florida State University, Department of Oceanography'),
        (798, 'University of Exeter', 4941, 'University of Exeter'),
        (799, 'Newcastle University', 2491, 'Newcastle University School of Marine Science and Technology'),
        (802, 'The Wildlife Trusts', 5491, 'The Wildlife Trusts'),
        (803, 'East Carolina University - ECU', 3537, 'East Carolina University'),
        (807, 'UC Los Angeles', 3646, 'University of California, Los Angeles'),
        (810, 'Academia Sinica, Taiwan', 3744, 'Academia Sinica'),
        (811, 'Thünen Institut', 1570, 'Thünen-Institute of Sea Fisheries'),
        (812, 'James Cook University', 4270, 'James Cook University'),
        (813, 'University of California, Santa Cruz', 3821, 'University of California, Santa Cruz'),
        (815, 'California Polytechnic State University San Luis Obispo', 5419, 'California Polytechnic State University'),
        (816, 'University of Galway', 774, 'University of Galway'),
        (817, 'university of Zurich', 4370, 'University of Zurich'),
        (819, 'IFREMER Port-en-bessin', 509, 'Ifremer, Station Port en Bessin'),
        (822, 'federal university of santa catarina', 5213, 'Federal University of Santa Catarina'),
        (823, 'Israel Oceanographic and Limnological Research', 963, 'Israel Oceanographic and Limnological Research'),
        (824, 'University of Rochester', 3663, 'University of Rochester'),
        (826, 'Université de Toulon', 4625, 'Mediterranean Institute Of Oceanography (Toulon)'),
        (829, 'CNR-IIA', 4647, NULL),
        (830, 'Virginia Institute of Marine Science CCRM', 3157, 'Virginia Institute of Marine Science'),
        (832, 'Nord University', 5998, 'Nord University, Bodø'),
        (833, 'Haifa univercity', 4897, 'University of Haifa'),
        (835, 'CNRS Sorbonne Université', 4962, 'Sorbonne University'),
        (836, 'Louisiana State University - LSU', 3114, 'Louisiana State University, Department of Oceanography and Coastal Sciences'),
        (837, 'University of Gothenburg', 3984, 'University of Gothenburg'),
        (839, 'Observatório Oceânico da Madeira', 5226, 'Oceanic Observatory of Madeira'),
        (841, 'Université Laval', 2076, 'Université Laval'),
        (844, 'Karlsruhe Institute of Technology (KIT)', 2528, 'Karlsruhe Institute of Technology (South Campus)'),
        (848, 'Johannes Gutenberg University Mainz', 1155, 'Johannes Gutenberg University Mainz'),
        (853, 'Universidad Las Palmas de Gran Canaria', 1398, 'University of Las Palmas de Gran Canaria. Faculty of Marine Science.'),
        (857, 'National Oceanography Centre', 17, 'National Oceanography Centre (Southampton)'),
        (859, 'GEOMAR Helmholtz-Zentrum für Ozeanforschung Kiel', 2947, 'Helmholtz Centre for Ocean Research Kiel'),
        (860, 'Ruder Boskovic Institute, Center for Marine Research', 702, 'Center for marine research, Rudjer Boskovic Institute'),
        (864, 'CNR - institute of Biophysics', 1650, 'CNR, Biophysics Institute'),
        (866, 'University of Alaska Fairbanks', 3643, 'University of Alaska Fairbanks'),
        (869, 'Nelson Mandela University - NMMU', 5149, 'Nelson Mandela University, Institute for Coastal and Marine Research'),
        (870, 'UK Centre for Ecology & Hydrology', 2574, 'Centre for Ecology & Hydrology (Edinburgh)'),
        (873, 'The Ohio State University', 3602, 'Ohio State University'),
        (877, 'Kenya Fisheries Service', 2594, 'Kenya Marine and Fisheries Research Institute'),
        (NULL, 'National Institute for Marine Research and Development "Grigore Antipa"', 697, 'National Institute for Marine Research and Development "Grigore Antipa"'),
        (NULL, 'UNIVERSITY OF SOUTH FLORIDA', 3838, 'University of South Florida'),
        (NULL, 'university of south florida', 3838, 'University of South Florida'),
        (NULL, 'university of washington', 3839, 'University of Washington');

-- Resolve to organizations: by id when present (authoritative, the name may have been edited
-- since the extraction), else all organizations with the same name.
CREATE TEMP TABLE edmo_org_all ON COMMIT DROP AS
SELECT org.id AS org_id, mat.edmo_id, mat.edmo_name, mat.eco_name
  FROM edmo_match mat
  JOIN organizations org
    ON org.id = mat.eco_id
    OR (mat.eco_id IS NULL AND pg_temp.edmo_norm(org.name) = pg_temp.edmo_norm(mat.eco_name));

-- One EDMO id per organization, organizations with contradicting rows are left untouched.
CREATE TEMP TABLE edmo_org ON COMMIT DROP AS
SELECT DISTINCT ON (org_id) org_id, edmo_id, edmo_name, eco_name
  FROM edmo_org_all
 WHERE org_id NOT IN (SELECT org_id FROM edmo_org_all GROUP BY org_id HAVING count(DISTINCT edmo_id) > 1)
 ORDER BY org_id, edmo_name IS NULL;

-- Organizations absent from the spreadsheet but already named like an EDMO name: same institution.
INSERT INTO edmo_org (org_id, edmo_id, edmo_name, eco_name)
SELECT DISTINCT ON (org.id) org.id, grp.edmo_id, grp.edmo_name, org.name
  FROM (SELECT DISTINCT edmo_id, edmo_name FROM edmo_org WHERE edmo_name IS NOT NULL) grp
  JOIN organizations org ON pg_temp.edmo_norm(org.name) = pg_temp.edmo_norm(grp.edmo_name)
 WHERE org.id NOT IN (SELECT org_id FROM edmo_org_all)
 ORDER BY org.id, grp.edmo_id;

-- One group per EDMO id. Survivor: already named as in EDMO, else most referenced, else lowest id.
CREATE TEMP TABLE edmo_group ON COMMIT DROP AS
SELECT DISTINCT ON (eor.edmo_id) eor.edmo_id,
                                 grn.edmo_name,
                                 eor.org_id                          AS survivor_id,
                                 coalesce(grn.edmo_name, org.name)   AS final_name,
                                 CAST(NULL AS VARCHAR)               AS skip_reason
  FROM edmo_org eor
  JOIN (SELECT edmo_id, min(edmo_name) AS edmo_name FROM edmo_org GROUP BY edmo_id) grn
       ON grn.edmo_id = eor.edmo_id
  JOIN organizations org ON org.id = eor.org_id
 ORDER BY eor.edmo_id,
          (pg_temp.edmo_norm(org.name) = pg_temp.edmo_norm(grn.edmo_name)) IS NOT TRUE,
          (SELECT count(*) FROM users usr WHERE usr.organization_id = org.id)
              + (SELECT count(*) FROM collection_orga_role cor WHERE cor.organization_id = org.id) DESC,
          org.id;

-- Final names must stay unique, case-insensitively as organizations are looked up with ILIKE.
-- Skipping a group keeps its organizations' names, which may conflict in turn: iterate.
DO
$$
    BEGIN
        LOOP
            UPDATE edmo_group grp
               SET skip_reason = 'final name conflict'
             WHERE grp.skip_reason IS NULL
               AND (EXISTS (SELECT 1
                              FROM edmo_group oth
                             WHERE oth.skip_reason IS NULL
                               AND oth.edmo_id <> grp.edmo_id
                               AND pg_temp.edmo_norm(oth.final_name) = pg_temp.edmo_norm(grp.final_name))
                 OR EXISTS (SELECT 1
                              FROM organizations org
                             WHERE pg_temp.edmo_norm(org.name) = pg_temp.edmo_norm(grp.final_name)
                               AND org.id NOT IN (SELECT eor.org_id
                                                    FROM edmo_org eor
                                                    JOIN edmo_group vld ON vld.edmo_id = eor.edmo_id
                                                   WHERE vld.skip_reason IS NULL)));
            EXIT WHEN NOT FOUND;
        END LOOP;
    END
$$;

CREATE TEMP TABLE edmo_merge ON COMMIT DROP AS
SELECT eor.org_id AS old_id, grp.survivor_id AS new_id
  FROM edmo_org eor
  JOIN edmo_group grp ON grp.edmo_id = eor.edmo_id
 WHERE grp.skip_reason IS NULL
   AND eor.org_id <> grp.survivor_id;

CREATE TABLE organizations_edmo_log AS
SELECT eor.org_id,
       org.name                                                    AS old_name,
       CASE WHEN grp.skip_reason IS NOT NULL THEN 'skip'
            WHEN eor.org_id = grp.survivor_id THEN 'update'
            ELSE 'merge' END                                        AS action,
       CASE WHEN grp.skip_reason IS NULL AND eor.org_id = grp.survivor_id
                THEN grp.final_name END                             AS new_name,
       eor.edmo_id,
       grp.edmo_name,
       CASE WHEN grp.skip_reason IS NULL AND eor.org_id <> grp.survivor_id
                THEN grp.survivor_id END                            AS merged_into,
       concat_ws('; ',
                 grp.skip_reason,
                 CASE WHEN grp.edmo_name IS NULL THEN 'EDMO name unknown' END,
                 CASE WHEN pg_temp.edmo_norm(org.name) <> pg_temp.edmo_norm(eor.eco_name)
                          THEN 'spreadsheet name: ' || eor.eco_name END) AS remark
  FROM edmo_org eor
  JOIN edmo_group grp ON grp.edmo_id = eor.edmo_id
  JOIN organizations org ON org.id = eor.org_id
UNION ALL
SELECT NULL, mat.eco_name, 'not found', NULL, mat.edmo_id, mat.edmo_name, NULL,
       CASE WHEN mat.eco_id IS NULL THEN 'no organization with this name'
            ELSE 'no organization with id ' || mat.eco_id END
  FROM edmo_match mat
 WHERE NOT EXISTS (SELECT 1 FROM edmo_org_all eoa WHERE eoa.eco_name = mat.eco_name AND eoa.edmo_id = mat.edmo_id)
UNION ALL
SELECT eoa.org_id, org.name, 'skip', NULL, eoa.edmo_id, eoa.edmo_name, NULL, 'contradicting EDMO ids'
  FROM edmo_org_all eoa
  JOIN organizations org ON org.id = eoa.org_id
 WHERE eoa.org_id NOT IN (SELECT org_id FROM edmo_org);

-- Users and guests of merged organizations go to the survivor
UPDATE users usr
   SET organization_id = mrg.new_id
  FROM edmo_merge mrg
 WHERE usr.organization_id = mrg.old_id;

-- Same for collections. Several merged organizations in the same collection & role collapse into one link.
INSERT INTO collection_orga_role (collection_id, organization_id, role, display_order)
SELECT cor.collection_id, mrg.new_id, cor.role, min(cor.display_order)
  FROM collection_orga_role cor
  JOIN edmo_merge mrg ON mrg.old_id = cor.organization_id
 GROUP BY cor.collection_id, mrg.new_id, cor.role
    ON CONFLICT DO NOTHING;

DELETE FROM collection_orga_role WHERE organization_id IN (SELECT old_id FROM edmo_merge);

DELETE FROM organizations WHERE id IN (SELECT old_id FROM edmo_merge);

-- Rename in 2 passes, as name swaps would transiently violate UNIQUE (name)
UPDATE organizations org
   SET name = '__edmo_tmp_' || org.id
  FROM edmo_group grp
 WHERE grp.skip_reason IS NULL
   AND org.id = grp.survivor_id
   AND org.name <> grp.final_name;

UPDATE organizations org
   SET name = grp.final_name
  FROM edmo_group grp
 WHERE grp.skip_reason IS NULL
   AND org.id = grp.survivor_id
   AND org.name = '__edmo_tmp_' || org.id;

-- EDMO reference, replacing any previous one and keeping other directories
UPDATE organizations org
   SET directories = concat_ws(',',
                               nullif(array_to_string(ARRAY(SELECT btrim(dir)
                                                              FROM unnest(string_to_array(org.directories, ',')) dir
                                                             WHERE btrim(dir) <> ''
                                                               AND left(btrim(dir), 5) <> 'edmo:'), ','), ''),
                               'edmo:' || grp.edmo_id)
  FROM edmo_group grp
 WHERE grp.skip_reason IS NULL
   AND org.id = grp.survivor_id;

UPDATE alembic_version SET version_num='890a5b01ab64' WHERE alembic_version.version_num = 'c593af18f13a';

COMMIT;

BEGIN;

-- Running upgrade 890a5b01ab64 -> af45d71653e4

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

UPDATE alembic_version SET version_num='af45d71653e4' WHERE alembic_version.version_num = '890a5b01ab64';

COMMIT;

------- Leave on tail

ALTER TABLE alembic_version REPLICA IDENTITY FULL;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole;

ALTER SUBSCRIPTION mysub13 REFRESH PUBLICATION;