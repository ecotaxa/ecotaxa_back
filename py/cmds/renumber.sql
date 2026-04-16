\set SAM_MULT 1000000::bigint
\set ACQ_MULT 10000000::bigint
\set OBJ_MULT 100000000::bigint
\set OTHER_TBLSPC home_tables

-- 1. Drop the view that depends on the affected tables
DROP VIEW IF EXISTS objects;

-- Bump the first projects which collide
CREATE TEMP TABLE projid_old_2_new AS
SELECT * FROM (VALUES
    (1, 12),
    (3, 16),
    (4, 17),
    (6, 19),
    (8, 20),
    (10, 21)
) AS t(old_id, new_id);

BEGIN;

SET LOCAL session_replication_role = 'replica';

-- 2. Update the main 'projects' table
UPDATE projects
SET projid = m.new_id
FROM projid_old_2_new m
WHERE projects.projid = m.old_id;

-- 3. Update all referencing tables
-- samples.projid
UPDATE samples
SET projid = m.new_id
FROM projid_old_2_new m
WHERE samples.projid = m.old_id;

-- projects_taxo_stat.projid
UPDATE projects_taxo_stat
SET projid = m.new_id
FROM projid_old_2_new m
WHERE projects_taxo_stat.projid = m.old_id;

-- projectspriv.projid
UPDATE projectspriv
SET projid = m.new_id
FROM projid_old_2_new m
WHERE projectspriv.projid = m.old_id;

-- projects_variables.project_id
UPDATE projects_variables
SET project_id = m.new_id
FROM projid_old_2_new m
WHERE projects_variables.project_id = m.old_id;

-- collection_project.project_id
UPDATE collection_project
SET project_id = m.new_id
FROM projid_old_2_new m
WHERE collection_project.project_id = m.old_id;

-- taxo_recast.project_id
UPDATE taxo_recast
SET project_id = m.new_id
FROM projid_old_2_new m
WHERE taxo_recast.project_id = m.old_id;

-- training.projid
UPDATE training
SET projid = m.new_id
FROM projid_old_2_new m
WHERE training.projid = m.old_id;

-- user_preferences.project_id
UPDATE user_preferences
SET project_id = m.new_id
FROM projid_old_2_new m
WHERE user_preferences.project_id = m.old_id;

-- taxo_change_log.project_id
UPDATE taxo_change_log
SET project_id = m.new_id
FROM projid_old_2_new m
WHERE taxo_change_log.project_id = m.old_id;

COMMIT;

-- 2. Drop the foreign key constraint from acquisitions to samples
ALTER TABLE acquisitions
    DROP CONSTRAINT acquisitions_sampleid_fkey;

-- 3. Change the type of sampleid in samples and its referencing column in acquisitions
ALTER TABLE samples
    ALTER COLUMN sampleid TYPE bigint;
ALTER TABLE acquisitions
    ALTER COLUMN acq_sample_id TYPE bigint;

-- 4. Re-create the foreign key constraint
ALTER TABLE acquisitions
    ADD CONSTRAINT acquisitions_sampleid_fkey
        FOREIGN KEY (acq_sample_id) REFERENCES samples (sampleid);

-- 1. Create a mapping table to hold old and new IDs
CREATE UNLOGGED TABLE samid_old_2_new AS
SELECT sampleid                                                                           AS old_id,
       (projid * :SAM_MULT) + ROW_NUMBER() OVER (PARTITION BY projid ORDER BY sampleid) AS new_id
FROM samples;

ALTER TABLE acquisitions
    DROP CONSTRAINT acquisitions_sampleid_fkey;

UPDATE samples
SET sampleid = mapping.new_id
FROM samid_old_2_new mapping
WHERE samples.sampleid = mapping.old_id;

-- 2. Update the referencing table(s).
-- In EcoTaxa, 'acquisitions' is the main table referencing 'samples'.
-- We use a temporary disable of constraints if necessary, or just a direct update.
-- Note: 'part_samples' was used in older versions but has been removed in recent ones.
UPDATE acquisitions
SET acq_sample_id = mapping.new_id
FROM samid_old_2_new mapping
WHERE acquisitions.acq_sample_id = mapping.old_id;

-- 4. Re-create the primary key and foreign keys
-- ALTER TABLE samples ADD PRIMARY KEY (sampleid);

ALTER TABLE acquisitions
    ADD CONSTRAINT acquisitions_sampleid_fkey
        FOREIGN KEY (acq_sample_id) REFERENCES samples (sampleid);

vacuum (verbose, full) samples;

vacuum (verbose, full) acquisitions;

-- 6. Cleanup
-- DROP TABLE samid_old_2_new;


-- 1. Create a mapping table to hold old and new IDs
-- Ordered by sample ID and then by the original ID
CREATE UNLOGGED TABLE acqid_old_2_new AS
SELECT acquisid AS old_id,
       (projid * :ACQ_MULT) +
       ROW_NUMBER() OVER (
           PARTITION BY projid
           ORDER BY acquisid
           )    AS new_id
	 FROM acquisitions acq
	 JOIN samples sam ON sam.sampleid = acq.acq_sample_id;

CREATE INDEX acquisid_mapping_idx ON acqid_old_2_new (new_id) INCLUDE (old_id);
CREATE INDEX acquisid_mapping_idx2 ON acqid_old_2_new (old_id) INCLUDE (new_id);

-- 2. Drop constraints to allow updating primary keys and foreign keys
-- This includes foreign keys from 'obj_head' and 'process'
ALTER TABLE obj_head
    DROP CONSTRAINT obj_head_acquisid_fkey;

ALTER TABLE process
    DROP CONSTRAINT process_pkey CASCADE;

ALTER TABLE acquisitions
    DROP CONSTRAINT acquisitions_pkey CASCADE;
-- NOTICE:  DROP cascade sur contrainte process_processid_fkey sur table process
-- ALTER TABLE

ALTER TABLE acquisitions
    ALTER COLUMN acquisid TYPE bigint;

-- 3. Update the 'acquisitions' table
UPDATE acquisitions
SET acquisid = mapping.new_id
FROM acqid_old_2_new mapping
WHERE acquisitions.acquisid = mapping.old_id;

-- 4. Update the 'process' table
-- Note: 'processid' in 'process' table is synchronized with 'acquisid'
ALTER TABLE process
    ALTER COLUMN processid TYPE bigint;

UPDATE process
SET processid = mapping.new_id
FROM acqid_old_2_new mapping
WHERE process.processid = mapping.old_id;

vacuum (verbose, full) acquisitions;

vacuum (verbose, full) process;

-- Make space in the old table namespace
-- Primary Key
ALTER TABLE obj_head
    RENAME CONSTRAINT obj_head_pkey TO obj_head_pkey_old;
-- Indexes:
ALTER INDEX is_obj_head_acquisid_objid RENAME TO is_obj_head_acquisid_objid_old;
ALTER INDEX is_objectsdate RENAME TO is_objectsdate_old;
ALTER INDEX is_objectsdepth RENAME TO is_objectsdepth_old;
ALTER INDEX is_objectslatlong RENAME TO is_objectslatlong_old;
ALTER INDEX is_objectstime RENAME TO is_objectstime_old;
-- Foreign-key constraints:
ALTER TABLE obj_head
    RENAME CONSTRAINT obj_head_acquisid_fkey TO obj_head_acquisid_fkey_old;
ALTER TABLE obj_head
    RENAME CONSTRAINT obj_head_classif_id_fkey TO obj_head_classif_id_fkey_old;
ALTER TABLE obj_head
    RENAME CONSTRAINT obj_head_classif_who_fkey TO obj_head_classif_who_fkey_old;
-- Referenced by:
ALTER TABLE obj_field
    DROP CONSTRAINT obj_field_objfid_fkey;
ALTER TABLE ONLY images
    DROP CONSTRAINT images_objid_fkey;
ALTER TABLE ONLY objectsclassifhisto
    DROP CONSTRAINT objectsclassifhisto_objid_fkey;
ALTER TABLE ONLY prediction
    DROP CONSTRAINT prediction_object_id_fkey;
ALTER TABLE ONLY prediction_histo
    DROP CONSTRAINT prediction_histo_object_id_fkey;
ALTER TABLE ONLY obj_cnn_features_vector
    DROP CONSTRAINT obj_cnn_features_vector_objcnnid_fkey;

ALTER TABLE obj_head
    RENAME TO obj_head_old;

CREATE TABLE obj_head
(
    objid           bigint                 NOT NULL,
    acquisid        bigint                 NOT NULL,
    classif_who     integer,
    classif_id      integer,
    objtime         time without time zone,
    latitude        double precision,
    longitude       double precision,
    depth_min       double precision,
    depth_max       double precision,
    objdate         date,
    classif_qual    character(1),
    sunpos          character(1),
    classif_date    timestamp without time zone,
    classif_score   double precision,
    orig_id         character varying(255) NOT NULL,
    object_link     character varying(255),
    complement_info character varying
)
    WITH (autovacuum_vacuum_scale_factor = '0.01', fillfactor = '98')
    TABLESPACE :OTHER_TBLSPC;

