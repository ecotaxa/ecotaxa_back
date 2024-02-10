--
-- Based on a pg_dump -t obj_head from production DB on the 9th of Feb 2024
--
drop table public.obj_head2;

create table public.obj_head2
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
ALTER TABLE ONLY public.obj_head2 ALTER COLUMN acquisid SET STATISTICS 10000;

alter table public.obj_head2
    owner to postgres;

--
-- Name: obj_head obj_head_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head2
    ADD CONSTRAINT obj_head_pkey2 PRIMARY KEY (objid);

--
-- Name: TABLE obj_head; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.obj_head2 TO readerole;
GRANT SELECT ON TABLE public.obj_head2 TO zoo;
GRANT SELECT ON TABLE public.obj_head2 TO repuser;

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
                insert into obj_head2 (objid, acquisid, classif_id,
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

ANALYSE obj_head2;

--
-- Name: is_objectsacqclassifqual; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsacqclassifqual RENAME TO is_objectsacqclassifqual_old;
-- CREATE INDEX is_objectsacqclassifqual ON public.obj_head2 USING btree (acquisid, classif_id, classif_qual);

--
-- Name: is_objectsacqrandom; Type: INDEX; Schema: public; Owner: postgres
--

ALTER INDEX is_objectsacqrandom RENAME TO is_objectsacqrandom_old;
-- CREATE INDEX is_objectsacqrandom ON public.obj_head2 USING btree (acquisid, hashtext(orig_id), classif_qual);

--
-- Name: is_objectsacquisition; Type: INDEX; Schema: public; Owner: postgres
--

ALTER INDEX is_objectsacquisition RENAME TO is_objectsacquisition_old;
CREATE INDEX is_objectsacquisition ON public.obj_head2 USING btree (acquisid);

ALTER TABLE public.obj_head2 CLUSTER ON is_objectsacquisition;

--
-- Name: is_objectsdate; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsdate RENAME TO is_objectsdate_old;
CREATE INDEX is_objectsdate ON public.obj_head2 USING btree (objdate, acquisid);


--
-- Name: is_objectsdepth; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectsdepth RENAME TO is_objectsdepth_old;
CREATE INDEX is_objectsdepth ON public.obj_head2 USING btree (depth_max, depth_min, acquisid);


--
-- Name: is_objectslatlong; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX is_objectslatlong RENAME TO is_objectslatlong_old;
CREATE INDEX is_objectslatlong ON public.obj_head2 USING btree (latitude, longitude, acquisid);


--
-- Name: is_objectstime; Type: INDEX; Schema: public; Owner: postgres
--
ALTER INDEX  is_objectstime RENAME TO is_objectstime_old;
CREATE INDEX is_objectstime ON public.obj_head2 USING btree (objtime, acquisid);

--
-- Name: obj_head obj_head_acquisid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_acquisid_fkey TO obj_head_acquisid_fkey_old;
ALTER TABLE ONLY public.obj_head2
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES public.acquisitions(acquisid) ON DELETE CASCADE;

--
-- Name: obj_head obj_head_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_classif_who_fkey TO obj_head_classif_who_fkey_old;
ALTER TABLE ONLY public.obj_head2
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);

ANALYSE obj_head2;

--
-- Name: objectsclassifhisto objectsclassifhisto_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.objectsclassifhisto
    DROP CONSTRAINT objectsclassifhisto_objid_fkey;
ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head2(objid) ON DELETE CASCADE;


--
-- Name: images images_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.images
    DROP CONSTRAINT images_objid_fkey;
ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head2(objid);

--
-- Name: obj_cnn_features obj_cnn_features_objcnnid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.obj_cnn_features
    DROP CONSTRAINT obj_cnn_features_objcnnid_fkey;
ALTER TABLE ONLY public.obj_cnn_features
    ADD CONSTRAINT obj_cnn_features_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES public.obj_head2(objid) ON DELETE CASCADE;

--
-- Name: obj_field obj_field_objfid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--
ALTER TABLE ONLY public.obj_field
    DROP CONSTRAINT obj_field_objfid_fkey;
ALTER TABLE ONLY public.obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES public.obj_head2(objid) ON DELETE CASCADE;

ALTER TABLE obj_head RENAME TO obj_head_old;

ALTER TABLE ONLY public.obj_head_old
    RENAME CONSTRAINT obj_head_pkey TO obj_head_pkey_old;

ALTER TABLE obj_head2 RENAME TO obj_head;

ALTER TABLE ONLY public.obj_head
    RENAME CONSTRAINT obj_head_pkey2 TO obj_head_pkey;
