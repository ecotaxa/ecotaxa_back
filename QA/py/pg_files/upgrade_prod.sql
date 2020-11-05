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