-- 11:33 -> 13:12
do
$$
    declare
        mpg     record;
        o_count integer;
        sum_o   integer = 0;
    begin
        for mpg in (select * from acqid_old_2_new order by new_id)
            loop
                insert into obj_head (objid,
                                             acquisid,
                                             classif_who,
                                             classif_id,
                                             objtime,
                                             latitude,
                                             longitude,
                                             depth_min,
                                             depth_max,
                                             objdate,
                                             classif_qual,
                                             sunpos,
                                             classif_date,
                                             classif_score,
                                             orig_id,
                                             object_link,
                                             complement_info)
                select objid,
                       mpg.new_id,
                       classif_who,
                       classif_id,
                       objtime,
                       latitude,
                       longitude,
                       depth_min,
                       depth_max,
                       objdate,
                       classif_qual,
                       sunpos,
                       classif_date,
                       classif_score,
                       orig_id,
                       object_link,
                       complement_info
                FROM obj_head_old
                WHERE acquisid = mpg.old_id
                ORDER BY objid;

                GET DIAGNOSTICS o_count = ROW_COUNT;
                IF (sum_o / 100000) != ((sum_o + o_count) / 100000) THEN
                    RAISE NOTICE 'index %, objects %, time:%', mpg.new_id, sum_o, clock_timestamp();
                    COMMIT;
                END IF;
                sum_o = sum_o + o_count;

            end loop;
        COMMIT;
    end;
$$;

-- 7. Restore primary keys and foreign keys
ALTER TABLE acquisitions
    ADD CONSTRAINT acquisitions_pkey PRIMARY KEY (acquisid);

