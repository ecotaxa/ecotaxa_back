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

COPY public.worms (aphia_id, url, scientificname, authority, status, unacceptreason, taxon_rank_id, rank, valid_aphia_id, valid_name, valid_authority, parent_name_usage_id, kingdom, phylum, class_, "order", family, genus, citation, lsid, is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct, match_type, modified, all_fetched) FROM stdin;
1101	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1101	Cyclopoida	Burmeister, 1834	accepted	\N	100	Order	1101	Cyclopoida	Burmeister, 1834	155879	Animalia	Arthropoda	Hexanauplia	Cyclopoida	\N	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Cyclopoida. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1101 on 2020-09-20	urn:lsid:marinespecies.org:taxname:1101	t	t	t	\N	\N	exact	2016-03-21 09:41:01.793	t
128586	http://www.marinespecies.org/aphia.php?p=taxdetails&id=128586	Oncaeidae	Giesbrecht, 1893	accepted	\N	140	Family	128586	Oncaeidae	Giesbrecht, 1893	1381349	Animalia	Arthropoda	Hexanauplia	Cyclopoida	Oncaeidae	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Oncaeidae Giesbrecht, 1893. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=128586 on 2020-09-20	urn:lsid:marinespecies.org:taxname:128586	t	\N	\N	\N	f	exact	2019-10-07 11:15:09.153	t
\.

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
-- ecotaxa_master$ python manage.py db upgrade --sql 36bb704b9fc5:4bb7276e86de >> ../ecotaxa_back/QA/py/pg_files/upgrade_prod.sql
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

