
DROP TABLE images_new;
--
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--
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
                    COMMIT;
                END IF ;
            END LOOP;
    END;
$$;

--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY images_new
    ADD CONSTRAINT images_pkey_new PRIMARY KEY (objid, imgrank);

ANALYSE images_new;

--
-- Name: TABLE images; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE images_new TO readerole;
GRANT SELECT ON TABLE images_new TO zoo;
GRANT SELECT ON TABLE images_new TO repuser;

ALTER TABLE images RENAME TO images_old;

ALTER TABLE images_new RENAME TO images;

DROP TABLE image_file;

CREATE TABLE image_file (
    imgid BIGINT NOT NULL,
    state CHAR DEFAULT '?' NOT NULL,
    ext CHAR(3) DEFAULT '?' NOT NULL,
    digest_type CHAR DEFAULT '?' NOT NULL,
    digest BYTEA,
    PRIMARY KEY (imgid)
);