ALTER TABLE process
    ADD CONSTRAINT process_pkey PRIMARY KEY (processid),
    ADD CONSTRAINT process_processid_fkey FOREIGN KEY (processid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE;

ALTER TABLE obj_head
    ADD CONSTRAINT obj_head_pkey PRIMARY KEY (objid),
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE,
    ADD CONSTRAINT obj_head_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES taxonomy (id),
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES users (id);

CREATE INDEX is_obj_head_acquisid_objid ON obj_head USING btree (acquisid, classif_qual) INCLUDE (classif_id);
CREATE INDEX is_objectsdate ON obj_head USING btree (objdate) INCLUDE (acquisid);
CREATE INDEX is_objectsdepth ON obj_head USING btree (depth_max, depth_min) INCLUDE (acquisid);
CREATE INDEX is_objectslatlong ON obj_head USING btree (latitude, longitude) INCLUDE (acquisid);
CREATE INDEX is_objectstime ON obj_head USING btree (objtime) INCLUDE (acquisid);


ALTER TABLE obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY images
    ADD CONSTRAINT images_objid_fkey FOREIGN KEY (objid) REFERENCES obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY prediction
    ADD CONSTRAINT prediction_object_id_fkey FOREIGN KEY (object_id) REFERENCES obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY prediction_histo
    ADD CONSTRAINT prediction_histo_object_id_fkey FOREIGN KEY (object_id) REFERENCES obj_head (objid) ON DELETE CASCADE;
ALTER TABLE ONLY obj_cnn_features_vector
    ADD CONSTRAINT obj_cnn_features_vector_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES obj_head (objid) ON DELETE CASCADE;

ALTER TABLE obj_head
    SET TABLESPACE pg_default;

-- Drop useless sequences

DROP SEQUENCE seq_samples;
DROP SEQUENCE seq_acquisitions;

-- 9. Cleanup

-- DROP TABLE acqid_old_2_new;

ALTER INDEX obj_field_acquisid_objfid_idx RENAME TO obj_field_acquisid_objfid_idx_old;

ALTER TABLE obj_field
    RENAME CONSTRAINT obj_field_pk TO obj_field_pk_old;

ALTER TABLE obj_field
    RENAME CONSTRAINT obj_field_objfid_fkey TO obj_field_objfid_fkey_old;

ALTER TABLE obj_field
    RENAME TO obj_field_old;

CREATE TABLE obj_field
(
    objfid    bigint NOT NULL,
    acquis_id bigint NOT NULL,
    n01       double precision,
    n02       double precision,
    n03       double precision,
    n04       double precision,
    n05       double precision,
    n06       double precision,
    n07       double precision,
    n08       double precision,
    n09       double precision,
    n10       double precision,
    n11       double precision,
    n12       double precision,
    n13       double precision,
    n14       double precision,
    n15       double precision,
    n16       double precision,
    n17       double precision,
    n18       double precision,
    n19       double precision,
    n20       double precision,
    n21       double precision,
    n22       double precision,
    n23       double precision,
    n24       double precision,
    n25       double precision,
    n26       double precision,
    n27       double precision,
    n28       double precision,
    n29       double precision,
    n30       double precision,
    n31       double precision,
    n32       double precision,
    n33       double precision,
    n34       double precision,
    n35       double precision,
    n36       double precision,
    n37       double precision,
    n38       double precision,
    n39       double precision,
    n40       double precision,
    n41       double precision,
    n42       double precision,
    n43       double precision,
    n44       double precision,
    n45       double precision,
    n46       double precision,
    n47       double precision,
    n48       double precision,
    n49       double precision,
    n50       double precision,
    n51       double precision,
    n52       double precision,
    n53       double precision,
    n54       double precision,
    n55       double precision,
    n56       double precision,
    n57       double precision,
    n58       double precision,
    n59       double precision,
    n60       double precision,
    n61       double precision,
    n62       double precision,
    n63       double precision,
    n64       double precision,
    n65       double precision,
    n66       double precision,
    n67       double precision,
    n68       double precision,
    n69       double precision,
    n70       double precision,
    n71       double precision,
    n72       double precision,
    n73       double precision,
    n74       double precision,
    n75       double precision,
    n76       double precision,
    n77       double precision,
    n78       double precision,
    n79       double precision,
    n80       double precision,
    n81       double precision,
    n82       double precision,
    n83       double precision,
    n84       double precision,
    n85       double precision,
    n86       double precision,
    n87       double precision,
    n88       double precision,
    n89       double precision,
    n90       double precision,
    n91       double precision,
    n92       double precision,
    n93       double precision,
    n94       double precision,
    n95       double precision,
    n96       double precision,
    n97       double precision,
    n98       double precision,
    n99       double precision,
    n100      double precision,
    n101      double precision,
    n102      double precision,
    n103      double precision,
    n104      double precision,
    n105      double precision,
    n106      double precision,
    n107      double precision,
    n108      double precision,
    n109      double precision,
    n110      double precision,
    n111      double precision,
    n112      double precision,
    n113      double precision,
    n114      double precision,
    n115      double precision,
    n116      double precision,
    n117      double precision,
    n118      double precision,
    n119      double precision,
    n120      double precision,
    n121      double precision,
    n122      double precision,
    n123      double precision,
    n124      double precision,
    n125      double precision,
    n126      double precision,
    n127      double precision,
    n128      double precision,
    n129      double precision,
    n130      double precision,
    n131      double precision,
    n132      double precision,
    n133      double precision,
    n134      double precision,
    n135      double precision,
    n136      double precision,
    n137      double precision,
    n138      double precision,
    n139      double precision,
    n140      double precision,
    n141      double precision,
    n142      double precision,
    n143      double precision,
    n144      double precision,
    n145      double precision,
    n146      double precision,
    n147      double precision,
    n148      double precision,
    n149      double precision,
    n150      double precision,
    n151      double precision,
    n152      double precision,
    n153      double precision,
    n154      double precision,
    n155      double precision,
    n156      double precision,
    n157      double precision,
    n158      double precision,
    n159      double precision,
    n160      double precision,
    n161      double precision,
    n162      double precision,
    n163      double precision,
    n164      double precision,
    n165      double precision,
    n166      double precision,
    n167      double precision,
    n168      double precision,
    n169      double precision,
    n170      double precision,
    n171      double precision,
    n172      double precision,
    n173      double precision,
    n174      double precision,
    n175      double precision,
    n176      double precision,
    n177      double precision,
    n178      double precision,
    n179      double precision,
    n180      double precision,
    n181      double precision,
    n182      double precision,
    n183      double precision,
    n184      double precision,
    n185      double precision,
    n186      double precision,
    n187      double precision,
    n188      double precision,
    n189      double precision,
    n190      double precision,
    n191      double precision,
    n192      double precision,
    n193      double precision,
    n194      double precision,
    n195      double precision,
    n196      double precision,
    n197      double precision,
    n198      double precision,
    n199      double precision,
    n200      double precision,
    n201      double precision,
    n202      double precision,
    n203      double precision,
    n204      double precision,
    n205      double precision,
    n206      double precision,
    n207      double precision,
    n208      double precision,
    n209      double precision,
    n210      double precision,
    n211      double precision,
    n212      double precision,
    n213      double precision,
    n214      double precision,
    n215      double precision,
    n216      double precision,
    n217      double precision,
    n218      double precision,
    n219      double precision,
    n220      double precision,
    n221      double precision,
    n222      double precision,
    n223      double precision,
    n224      double precision,
    n225      double precision,
    n226      double precision,
    n227      double precision,
    n228      double precision,
    n229      double precision,
    n230      double precision,
    n231      double precision,
    n232      double precision,
    n233      double precision,
    n234      double precision,
    n235      double precision,
    n236      double precision,
    n237      double precision,
    n238      double precision,
    n239      double precision,
    n240      double precision,
    n241      double precision,
    n242      double precision,
    n243      double precision,
    n244      double precision,
    n245      double precision,
    n246      double precision,
    n247      double precision,
    n248      double precision,
    n249      double precision,
    n250      double precision,
    n251      double precision,
    n252      double precision,
    n253      double precision,
    n254      double precision,
    n255      double precision,
    n256      double precision,
    n257      double precision,
    n258      double precision,
    n259      double precision,
    n260      double precision,
    n261      double precision,
    n262      double precision,
    n263      double precision,
    n264      double precision,
    n265      double precision,
    n266      double precision,
    n267      double precision,
    n268      double precision,
    n269      double precision,
    n270      double precision,
    n271      double precision,
    n272      double precision,
    n273      double precision,
    n274      double precision,
    n275      double precision,
    n276      double precision,
    n277      double precision,
    n278      double precision,
    n279      double precision,
    n280      double precision,
    n281      double precision,
    n282      double precision,
    n283      double precision,
    n284      double precision,
    n285      double precision,
    n286      double precision,
    n287      double precision,
    n288      double precision,
    n289      double precision,
    n290      double precision,
    n291      double precision,
    n292      double precision,
    n293      double precision,
    n294      double precision,
    n295      double precision,
    n296      double precision,
    n297      double precision,
    n298      double precision,
    n299      double precision,
    n300      double precision,
    n301      double precision,
    n302      double precision,
    n303      double precision,
    n304      double precision,
    n305      double precision,
    n306      double precision,
    n307      double precision,
    n308      double precision,
    n309      double precision,
    n310      double precision,
    n311      double precision,
    n312      double precision,
    n313      double precision,
    n314      double precision,
    n315      double precision,
    n316      double precision,
    n317      double precision,
    n318      double precision,
    n319      double precision,
    n320      double precision,
    n321      double precision,
    n322      double precision,
    n323      double precision,
    n324      double precision,
    n325      double precision,
    n326      double precision,
    n327      double precision,
    n328      double precision,
    n329      double precision,
    n330      double precision,
    n331      double precision,
    n332      double precision,
    n333      double precision,
    n334      double precision,
    n335      double precision,
    n336      double precision,
    n337      double precision,
    n338      double precision,
    n339      double precision,
    n340      double precision,
    n341      double precision,
    n342      double precision,
    n343      double precision,
    n344      double precision,
    n345      double precision,
    n346      double precision,
    n347      double precision,
    n348      double precision,
    n349      double precision,
    n350      double precision,
    n351      double precision,
    n352      double precision,
    n353      double precision,
    n354      double precision,
    n355      double precision,
    n356      double precision,
    n357      double precision,
    n358      double precision,
    n359      double precision,
    n360      double precision,
    n361      double precision,
    n362      double precision,
    n363      double precision,
    n364      double precision,
    n365      double precision,
    n366      double precision,
    n367      double precision,
    n368      double precision,
    n369      double precision,
    n370      double precision,
    n371      double precision,
    n372      double precision,
    n373      double precision,
    n374      double precision,
    n375      double precision,
    n376      double precision,
    n377      double precision,
    n378      double precision,
    n379      double precision,
    n380      double precision,
    n381      double precision,
    n382      double precision,
    n383      double precision,
    n384      double precision,
    n385      double precision,
    n386      double precision,
    n387      double precision,
    n388      double precision,
    n389      double precision,
    n390      double precision,
    n391      double precision,
    n392      double precision,
    n393      double precision,
    n394      double precision,
    n395      double precision,
    n396      double precision,
    n397      double precision,
    n398      double precision,
    n399      double precision,
    n400      double precision,
    n401      double precision,
    n402      double precision,
    n403      double precision,
    n404      double precision,
    n405      double precision,
    n406      double precision,
    n407      double precision,
    n408      double precision,
    n409      double precision,
    n410      double precision,
    n411      double precision,
    n412      double precision,
    n413      double precision,
    n414      double precision,
    n415      double precision,
    n416      double precision,
    n417      double precision,
    n418      double precision,
    n419      double precision,
    n420      double precision,
    n421      double precision,
    n422      double precision,
    n423      double precision,
    n424      double precision,
    n425      double precision,
    n426      double precision,
    n427      double precision,
    n428      double precision,
    n429      double precision,
    n430      double precision,
    n431      double precision,
    n432      double precision,
    n433      double precision,
    n434      double precision,
    n435      double precision,
    n436      double precision,
    n437      double precision,
    n438      double precision,
    n439      double precision,
    n440      double precision,
    n441      double precision,
    n442      double precision,
    n443      double precision,
    n444      double precision,
    n445      double precision,
    n446      double precision,
    n447      double precision,
    n448      double precision,
    n449      double precision,
    n450      double precision,
    n451      double precision,
    n452      double precision,
    n453      double precision,
    n454      double precision,
    n455      double precision,
    n456      double precision,
    n457      double precision,
    n458      double precision,
    n459      double precision,
    n460      double precision,
    n461      double precision,
    n462      double precision,
    n463      double precision,
    n464      double precision,
    n465      double precision,
    n466      double precision,
    n467      double precision,
    n468      double precision,
    n469      double precision,
    n470      double precision,
    n471      double precision,
    n472      double precision,
    n473      double precision,
    n474      double precision,
    n475      double precision,
    n476      double precision,
    n477      double precision,
    n478      double precision,
    n479      double precision,
    n480      double precision,
    n481      double precision,
    n482      double precision,
    n483      double precision,
    n484      double precision,
    n485      double precision,
    n486      double precision,
    n487      double precision,
    n488      double precision,
    n489      double precision,
    n490      double precision,
    n491      double precision,
    n492      double precision,
    n493      double precision,
    n494      double precision,
    n495      double precision,
    n496      double precision,
    n497      double precision,
    n498      double precision,
    n499      double precision,
    n500      double precision,
    t01       character varying(250),
    t02       character varying(250),
    t03       character varying(250),
    t04       character varying(250),
    t05       character varying(250),
    t06       character varying(250),
    t07       character varying(250),
    t08       character varying(250),
    t09       character varying(250),
    t10       character varying(250),
    t11       character varying(250),
    t12       character varying(250),
    t13       character varying(250),
    t14       character varying(250),
    t15       character varying(250),
    t16       character varying(250),
    t17       character varying(250),
    t18       character varying(250),
    t19       character varying(250),
    t20       character varying(250)
)
    WITH (autovacuum_vacuum_scale_factor = '0.01', fillfactor = '98', autovacuum_enabled = 'true')
    TABLESPACE :OTHER_TBLSPC;

ALTER TABLE obj_field
    ALTER COLUMN acquis_id SET STATISTICS 10000;

-- Durée : 19536610,045 ms (05:25:36,610) (nvme)
do
$$
    declare
        mpg     record;
        o_count integer;
        sum_o   integer = 0;
    begin
        for mpg in (select * from acqid_old_2_new order by new_id)
            loop
                insert into obj_field (objfid, acquis_id, n01, n02, n03, n04, n05, n06, n07, n08,
                                           n09, n10, n11,
                                           n12,
                                           n13, n14, n15, n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26,
                                           n27,
                                           n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40, n41,
                                           n42,
                                           n43, n44, n45, n46, n47, n48, n49, n50, n51, n52, n53, n54, n55, n56,
                                           n57,
                                           n58, n59, n60, n61, n62, n63, n64, n65, n66, n67, n68, n69, n70, n71,
                                           n72,
                                           n73, n74, n75, n76, n77, n78, n79, n80, n81, n82, n83, n84, n85, n86,
                                           n87,
                                           n88, n89, n90, n91, n92, n93, n94, n95, n96, n97, n98, n99, n100,
                                           n101, n102,
                                           n103, n104, n105, n106, n107, n108, n109, n110, n111, n112, n113,
                                           n114, n115,
                                           n116, n117, n118, n119, n120, n121, n122, n123, n124, n125, n126,
                                           n127, n128,
                                           n129, n130, n131, n132, n133, n134, n135, n136, n137, n138, n139,
                                           n140, n141,
                                           n142, n143, n144, n145, n146, n147, n148, n149, n150, n151, n152,
                                           n153, n154,
                                           n155, n156, n157, n158, n159, n160, n161, n162, n163, n164, n165,
                                           n166, n167,
                                           n168, n169, n170, n171, n172, n173, n174, n175, n176, n177, n178,
                                           n179, n180,
                                           n181, n182, n183, n184, n185, n186, n187, n188, n189, n190, n191,
                                           n192, n193,
                                           n194, n195, n196, n197, n198, n199, n200, n201, n202, n203, n204,
                                           n205, n206,
                                           n207, n208, n209, n210, n211, n212, n213, n214, n215, n216, n217,
                                           n218, n219,
                                           n220, n221, n222, n223, n224, n225, n226, n227, n228, n229, n230,
                                           n231, n232,
                                           n233, n234, n235, n236, n237, n238, n239, n240, n241, n242, n243,
                                           n244, n245,
                                           n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256,
                                           n257, n258,
                                           n259, n260, n261, n262, n263, n264, n265, n266, n267, n268, n269,
                                           n270, n271,
                                           n272, n273, n274, n275, n276, n277, n278, n279, n280, n281, n282,
                                           n283, n284,
                                           n285, n286, n287, n288, n289, n290, n291, n292, n293, n294, n295,
                                           n296, n297,
                                           n298, n299, n300, n301, n302, n303, n304, n305, n306, n307, n308,
                                           n309, n310,
                                           n311, n312, n313, n314, n315, n316, n317, n318, n319, n320, n321,
                                           n322, n323,
                                           n324, n325, n326, n327, n328, n329, n330, n331, n332, n333, n334,
                                           n335, n336,
                                           n337, n338, n339, n340, n341, n342, n343, n344, n345, n346, n347,
                                           n348, n349,
                                           n350, n351, n352, n353, n354, n355, n356, n357, n358, n359, n360,
                                           n361, n362,
                                           n363, n364, n365, n366, n367, n368, n369, n370, n371, n372, n373,
                                           n374, n375,
                                           n376, n377, n378, n379, n380, n381, n382, n383, n384, n385, n386,
                                           n387, n388,
                                           n389, n390, n391, n392, n393, n394, n395, n396, n397, n398, n399,
                                           n400, n401,
                                           n402, n403, n404, n405, n406, n407, n408, n409, n410, n411, n412,
                                           n413, n414,
                                           n415, n416, n417, n418, n419, n420, n421, n422, n423, n424, n425,
                                           n426, n427,
                                           n428, n429, n430, n431, n432, n433, n434, n435, n436, n437, n438,
                                           n439, n440,
                                           n441, n442, n443, n444, n445, n446, n447, n448, n449, n450, n451,
                                           n452, n453,
                                           n454, n455, n456, n457, n458, n459, n460, n461, n462, n463, n464,
                                           n465, n466,
                                           n467, n468, n469, n470, n471, n472, n473, n474, n475, n476, n477,
                                           n478, n479,
                                           n480, n481, n482, n483, n484, n485, n486, n487, n488, n489, n490,
                                           n491, n492,
                                           n493, n494, n495, n496, n497, n498, n499, n500,
                                           t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12, t13, t14,
                                           t15,
                                           t16, t17, t18, t19, t20)
                select objfid, mpg.new_id, n01, n02, n03, n04, n05, n06, n07, n08,
                                           n09, n10, n11,
                                           n12,
                                           n13, n14, n15, n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26,
                                           n27,
                                           n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40, n41,
                                           n42,
                                           n43, n44, n45, n46, n47, n48, n49, n50, n51, n52, n53, n54, n55, n56,
                                           n57,
                                           n58, n59, n60, n61, n62, n63, n64, n65, n66, n67, n68, n69, n70, n71,
                                           n72,
                                           n73, n74, n75, n76, n77, n78, n79, n80, n81, n82, n83, n84, n85, n86,
                                           n87,
                                           n88, n89, n90, n91, n92, n93, n94, n95, n96, n97, n98, n99, n100,
                                           n101, n102,
                                           n103, n104, n105, n106, n107, n108, n109, n110, n111, n112, n113,
                                           n114, n115,
                                           n116, n117, n118, n119, n120, n121, n122, n123, n124, n125, n126,
                                           n127, n128,
                                           n129, n130, n131, n132, n133, n134, n135, n136, n137, n138, n139,
                                           n140, n141,
                                           n142, n143, n144, n145, n146, n147, n148, n149, n150, n151, n152,
                                           n153, n154,
                                           n155, n156, n157, n158, n159, n160, n161, n162, n163, n164, n165,
                                           n166, n167,
                                           n168, n169, n170, n171, n172, n173, n174, n175, n176, n177, n178,
                                           n179, n180,
                                           n181, n182, n183, n184, n185, n186, n187, n188, n189, n190, n191,
                                           n192, n193,
                                           n194, n195, n196, n197, n198, n199, n200, n201, n202, n203, n204,
                                           n205, n206,
                                           n207, n208, n209, n210, n211, n212, n213, n214, n215, n216, n217,
                                           n218, n219,
                                           n220, n221, n222, n223, n224, n225, n226, n227, n228, n229, n230,
                                           n231, n232,
                                           n233, n234, n235, n236, n237, n238, n239, n240, n241, n242, n243,
                                           n244, n245,
                                           n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256,
                                           n257, n258,
                                           n259, n260, n261, n262, n263, n264, n265, n266, n267, n268, n269,
                                           n270, n271,
                                           n272, n273, n274, n275, n276, n277, n278, n279, n280, n281, n282,
                                           n283, n284,
                                           n285, n286, n287, n288, n289, n290, n291, n292, n293, n294, n295,
                                           n296, n297,
                                           n298, n299, n300, n301, n302, n303, n304, n305, n306, n307, n308,
                                           n309, n310,
                                           n311, n312, n313, n314, n315, n316, n317, n318, n319, n320, n321,
                                           n322, n323,
                                           n324, n325, n326, n327, n328, n329, n330, n331, n332, n333, n334,
                                           n335, n336,
                                           n337, n338, n339, n340, n341, n342, n343, n344, n345, n346, n347,
                                           n348, n349,
                                           n350, n351, n352, n353, n354, n355, n356, n357, n358, n359, n360,
                                           n361, n362,
                                           n363, n364, n365, n366, n367, n368, n369, n370, n371, n372, n373,
                                           n374, n375,
                                           n376, n377, n378, n379, n380, n381, n382, n383, n384, n385, n386,
                                           n387, n388,
                                           n389, n390, n391, n392, n393, n394, n395, n396, n397, n398, n399,
                                           n400, n401,
                                           n402, n403, n404, n405, n406, n407, n408, n409, n410, n411, n412,
                                           n413, n414,
                                           n415, n416, n417, n418, n419, n420, n421, n422, n423, n424, n425,
                                           n426, n427,
                                           n428, n429, n430, n431, n432, n433, n434, n435, n436, n437, n438,
                                           n439, n440,
                                           n441, n442, n443, n444, n445, n446, n447, n448, n449, n450, n451,
                                           n452, n453,
                                           n454, n455, n456, n457, n458, n459, n460, n461, n462, n463, n464,
                                           n465, n466,
                                           n467, n468, n469, n470, n471, n472, n473, n474, n475, n476, n477,
                                           n478, n479,
                                           n480, n481, n482, n483, n484, n485, n486, n487, n488, n489, n490,
                                           n491, n492,
                                           n493, n494, n495, n496, n497, n498, n499, n500,
                                           t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12, t13, t14,
                                           t15,
                                           t16, t17, t18, t19, t20
                FROM obj_field_old
                WHERE acquis_id = mpg.old_id
                ORDER BY objfid;

                GET DIAGNOSTICS o_count = ROW_COUNT;
                IF (sum_o / 100000) != ((sum_o + o_count) / 100000) THEN
                    RAISE NOTICE 'index %, objects %, time:%', mpg.new_id, sum_o, clock_timestamp();
                    COMMIT;
                END IF;
                sum_o = sum_o + o_count;

            end loop;
        COMMIT;
    end;
$$;

ALTER TABLE obj_field
    OWNER TO postgres;

ALTER TABLE obj_field
    ADD CONSTRAINT obj_field_pk PRIMARY KEY (objfid) WITH (fillfactor ='98');

ALTER TABLE obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES obj_head (objid) ON DELETE CASCADE;

CREATE INDEX obj_field_acquisid_objfid_idx ON obj_field USING btree (acquis_id, objfid) WITH (fillfactor ='98');

GRANT SELECT ON TABLE obj_field TO readerole;

ALTER TABLE obj_field
    SET TABLESPACE pg_default;

---- OBJ
-- Durée : 1013986,567 ms (16:53,987) NVME drive
-- PROD: Durée : 1740768,903 ms (29:00,769)
CREATE UNLOGGED TABLE objid_old_2_new TABLESPACE :OTHER_TBLSPC AS
SELECT objid AS old_id,
       (projid * :OBJ_MULT) + ROW_NUMBER() OVER (
        PARTITION BY projid
        ORDER BY objid) AS new_id
	 FROM obj_head obh
	 JOIN acquisitions acq ON acq.acquisid = obh.acquisid
	 JOIN samples sam ON sam.sampleid = acq.acq_sample_id;

-- Durée : 528378,732 ms (08:48,379)
CREATE UNIQUE INDEX objid_mapping_old_to_new ON objid_old_2_new (old_id) INCLUDE (new_id);

-- Durée : 453830,658 ms (07:33,831)
CREATE UNIQUE INDEX objid_mapping_new_to_old ON objid_old_2_new (new_id) INCLUDE (old_id);

CREATE TABLE obj_head
(
    objid           bigint                 NOT NULL,
    acquisid        bigint                 NOT NULL,
    classif_who     integer,
    classif_id      integer,
    objtime         time without time zone,
    latitude        double precision,
    longitude       double precision,
    depth_min       double precision,
    depth_max       double precision,
    objdate         date,
    classif_qual    character(1),
    sunpos          character(1),
    classif_date    timestamp without time zone,
    classif_score   double precision,
    orig_id         character varying(255) NOT NULL,
    object_link     character varying(255),
    complement_info character varying
)
    PARTITION BY RANGE (objid);

CREATE TABLE obj_head_p1 PARTITION OF obj_head
    FOR VALUES FROM (0) TO (923*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p2 PARTITION OF obj_head
    FOR VALUES FROM (923*:OBJ_MULT) TO (3118*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p3 PARTITION OF obj_head
    FOR VALUES FROM (3118*:OBJ_MULT) TO (4591*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p4 PARTITION OF obj_head
    FOR VALUES FROM (4591*:OBJ_MULT) TO (5976*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p5 PARTITION OF obj_head
    FOR VALUES FROM (5976*:OBJ_MULT) TO (7380*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p6 PARTITION OF obj_head
    FOR VALUES FROM (7380*:OBJ_MULT) TO (9107*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p7 PARTITION OF obj_head
    FOR VALUES FROM (9107*:OBJ_MULT) TO (10956*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p8 PARTITION OF obj_head
    FOR VALUES FROM (10956*:OBJ_MULT) TO (12308*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p9 PARTITION OF obj_head
    FOR VALUES FROM (12308*:OBJ_MULT) TO (14077*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p10 PARTITION OF obj_head
    FOR VALUES FROM (14077*:OBJ_MULT) TO (15239*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p11 PARTITION OF obj_head
    FOR VALUES FROM (15239*:OBJ_MULT) TO (16517*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p12 PARTITION OF obj_head
    FOR VALUES FROM (16517*:OBJ_MULT) TO (17161*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p13 PARTITION OF obj_head
    FOR VALUES FROM (17161*:OBJ_MULT) TO (17794*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p14 PARTITION OF obj_head
    FOR VALUES FROM (17794*:OBJ_MULT) TO (19042*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p15 PARTITION OF obj_head
    FOR VALUES FROM (19042*:OBJ_MULT) TO (20422*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_p16 PARTITION OF obj_head
    FOR VALUES FROM (20422*:OBJ_MULT) TO (21431*:OBJ_MULT)
    TABLESPACE :OTHER_TBLSPC;
CREATE TABLE obj_head_default PARTITION OF obj_head DEFAULT
    TABLESPACE :OTHER_TBLSPC;

--    WITH (autovacuum_vacuum_scale_factor = '0.01', fillfactor = '98');
--    TABLESPACE :OTHER_TBLSPC;

do
$$
    declare
        acq_mpg     record;
        o_count integer;
        sum_o   integer = 0;
    begin
        for acq_mpg in (select * from acqid_old_2_new order by new_id)
            loop
                insert into obj_head (objid,
                                             acquisid,
                                             classif_who,
                                             classif_id,
                                             objtime,
                                             latitude,
                                             longitude,
                                             depth_min,
                                             depth_max,
                                             objdate,
                                             classif_qual,
                                             sunpos,
                                             classif_date,
                                             classif_score,
                                             orig_id,
                                             object_link,
                                             complement_info)
                select obj_mpg.new_id,
                       acq_mpg.new_id,
                       classif_who,
                       classif_id,
                       objtime,
                       latitude,
                       longitude,
                       depth_min,
                       depth_max,
                       objdate,
                       classif_qual,
                       sunpos,
                       classif_date,
                       classif_score,
                       orig_id,
                       object_link,
                       complement_info
                FROM obj_head_old
                JOIN objid_old_2_new obj_mpg ON obj_mpg.old_id = obj_head_old.objid
                WHERE acquisid = acq_mpg.new_id -- TODO acq_mpg.old_id
                ORDER BY objid;

                GET DIAGNOSTICS o_count = ROW_COUNT;
                IF (sum_o / 100000) != ((sum_o + o_count) / 100000) THEN
                    RAISE NOTICE 'index %, objects %, time:%', acq_mpg.new_id, sum_o, clock_timestamp();
                    COMMIT;
                END IF;
                sum_o = sum_o + o_count;

            end loop;
        COMMIT;
    end;
$$;

ALTER TABLE obj_head
    ADD CONSTRAINT obj_head_pkey PRIMARY KEY (objid),
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES acquisitions (acquisid) ON DELETE CASCADE,
    ADD CONSTRAINT obj_head_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES taxonomy (id),
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES users (id);

CREATE INDEX is_obj_head_acquisid_objid ON obj_head USING btree (acquisid, classif_qual) INCLUDE (classif_id);
CREATE INDEX is_objectsdate ON obj_head USING btree (objdate) INCLUDE (acquisid);
CREATE INDEX is_objectsdepth ON obj_head USING btree (depth_max, depth_min) INCLUDE (acquisid);
CREATE INDEX is_objectslatlong ON obj_head USING btree (latitude, longitude) INCLUDE (acquisid);
CREATE INDEX is_objectstime ON obj_head USING btree (objtime) INCLUDE (acquisid);

CREATE STATISTICS obj_head_classif_if_qual ON classif_id, classif_qual FROM obj_head;
ALTER STATISTICS obj_head_classif_if_qual OWNER TO postgres;
CREATE STATISTICS obj_head_score_if_p ON classif_qual, classif_score FROM obj_head;
ALTER STATISTICS obj_head_score_if_p OWNER TO postgres;
CREATE STATISTICS obj_head_user_if_v_d ON classif_qual, classif_who FROM obj_head;
ALTER STATISTICS obj_head_user_if_v_d OWNER TO postgres;


------------------------ OBJ_FIELD -------------------
ALTER TABLE obj_field
    RENAME CONSTRAINT obj_field_pk TO obj_field_pk_old;

ALTER TABLE obj_field
    RENAME TO obj_field_old;

ALTER INDEX obj_field_acquisid_objfid_idx RENAME TO obj_field_acquisid_objfid_idx_old;

ALTER TABLE obj_field_old
    RENAME CONSTRAINT obj_field_objfid_fkey TO obj_field_objfid_fkey_old;

CREATE TABLE obj_field
(
    objfid    bigint NOT NULL,
    acquis_id bigint NOT NULL,
    n01       double precision,
    n02       double precision,
    n03       double precision,
    n04       double precision,
    n05       double precision,
    n06       double precision,
    n07       double precision,
    n08       double precision,
    n09       double precision,
    n10       double precision,
    n11       double precision,
    n12       double precision,
    n13       double precision,
    n14       double precision,
    n15       double precision,
    n16       double precision,
    n17       double precision,
    n18       double precision,
    n19       double precision,
    n20       double precision,
    n21       double precision,
    n22       double precision,
    n23       double precision,
    n24       double precision,
    n25       double precision,
    n26       double precision,
    n27       double precision,
    n28       double precision,
    n29       double precision,
    n30       double precision,
    n31       double precision,
    n32       double precision,
    n33       double precision,
    n34       double precision,
    n35       double precision,
    n36       double precision,
    n37       double precision,
    n38       double precision,
    n39       double precision,
    n40       double precision,
    n41       double precision,
    n42       double precision,
    n43       double precision,
    n44       double precision,
    n45       double precision,
    n46       double precision,
    n47       double precision,
    n48       double precision,
    n49       double precision,
    n50       double precision,
    n51       double precision,
    n52       double precision,
    n53       double precision,
    n54       double precision,
    n55       double precision,
    n56       double precision,
    n57       double precision,
    n58       double precision,
    n59       double precision,
    n60       double precision,
    n61       double precision,
    n62       double precision,
    n63       double precision,
    n64       double precision,
    n65       double precision,
    n66       double precision,
    n67       double precision,
    n68       double precision,
    n69       double precision,
    n70       double precision,
    n71       double precision,
    n72       double precision,
    n73       double precision,
    n74       double precision,
    n75       double precision,
    n76       double precision,
    n77       double precision,
    n78       double precision,
    n79       double precision,
    n80       double precision,
    n81       double precision,
    n82       double precision,
    n83       double precision,
    n84       double precision,
    n85       double precision,
    n86       double precision,
    n87       double precision,
    n88       double precision,
    n89       double precision,
    n90       double precision,
    n91       double precision,
    n92       double precision,
    n93       double precision,
    n94       double precision,
    n95       double precision,
    n96       double precision,
    n97       double precision,
    n98       double precision,
    n99       double precision,
    n100      double precision,
    n101      double precision,
    n102      double precision,
    n103      double precision,
    n104      double precision,
    n105      double precision,
    n106      double precision,
    n107      double precision,
    n108      double precision,
    n109      double precision,
    n110      double precision,
    n111      double precision,
    n112      double precision,
    n113      double precision,
    n114      double precision,
    n115      double precision,
    n116      double precision,
    n117      double precision,
    n118      double precision,
    n119      double precision,
    n120      double precision,
    n121      double precision,
    n122      double precision,
    n123      double precision,
    n124      double precision,
    n125      double precision,
    n126      double precision,
    n127      double precision,
    n128      double precision,
    n129      double precision,
    n130      double precision,
    n131      double precision,
    n132      double precision,
    n133      double precision,
    n134      double precision,
    n135      double precision,
    n136      double precision,
    n137      double precision,
    n138      double precision,
    n139      double precision,
    n140      double precision,
    n141      double precision,
    n142      double precision,
    n143      double precision,
    n144      double precision,
    n145      double precision,
    n146      double precision,
    n147      double precision,
    n148      double precision,
    n149      double precision,
    n150      double precision,
    n151      double precision,
    n152      double precision,
    n153      double precision,
    n154      double precision,
    n155      double precision,
    n156      double precision,
    n157      double precision,
    n158      double precision,
    n159      double precision,
    n160      double precision,
    n161      double precision,
    n162      double precision,
    n163      double precision,
    n164      double precision,
    n165      double precision,
    n166      double precision,
    n167      double precision,
    n168      double precision,
    n169      double precision,
    n170      double precision,
    n171      double precision,
    n172      double precision,
    n173      double precision,
    n174      double precision,
    n175      double precision,
    n176      double precision,
    n177      double precision,
    n178      double precision,
    n179      double precision,
    n180      double precision,
    n181      double precision,
    n182      double precision,
    n183      double precision,
    n184      double precision,
    n185      double precision,
    n186      double precision,
    n187      double precision,
    n188      double precision,
    n189      double precision,
    n190      double precision,
    n191      double precision,
    n192      double precision,
    n193      double precision,
    n194      double precision,
    n195      double precision,
    n196      double precision,
    n197      double precision,
    n198      double precision,
    n199      double precision,
    n200      double precision,
    n201      double precision,
    n202      double precision,
    n203      double precision,
    n204      double precision,
    n205      double precision,
    n206      double precision,
    n207      double precision,
    n208      double precision,
    n209      double precision,
    n210      double precision,
    n211      double precision,
    n212      double precision,
    n213      double precision,
    n214      double precision,
    n215      double precision,
    n216      double precision,
    n217      double precision,
    n218      double precision,
    n219      double precision,
    n220      double precision,
    n221      double precision,
    n222      double precision,
    n223      double precision,
    n224      double precision,
    n225      double precision,
    n226      double precision,
    n227      double precision,
    n228      double precision,
    n229      double precision,
    n230      double precision,
    n231      double precision,
    n232      double precision,
    n233      double precision,
    n234      double precision,
    n235      double precision,
    n236      double precision,
    n237      double precision,
    n238      double precision,
    n239      double precision,
    n240      double precision,
    n241      double precision,
    n242      double precision,
    n243      double precision,
    n244      double precision,
    n245      double precision,
    n246      double precision,
    n247      double precision,
    n248      double precision,
    n249      double precision,
    n250      double precision,
    n251      double precision,
    n252      double precision,
    n253      double precision,
    n254      double precision,
    n255      double precision,
    n256      double precision,
    n257      double precision,
    n258      double precision,
    n259      double precision,
    n260      double precision,
    n261      double precision,
    n262      double precision,
    n263      double precision,
    n264      double precision,
    n265      double precision,
    n266      double precision,
    n267      double precision,
    n268      double precision,
    n269      double precision,
    n270      double precision,
    n271      double precision,
    n272      double precision,
    n273      double precision,
    n274      double precision,
    n275      double precision,
    n276      double precision,
    n277      double precision,
    n278      double precision,
    n279      double precision,
    n280      double precision,
    n281      double precision,
    n282      double precision,
    n283      double precision,
    n284      double precision,
    n285      double precision,
    n286      double precision,
    n287      double precision,
    n288      double precision,
    n289      double precision,
    n290      double precision,
    n291      double precision,
    n292      double precision,
    n293      double precision,
    n294      double precision,
    n295      double precision,
    n296      double precision,
    n297      double precision,
    n298      double precision,
    n299      double precision,
    n300      double precision,
    n301      double precision,
    n302      double precision,
    n303      double precision,
    n304      double precision,
    n305      double precision,
    n306      double precision,
    n307      double precision,
    n308      double precision,
    n309      double precision,
    n310      double precision,
    n311      double precision,
    n312      double precision,
    n313      double precision,
    n314      double precision,
    n315      double precision,
    n316      double precision,
    n317      double precision,
    n318      double precision,
    n319      double precision,
    n320      double precision,
    n321      double precision,
    n322      double precision,
    n323      double precision,
    n324      double precision,
    n325      double precision,
    n326      double precision,
    n327      double precision,
    n328      double precision,
    n329      double precision,
    n330      double precision,
    n331      double precision,
    n332      double precision,
    n333      double precision,
    n334      double precision,
    n335      double precision,
    n336      double precision,
    n337      double precision,
    n338      double precision,
    n339      double precision,
    n340      double precision,
    n341      double precision,
    n342      double precision,
    n343      double precision,
    n344      double precision,
    n345      double precision,
    n346      double precision,
    n347      double precision,
    n348      double precision,
    n349      double precision,
    n350      double precision,
    n351      double precision,
    n352      double precision,
    n353      double precision,
    n354      double precision,
    n355      double precision,
    n356      double precision,
    n357      double precision,
    n358      double precision,
    n359      double precision,
    n360      double precision,
    n361      double precision,
    n362      double precision,
    n363      double precision,
    n364      double precision,
    n365      double precision,
    n366      double precision,
    n367      double precision,
    n368      double precision,
    n369      double precision,
    n370      double precision,
    n371      double precision,
    n372      double precision,
    n373      double precision,
    n374      double precision,
    n375      double precision,
    n376      double precision,
    n377      double precision,
    n378      double precision,
    n379      double precision,
    n380      double precision,
    n381      double precision,
    n382      double precision,
    n383      double precision,
    n384      double precision,
    n385      double precision,
    n386      double precision,
    n387      double precision,
    n388      double precision,
    n389      double precision,
    n390      double precision,
    n391      double precision,
    n392      double precision,
    n393      double precision,
    n394      double precision,
    n395      double precision,
    n396      double precision,
    n397      double precision,
    n398      double precision,
    n399      double precision,
    n400      double precision,
    n401      double precision,
    n402      double precision,
    n403      double precision,
    n404      double precision,
    n405      double precision,
    n406      double precision,
    n407      double precision,
    n408      double precision,
    n409      double precision,
    n410      double precision,
    n411      double precision,
    n412      double precision,
    n413      double precision,
    n414      double precision,
    n415      double precision,
    n416      double precision,
    n417      double precision,
    n418      double precision,
    n419      double precision,
    n420      double precision,
    n421      double precision,
    n422      double precision,
    n423      double precision,
    n424      double precision,
    n425      double precision,
    n426      double precision,
    n427      double precision,
    n428      double precision,
    n429      double precision,
    n430      double precision,
    n431      double precision,
    n432      double precision,
    n433      double precision,
    n434      double precision,
    n435      double precision,
    n436      double precision,
    n437      double precision,
    n438      double precision,
    n439      double precision,
    n440      double precision,
    n441      double precision,
    n442      double precision,
    n443      double precision,
    n444      double precision,
    n445      double precision,
    n446      double precision,
    n447      double precision,
    n448      double precision,
    n449      double precision,
    n450      double precision,
    n451      double precision,
    n452      double precision,
    n453      double precision,
    n454      double precision,
    n455      double precision,
    n456      double precision,
    n457      double precision,
    n458      double precision,
    n459      double precision,
    n460      double precision,
    n461      double precision,
    n462      double precision,
    n463      double precision,
    n464      double precision,
    n465      double precision,
    n466      double precision,
    n467      double precision,
    n468      double precision,
    n469      double precision,
    n470      double precision,
    n471      double precision,
    n472      double precision,
    n473      double precision,
    n474      double precision,
    n475      double precision,
    n476      double precision,
    n477      double precision,
    n478      double precision,
    n479      double precision,
    n480      double precision,
    n481      double precision,
    n482      double precision,
    n483      double precision,
    n484      double precision,
    n485      double precision,
    n486      double precision,
    n487      double precision,
    n488      double precision,
    n489      double precision,
    n490      double precision,
    n491      double precision,
    n492      double precision,
    n493      double precision,
    n494      double precision,
    n495      double precision,
    n496      double precision,
    n497      double precision,
    n498      double precision,
    n499      double precision,
    n500      double precision,
    t01       character varying(250),
    t02       character varying(250),
    t03       character varying(250),
    t04       character varying(250),
    t05       character varying(250),
    t06       character varying(250),
    t07       character varying(250),
    t08       character varying(250),
    t09       character varying(250),
    t10       character varying(250),
    t11       character varying(250),
    t12       character varying(250),
    t13       character varying(250),
    t14       character varying(250),
    t15       character varying(250),
    t16       character varying(250),
    t17       character varying(250),
    t18       character varying(250),
    t19       character varying(250),
    t20       character varying(250)
)
PARTITION BY RANGE (objfid);

CREATE TABLE obj_field_p1 PARTITION OF obj_field
    FOR VALUES FROM (0) TO (923*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p2 PARTITION OF obj_field
    FOR VALUES FROM (923*:OBJ_MULT) TO (3118*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p3 PARTITION OF obj_field
    FOR VALUES FROM (3118*:OBJ_MULT) TO (4591*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p4 PARTITION OF obj_field
    FOR VALUES FROM (4591*:OBJ_MULT) TO (5976*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p5 PARTITION OF obj_field
    FOR VALUES FROM (5976*:OBJ_MULT) TO (7380*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p6 PARTITION OF obj_field
    FOR VALUES FROM (7380*:OBJ_MULT) TO (9107*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p7 PARTITION OF obj_field
    FOR VALUES FROM (9107*:OBJ_MULT) TO (10956*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p8 PARTITION OF obj_field
    FOR VALUES FROM (10956*:OBJ_MULT) TO (12308*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p9 PARTITION OF obj_field
    FOR VALUES FROM (12308*:OBJ_MULT) TO (14077*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p10 PARTITION OF obj_field
    FOR VALUES FROM (14077*:OBJ_MULT) TO (15239*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p11 PARTITION OF obj_field
    FOR VALUES FROM (15239*:OBJ_MULT) TO (16517*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p12 PARTITION OF obj_field
    FOR VALUES FROM (16517*:OBJ_MULT) TO (17161*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p13 PARTITION OF obj_field
    FOR VALUES FROM (17161*:OBJ_MULT) TO (17794*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p14 PARTITION OF obj_field
    FOR VALUES FROM (17794*:OBJ_MULT) TO (19042*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p15 PARTITION OF obj_field
    FOR VALUES FROM (19042*:OBJ_MULT) TO (20422*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_p16 PARTITION OF obj_field
    FOR VALUES FROM (20422*:OBJ_MULT) TO (21431*:OBJ_MULT)
    /*TABLESPACE default*/;
CREATE TABLE obj_field_default PARTITION OF obj_field DEFAULT
    /*TABLESPACE default*/;

do
$$
    declare
        acq_mpg     record;
        o_count integer;
        sum_o   integer = 0;
    begin
        for acq_mpg in (select * from acqid_old_2_new order by new_id)
            loop
                insert into obj_field (objfid, acquis_id, n01, n02, n03, n04, n05, n06, n07, n08,
                                           n09, n10, n11,
                                           n12,
                                           n13, n14, n15, n16, n17, n18, n19, n20, n21, n22, n23, n24, n25, n26,
                                           n27,
                                           n28, n29, n30, n31, n32, n33, n34, n35, n36, n37, n38, n39, n40, n41,
                                           n42,
                                           n43, n44, n45, n46, n47, n48, n49, n50, n51, n52, n53, n54, n55, n56,
                                           n57,
                                           n58, n59, n60, n61, n62, n63, n64, n65, n66, n67, n68, n69, n70, n71,
                                           n72,
                                           n73, n74, n75, n76, n77, n78, n79, n80, n81, n82, n83, n84, n85, n86,
                                           n87,
                                           n88, n89, n90, n91, n92, n93, n94, n95, n96, n97, n98, n99, n100,
                                           n101, n102,
                                           n103, n104, n105, n106, n107, n108, n109, n110, n111, n112, n113,
                                           n114, n115,
                                           n116, n117, n118, n119, n120, n121, n122, n123, n124, n125, n126,
                                           n127, n128,
                                           n129, n130, n131, n132, n133, n134, n135, n136, n137, n138, n139,
                                           n140, n141,
                                           n142, n143, n144, n145, n146, n147, n148, n149, n150, n151, n152,
                                           n153, n154,
                                           n155, n156, n157, n158, n159, n160, n161, n162, n163, n164, n165,
                                           n166, n167,
                                           n168, n169, n170, n171, n172, n173, n174, n175, n176, n177, n178,
                                           n179, n180,
                                           n181, n182, n183, n184, n185, n186, n187, n188, n189, n190, n191,
                                           n192, n193,
                                           n194, n195, n196, n197, n198, n199, n200, n201, n202, n203, n204,
                                           n205, n206,
                                           n207, n208, n209, n210, n211, n212, n213, n214, n215, n216, n217,
                                           n218, n219,
                                           n220, n221, n222, n223, n224, n225, n226, n227, n228, n229, n230,
                                           n231, n232,
                                           n233, n234, n235, n236, n237, n238, n239, n240, n241, n242, n243,
                                           n244, n245,
                                           n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256,
                                           n257, n258,
                                           n259, n260, n261, n262, n263, n264, n265, n266, n267, n268, n269,
                                           n270, n271,
                                           n272, n273, n274, n275, n276, n277, n278, n279, n280, n281, n282,
                                           n283, n284,
                                           n285, n286, n287, n288, n289, n290, n291, n292, n293, n294, n295,
                                           n296, n297,
                                           n298, n299, n300, n301, n302, n303, n304, n305, n306, n307, n308,
                                           n309, n310,
                                           n311, n312, n313, n314, n315, n316, n317, n318, n319, n320, n321,
                                           n322, n323,
                                           n324, n325, n326, n327, n328, n329, n330, n331, n332, n333, n334,
                                           n335, n336,
                                           n337, n338, n339, n340, n341, n342, n343, n344, n345, n346, n347,
                                           n348, n349,
                                           n350, n351, n352, n353, n354, n355, n356, n357, n358, n359, n360,
                                           n361, n362,
                                           n363, n364, n365, n366, n367, n368, n369, n370, n371, n372, n373,
                                           n374, n375,
                                           n376, n377, n378, n379, n380, n381, n382, n383, n384, n385, n386,
                                           n387, n388,
                                           n389, n390, n391, n392, n393, n394, n395, n396, n397, n398, n399,
                                           n400, n401,
                                           n402, n403, n404, n405, n406, n407, n408, n409, n410, n411, n412,
                                           n413, n414,
                                           n415, n416, n417, n418, n419, n420, n421, n422, n423, n424, n425,
                                           n426, n427,
                                           n428, n429, n430, n431, n432, n433, n434, n435, n436, n437, n438,
                                           n439, n440,
                                           n441, n442, n443, n444, n445, n446, n447, n448, n449, n450, n451,
                                           n452, n453,
                                           n454, n455, n456, n457, n458, n459, n460, n461, n462, n463, n464,
                                           n465, n466,
                                           n467, n468, n469, n470, n471, n472, n473, n474, n475, n476, n477,
                                           n478, n479,
                                           n480, n481, n482, n483, n484, n485, n486, n487, n488, n489, n490,
                                           n491, n492,
                                           n493, n494, n495, n496, n497, n498, n499, n500,
                                           t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12, t13, t14,
                                           t15,
                                           t16, t17, t18, t19, t20)
                select obj_mpg.new_id,
                       acq_mpg.new_id,n01,n02,n03,n04,n05,n06,n07,n08,
                       n09,n10,n11,
                       n12,
                       n13,n14,n15,n16,n17,n18,n19,n20,n21,n22,n23,n24,n25,n26,
                       n27,
                       n28,n29,n30,n31,n32,n33,n34,n35,n36,n37,n38,n39,n40,n41,
                       n42,
                       n43,n44,n45,n46,n47,n48,n49,n50,n51,n52,n53,n54,n55,n56,
                       n57,
                       n58,n59,n60,n61,n62,n63,n64,n65,n66,n67,n68,n69,n70,n71,
                       n72,
                       n73,n74,n75,n76,n77,n78,n79,n80,n81,n82,n83,n84,n85,n86,
                       n87,
                       n88,n89,n90,n91,n92,n93,n94,n95,n96,n97,n98,n99,n100,
                       n101,n102,
                       n103,n104,n105,n106,n107,n108,n109,n110,n111,n112,n113,
                       n114,n115,
                       n116,n117,n118,n119,n120,n121,n122,n123,n124,n125,n126,
                       n127,n128,
                       n129,n130,n131,n132,n133,n134,n135,n136,n137,n138,n139,
                       n140,n141,
                       n142,n143,n144,n145,n146,n147,n148,n149,n150,n151,n152,
                       n153,n154,
                       n155,n156,n157,n158,n159,n160,n161,n162,n163,n164,n165,
                       n166,n167,
                       n168,n169,n170,n171,n172,n173,n174,n175,n176,n177,n178,
                       n179,n180,
                       n181,n182,n183,n184,n185,n186,n187,n188,n189,n190,n191,
                       n192,n193,
                       n194,n195,n196,n197,n198,n199,n200,n201,n202,n203,n204,
                       n205,n206,
                       n207,n208,n209,n210,n211,n212,n213,n214,n215,n216,n217,
                       n218,n219,
                       n220,n221,n222,n223,n224,n225,n226,n227,n228,n229,n230,
                       n231,n232,
                       n233,n234,n235,n236,n237,n238,n239,n240,n241,n242,n243,
                       n244,n245,
                       n246,n247,n248,n249,n250,n251,n252,n253,n254,n255,n256,
                       n257,n258,
                       n259,n260,n261,n262,n263,n264,n265,n266,n267,n268,n269,
                       n270,n271,
                       n272,n273,n274,n275,n276,n277,n278,n279,n280,n281,n282,
                       n283,n284,
                       n285,n286,n287,n288,n289,n290,n291,n292,n293,n294,n295,
                       n296,n297,
                       n298,n299,n300,n301,n302,n303,n304,n305,n306,n307,n308,
                       n309,n310,
                       n311,n312,n313,n314,n315,n316,n317,n318,n319,n320,n321,
                       n322,n323,
                       n324,n325,n326,n327,n328,n329,n330,n331,n332,n333,n334,
                       n335,n336,
                       n337,n338,n339,n340,n341,n342,n343,n344,n345,n346,n347,
                       n348,n349,
                       n350,n351,n352,n353,n354,n355,n356,n357,n358,n359,n360,
                       n361,n362,
                       n363,n364,n365,n366,n367,n368,n369,n370,n371,n372,n373,
                       n374,n375,
                       n376,n377,n378,n379,n380,n381,n382,n383,n384,n385,n386,
                       n387,n388,
                       n389,n390,n391,n392,n393,n394,n395,n396,n397,n398,n399,
                       n400,n401,
                       n402,n403,n404,n405,n406,n407,n408,n409,n410,n411,n412,
                       n413,n414,
                       n415,n416,n417,n418,n419,n420,n421,n422,n423,n424,n425,
                       n426,n427,
                       n428,n429,n430,n431,n432,n433,n434,n435,n436,n437,n438,
                       n439,n440,
                       n441,n442,n443,n444,n445,n446,n447,n448,n449,n450,n451,
                       n452,n453,
                       n454,n455,n456,n457,n458,n459,n460,n461,n462,n463,n464,
                       n465,n466,
                       n467,n468,n469,n470,n471,n472,n473,n474,n475,n476,n477,
                       n478,n479,
                       n480,n481,n482,n483,n484,n485,n486,n487,n488,n489,n490,
                       n491,n492,
                       n493,n494,n495,n496,n497,n498,n499,n500,
                       t01,t02,t03,t04,t05,t06,t07,t08,t09,t10,t11,t12,t13,t14,
                       t15,
                       t16,t17,t18,t19,t20
                FROM obj_field_old
                JOIN objid_old_2_new obj_mpg ON obj_mpg.old_id = obj_field_old.objfid
                WHERE acquis_id = acq_mpg.new_id -- TODO
                ORDER BY objfid;

                GET DIAGNOSTICS o_count = ROW_COUNT;
                IF (sum_o / 100000) != ((sum_o + o_count) / 100000) THEN
                    RAISE NOTICE 'index %, objects %, time:%', acq_mpg.new_id, sum_o, clock_timestamp();
                    COMMIT;
                END IF;
                sum_o = sum_o + o_count;

            end loop;
        COMMIT;
    end;
$$;

ALTER TABLE obj_field
    OWNER TO postgres;

ALTER TABLE obj_field
    ADD CONSTRAINT obj_field_pk PRIMARY KEY (objfid) WITH (fillfactor ='98');

ALTER TABLE obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES obj_head(objid) ON DELETE CASCADE;

CREATE INDEX obj_field_acquisid_objfid_idx ON obj_field USING btree (acquis_id, objfid) WITH (fillfactor ='98');

GRANT SELECT ON TABLE obj_field TO readerole;

------------------------ IMAGES ----------------------

ALTER TABLE images RENAME TO images_old;
ALTER INDEX images_pkey RENAME TO images_pkey_old;
ALTER INDEX images_objid_fkey RENAME TO images_objid_fkey_old;

CREATE TABLE images (
    imgid bigint NOT NULL,
    objid bigint NOT NULL,
    imgrank smallint NOT NULL,
    width smallint NOT NULL,
    height smallint NOT NULL,
    orig_file_name character varying(255) NOT NULL,
    thumb_width smallint,
    thumb_height smallint
) TABLESPACE home_indexes;

INSERT INTO images
SELECT imgid,
       mpg_obj.new_id,
       imgrank,
       width,
       height,
       orig_file_name,
       thumb_width,
       thumb_height
  FROM images_old
  JOIN objid_old_2_new mpg_obj ON mpg_obj.old_id = objid;

ALTER TABLE ONLY images ALTER COLUMN objid SET STATISTICS 10000;

ALTER TABLE images OWNER TO postgres;

ALTER TABLE ONLY images
    ADD CONSTRAINT images_pkey PRIMARY KEY (objid, imgrank);

ALTER TABLE ONLY images
    ADD CONSTRAINT images_objid_fkey FOREIGN KEY (objid) REFERENCES obj_head(objid);

GRANT SELECT ON TABLE images TO readerole;
GRANT SELECT ON TABLE images TO zoo;

VACUUM VERBOSE images;

--------------------------- HISTO --------------------------

ALTER TABLE objectsclassifhisto RENAME TO objectsclassifhisto_old;
ALTER INDEX objectsclassifhisto_pkey RENAME TO objectsclassifhisto_pkey_old;

CREATE TABLE objectsclassifhisto (
    objid bigint NOT NULL,
    classif_date timestamp without time zone NOT NULL,
    classif_score double precision,
    classif_id integer NOT NULL,
    classif_who integer,
    classif_qual character(1) NOT NULL
) TABLESPACE home_indexes;

INSERT INTO objectsclassifhisto
SELECT mpg_obj.new_id,
       classif_date,
       classif_score,
       classif_id,
       classif_who,
       classif_qual
  FROM objectsclassifhisto_old
  JOIN objid_old_2_new mpg_obj ON mpg_obj.old_id = objid;

ALTER TABLE ONLY objectsclassifhisto ALTER COLUMN classif_date SET STATISTICS 10000;

ALTER TABLE objectsclassifhisto OWNER TO postgres;

ALTER TABLE ONLY objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_pkey PRIMARY KEY (objid, classif_date);

ALTER TABLE ONLY objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES taxonomy(id) ON DELETE CASCADE,
    ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES users(id),
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES obj_head(objid) ON DELETE CASCADE;

VACUUM VERBOSE objectsclassifhisto;

---------------------- PREDICTION ------------------

ALTER TABLE prediction RENAME TO prediction_old;
ALTER INDEX prediction_pkey RENAME TO prediction_pkey_old;
ALTER INDEX is_prediction_training RENAME TO is_prediction_training_old;

CREATE TABLE prediction (
    object_id bigint NOT NULL,
    training_id integer NOT NULL,
    classif_id integer NOT NULL,
    score double precision NOT NULL
) TABLESPACE home_indexes;

INSERT INTO prediction
SELECT mpg_obj.new_id,
       training_id,
       classif_id,
       score
  FROM prediction_old
  JOIN objid_old_2_new mpg_obj ON mpg_obj.old_id = object_id;

ALTER TABLE prediction OWNER TO postgres;

ALTER TABLE ONLY prediction
    ADD CONSTRAINT prediction_pkey PRIMARY KEY (object_id, classif_id);

ALTER TABLE ONLY prediction
    ADD CONSTRAINT prediction_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES taxonomy(id) ON DELETE CASCADE,
    ADD CONSTRAINT prediction_object_id_fkey FOREIGN KEY (object_id) REFERENCES obj_head(objid) ON DELETE CASCADE,
    ADD CONSTRAINT prediction_training_id_fkey FOREIGN KEY (training_id) REFERENCES training(training_id) ON DELETE CASCADE;

CREATE INDEX is_prediction_training ON prediction USING btree (training_id);

GRANT SELECT ON TABLE prediction TO readerole;

---------------------- PREDICTION HISTO ------------------

ALTER TABLE prediction_histo RENAME TO prediction_histo_old;
ALTER INDEX prediction_histo_pkey RENAME TO prediction_histo_pkey_old;
ALTER INDEX is_prediction_histo_object RENAME TO is_prediction_histo_object_old;

CREATE TABLE prediction_histo (
    object_id bigint NOT NULL,
    training_id integer NOT NULL,
    classif_id integer NOT NULL,
    score double precision NOT NULL
);

INSERT INTO prediction_histo
SELECT mpg_obj.new_id,
       training_id,
       classif_id,
       score
  FROM prediction_histo_old
  JOIN objid_old_2_new mpg_obj ON mpg_obj.old_id = object_id;

ALTER TABLE prediction_histo OWNER TO postgres;

ALTER TABLE ONLY prediction_histo
    ADD CONSTRAINT prediction_histo_pkey PRIMARY KEY (training_id, object_id, classif_id);

CREATE INDEX is_prediction_histo_object ON prediction_histo USING btree (object_id);

ALTER TABLE ONLY prediction_histo
    ADD CONSTRAINT prediction_histo_classif_id_fkey FOREIGN KEY (classif_id) REFERENCES taxonomy(id) ON DELETE CASCADE,
    ADD CONSTRAINT prediction_histo_object_id_fkey FOREIGN KEY (object_id) REFERENCES obj_head(objid) ON DELETE CASCADE,
    ADD CONSTRAINT prediction_histo_training_id_fkey FOREIGN KEY (training_id) REFERENCES training(training_id) ON DELETE CASCADE;

GRANT SELECT ON TABLE prediction_histo TO readerole;

---------------------- CNN FEATURES ------------------

ALTER TABLE obj_cnn_features_vector RENAME TO obj_cnn_features_vector_old;
ALTER INDEX obj_cnn_features_vector_pkey RENAME TO obj_cnn_features_vector_pkey_old;
ALTER INDEX obj_cnn_features_vector_hv_ivfflat_l2_5k_idx RENAME TO obj_cnn_features_vector_hv_ivfflat_l2_5k_idx_old;

CREATE TABLE obj_cnn_features_vector (
    objcnnid bigint NOT NULL,
    features vector(50)
);
ALTER TABLE ONLY obj_cnn_features_vector ALTER COLUMN features SET STORAGE EXTENDED;

INSERT INTO obj_cnn_features_vector
SELECT mpg_obj.new_id,
       features
  FROM obj_cnn_features_vector_old
  JOIN objid_old_2_new mpg_obj ON mpg_obj.old_id = objcnnid;

ALTER TABLE obj_cnn_features_vector OWNER TO postgres;

ALTER TABLE ONLY obj_cnn_features_vector
    ADD CONSTRAINT obj_cnn_features_vector_pkey PRIMARY KEY (objcnnid);

CREATE INDEX obj_cnn_features_vector_hv_ivfflat_l2_5k_idx ON obj_cnn_features_vector USING ivfflat (((features)::halfvec(50)) halfvec_l2_ops) WITH (lists='5000');

ALTER TABLE ONLY obj_cnn_features_vector
    ADD CONSTRAINT obj_cnn_features_vector_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES obj_head(objid) ON DELETE CASCADE;

GRANT SELECT ON TABLE obj_cnn_features_vector TO readerole;
GRANT SELECT ON TABLE obj_cnn_features_vector TO zoo;


-- Recreate objects view
CREATE VIEW objects AS
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
FROM obj_head obh
         JOIN acquisitions acq ON obh.acquisid = acq.acquisid
         JOIN samples sam ON acq.acq_sample_id = sam.sampleid
         LEFT JOIN obj_field ofi ON obh.objid = ofi.objfid;
