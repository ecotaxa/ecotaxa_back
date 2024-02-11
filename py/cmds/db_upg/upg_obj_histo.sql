--
-- Based on a pg_dump -t objectsclassifhisto from production DB on the 9th of Feb 2024
--

drop table public.objectsclassifhisto2;

create table public.objectsclassifhisto2
(
    objid         bigint                      not null,
    classif_date  timestamp without time zone not null,
    classif_id    integer                     not null,
    classif_type  character(1),
    classif_qual  character(1),
    classif_score double precision,
    classif_who   integer
);

ALTER TABLE ONLY public.objectsclassifhisto2 ALTER COLUMN classif_date SET STATISTICS 10000;


ALTER TABLE public.objectsclassifhisto2 OWNER TO postgres;

--
-- Name: TABLE objectsclassifhisto; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.objectsclassifhisto2 TO readerole;
GRANT SELECT ON TABLE public.objectsclassifhisto2 TO zoo;
GRANT SELECT ON TABLE public.objectsclassifhisto2 TO repuser;

DO
$$
    DECLARE
        cp_objid  integer = 0;
        next_cp_objid integer = 1;
        chunk     integer = 1000000;
    BEGIN
        WHILE next_cp_objid IS NOT NULL
            LOOP
                with done as (insert into objectsclassifhisto2 (objid,
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

ALTER TABLE ONLY public.objectsclassifhisto2
    ADD CONSTRAINT objectsclassifhisto_pkey PRIMARY KEY (objid, classif_date);


ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_classif_who_fkey TO objectsclassifhisto_classif_who_fkey_old;

--
-- Name: objectsclassifhisto objectsclassifhisto_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto2
    ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);

--
-- Name: objectsclassifhisto objectsclassifhisto_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.objectsclassifhisto
    RENAME CONSTRAINT objectsclassifhisto_objid_fkey TO objectsclassifhisto_objid_fkey_old;

ALTER TABLE ONLY public.objectsclassifhisto2
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head(objid) ON DELETE CASCADE;

ALTER TABLE public.objectsclassifhisto RENAME TO objectsclassifhisto_old;

ALTER TABLE public.objectsclassifhisto2 RENAME TO objectsclassifhisto;
