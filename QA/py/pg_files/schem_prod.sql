
--
-- PostgreSQL database dump
--

-- Dumped from database version 11.6 (Ubuntu 11.6-1.pgdg18.04+1)
-- Dumped by pg_dump version 12.2 (Ubuntu 12.2-2.pgdg18.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'LATIN1';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_buffercache; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_buffercache WITH SCHEMA public;


--
-- Name: EXTENSION pg_buffercache; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_buffercache IS 'examine the shared buffer cache';


--
-- Name: tsm_system_time; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS tsm_system_time WITH SCHEMA public;


--
-- Name: EXTENSION tsm_system_time; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION tsm_system_time IS 'TABLESAMPLE method which accepts time in milliseconds as a limit';


SET default_tablespace = '';

--
-- Name: acquisitions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.acquisitions (
    acquisid bigint NOT NULL,
    projid integer,
    orig_id character varying(255),
    instrument character varying(255),
    t01 character varying(250),
    t02 character varying(250),
    t03 character varying(250),
    t04 character varying(250),
    t05 character varying(250),
    t06 character varying(250),
    t07 character varying(250),
    t08 character varying(250),
    t09 character varying(250),
    t10 character varying(250),
    t11 character varying(250),
    t12 character varying(250),
    t13 character varying(250),
    t14 character varying(250),
    t15 character varying(250),
    t16 character varying(250),
    t17 character varying(250),
    t18 character varying(250),
    t19 character varying(250),
    t20 character varying(250),
    t21 character varying(250),
    t22 character varying(250),
    t23 character varying(250),
    t24 character varying(250),
    t25 character varying(250),
    t26 character varying(250),
    t27 character varying(250),
    t28 character varying(250),
    t29 character varying(250),
    t30 character varying(250)
);


ALTER TABLE public.acquisitions OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: countrylist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.countrylist (
    countryname character varying(50) NOT NULL
);


ALTER TABLE public.countrylist OWNER TO postgres;

--
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.images (
    imgid bigint NOT NULL,
    objid bigint,
    imgrank integer,
    file_name character varying(255),
    orig_file_name character varying(255),
    width integer,
    height integer,
    thumb_file_name character varying(255),
    thumb_width integer,
    thumb_height integer
);


ALTER TABLE public.images OWNER TO postgres;

--
-- Name: obj_cnn_features; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.obj_cnn_features (
    objcnnid bigint NOT NULL,
    cnn01 real,
    cnn02 real,
    cnn03 real,
    cnn04 real,
    cnn05 real,
    cnn06 real,
    cnn07 real,
    cnn08 real,
    cnn09 real,
    cnn10 real,
    cnn11 real,
    cnn12 real,
    cnn13 real,
    cnn14 real,
    cnn15 real,
    cnn16 real,
    cnn17 real,
    cnn18 real,
    cnn19 real,
    cnn20 real,
    cnn21 real,
    cnn22 real,
    cnn23 real,
    cnn24 real,
    cnn25 real,
    cnn26 real,
    cnn27 real,
    cnn28 real,
    cnn29 real,
    cnn30 real,
    cnn31 real,
    cnn32 real,
    cnn33 real,
    cnn34 real,
    cnn35 real,
    cnn36 real,
    cnn37 real,
    cnn38 real,
    cnn39 real,
    cnn40 real,
    cnn41 real,
    cnn42 real,
    cnn43 real,
    cnn44 real,
    cnn45 real,
    cnn46 real,
    cnn47 real,
    cnn48 real,
    cnn49 real,
    cnn50 real
);


ALTER TABLE public.obj_cnn_features OWNER TO postgres;

--
-- Name: obj_field; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.obj_field (
    objfid bigint NOT NULL,
    orig_id character varying(255),
    object_link character varying(255),
    n01 double precision,
    n02 double precision,
    n03 double precision,
    n04 double precision,
    n05 double precision,
    n06 double precision,
    n07 double precision,
    n08 double precision,
    n09 double precision,
    n10 double precision,
    n11 double precision,
    n12 double precision,
    n13 double precision,
    n14 double precision,
    n15 double precision,
    n16 double precision,
    n17 double precision,
    n18 double precision,
    n19 double precision,
    n20 double precision,
    n21 double precision,
    n22 double precision,
    n23 double precision,
    n24 double precision,
    n25 double precision,
    n26 double precision,
    n27 double precision,
    n28 double precision,
    n29 double precision,
    n30 double precision,
    n31 double precision,
    n32 double precision,
    n33 double precision,
    n34 double precision,
    n35 double precision,
    n36 double precision,
    n37 double precision,
    n38 double precision,
    n39 double precision,
    n40 double precision,
    n41 double precision,
    n42 double precision,
    n43 double precision,
    n44 double precision,
    n45 double precision,
    n46 double precision,
    n47 double precision,
    n48 double precision,
    n49 double precision,
    n50 double precision,
    n51 double precision,
    n52 double precision,
    n53 double precision,
    n54 double precision,
    n55 double precision,
    n56 double precision,
    n57 double precision,
    n58 double precision,
    n59 double precision,
    n60 double precision,
    n61 double precision,
    n62 double precision,
    n63 double precision,
    n64 double precision,
    n65 double precision,
    n66 double precision,
    n67 double precision,
    n68 double precision,
    n69 double precision,
    n70 double precision,
    n71 double precision,
    n72 double precision,
    n73 double precision,
    n74 double precision,
    n75 double precision,
    n76 double precision,
    n77 double precision,
    n78 double precision,
    n79 double precision,
    n80 double precision,
    n81 double precision,
    n82 double precision,
    n83 double precision,
    n84 double precision,
    n85 double precision,
    n86 double precision,
    n87 double precision,
    n88 double precision,
    n89 double precision,
    n90 double precision,
    n91 double precision,
    n92 double precision,
    n93 double precision,
    n94 double precision,
    n95 double precision,
    n96 double precision,
    n97 double precision,
    n98 double precision,
    n99 double precision,
    n100 double precision,
    n101 double precision,
    n102 double precision,
    n103 double precision,
    n104 double precision,
    n105 double precision,
    n106 double precision,
    n107 double precision,
    n108 double precision,
    n109 double precision,
    n110 double precision,
    n111 double precision,
    n112 double precision,
    n113 double precision,
    n114 double precision,
    n115 double precision,
    n116 double precision,
    n117 double precision,
    n118 double precision,
    n119 double precision,
    n120 double precision,
    n121 double precision,
    n122 double precision,
    n123 double precision,
    n124 double precision,
    n125 double precision,
    n126 double precision,
    n127 double precision,
    n128 double precision,
    n129 double precision,
    n130 double precision,
    n131 double precision,
    n132 double precision,
    n133 double precision,
    n134 double precision,
    n135 double precision,
    n136 double precision,
    n137 double precision,
    n138 double precision,
    n139 double precision,
    n140 double precision,
    n141 double precision,
    n142 double precision,
    n143 double precision,
    n144 double precision,
    n145 double precision,
    n146 double precision,
    n147 double precision,
    n148 double precision,
    n149 double precision,
    n150 double precision,
    n151 double precision,
    n152 double precision,
    n153 double precision,
    n154 double precision,
    n155 double precision,
    n156 double precision,
    n157 double precision,
    n158 double precision,
    n159 double precision,
    n160 double precision,
    n161 double precision,
    n162 double precision,
    n163 double precision,
    n164 double precision,
    n165 double precision,
    n166 double precision,
    n167 double precision,
    n168 double precision,
    n169 double precision,
    n170 double precision,
    n171 double precision,
    n172 double precision,
    n173 double precision,
    n174 double precision,
    n175 double precision,
    n176 double precision,
    n177 double precision,
    n178 double precision,
    n179 double precision,
    n180 double precision,
    n181 double precision,
    n182 double precision,
    n183 double precision,
    n184 double precision,
    n185 double precision,
    n186 double precision,
    n187 double precision,
    n188 double precision,
    n189 double precision,
    n190 double precision,
    n191 double precision,
    n192 double precision,
    n193 double precision,
    n194 double precision,
    n195 double precision,
    n196 double precision,
    n197 double precision,
    n198 double precision,
    n199 double precision,
    n200 double precision,
    n201 double precision,
    n202 double precision,
    n203 double precision,
    n204 double precision,
    n205 double precision,
    n206 double precision,
    n207 double precision,
    n208 double precision,
    n209 double precision,
    n210 double precision,
    n211 double precision,
    n212 double precision,
    n213 double precision,
    n214 double precision,
    n215 double precision,
    n216 double precision,
    n217 double precision,
    n218 double precision,
    n219 double precision,
    n220 double precision,
    n221 double precision,
    n222 double precision,
    n223 double precision,
    n224 double precision,
    n225 double precision,
    n226 double precision,
    n227 double precision,
    n228 double precision,
    n229 double precision,
    n230 double precision,
    n231 double precision,
    n232 double precision,
    n233 double precision,
    n234 double precision,
    n235 double precision,
    n236 double precision,
    n237 double precision,
    n238 double precision,
    n239 double precision,
    n240 double precision,
    n241 double precision,
    n242 double precision,
    n243 double precision,
    n244 double precision,
    n245 double precision,
    n246 double precision,
    n247 double precision,
    n248 double precision,
    n249 double precision,
    n250 double precision,
    n251 double precision,
    n252 double precision,
    n253 double precision,
    n254 double precision,
    n255 double precision,
    n256 double precision,
    n257 double precision,
    n258 double precision,
    n259 double precision,
    n260 double precision,
    n261 double precision,
    n262 double precision,
    n263 double precision,
    n264 double precision,
    n265 double precision,
    n266 double precision,
    n267 double precision,
    n268 double precision,
    n269 double precision,
    n270 double precision,
    n271 double precision,
    n272 double precision,
    n273 double precision,
    n274 double precision,
    n275 double precision,
    n276 double precision,
    n277 double precision,
    n278 double precision,
    n279 double precision,
    n280 double precision,
    n281 double precision,
    n282 double precision,
    n283 double precision,
    n284 double precision,
    n285 double precision,
    n286 double precision,
    n287 double precision,
    n288 double precision,
    n289 double precision,
    n290 double precision,
    n291 double precision,
    n292 double precision,
    n293 double precision,
    n294 double precision,
    n295 double precision,
    n296 double precision,
    n297 double precision,
    n298 double precision,
    n299 double precision,
    n300 double precision,
    n301 double precision,
    n302 double precision,
    n303 double precision,
    n304 double precision,
    n305 double precision,
    n306 double precision,
    n307 double precision,
    n308 double precision,
    n309 double precision,
    n310 double precision,
    n311 double precision,
    n312 double precision,
    n313 double precision,
    n314 double precision,
    n315 double precision,
    n316 double precision,
    n317 double precision,
    n318 double precision,
    n319 double precision,
    n320 double precision,
    n321 double precision,
    n322 double precision,
    n323 double precision,
    n324 double precision,
    n325 double precision,
    n326 double precision,
    n327 double precision,
    n328 double precision,
    n329 double precision,
    n330 double precision,
    n331 double precision,
    n332 double precision,
    n333 double precision,
    n334 double precision,
    n335 double precision,
    n336 double precision,
    n337 double precision,
    n338 double precision,
    n339 double precision,
    n340 double precision,
    n341 double precision,
    n342 double precision,
    n343 double precision,
    n344 double precision,
    n345 double precision,
    n346 double precision,
    n347 double precision,
    n348 double precision,
    n349 double precision,
    n350 double precision,
    n351 double precision,
    n352 double precision,
    n353 double precision,
    n354 double precision,
    n355 double precision,
    n356 double precision,
    n357 double precision,
    n358 double precision,
    n359 double precision,
    n360 double precision,
    n361 double precision,
    n362 double precision,
    n363 double precision,
    n364 double precision,
    n365 double precision,
    n366 double precision,
    n367 double precision,
    n368 double precision,
    n369 double precision,
    n370 double precision,
    n371 double precision,
    n372 double precision,
    n373 double precision,
    n374 double precision,
    n375 double precision,
    n376 double precision,
    n377 double precision,
    n378 double precision,
    n379 double precision,
    n380 double precision,
    n381 double precision,
    n382 double precision,
    n383 double precision,
    n384 double precision,
    n385 double precision,
    n386 double precision,
    n387 double precision,
    n388 double precision,
    n389 double precision,
    n390 double precision,
    n391 double precision,
    n392 double precision,
    n393 double precision,
    n394 double precision,
    n395 double precision,
    n396 double precision,
    n397 double precision,
    n398 double precision,
    n399 double precision,
    n400 double precision,
    n401 double precision,
    n402 double precision,
    n403 double precision,
    n404 double precision,
    n405 double precision,
    n406 double precision,
    n407 double precision,
    n408 double precision,
    n409 double precision,
    n410 double precision,
    n411 double precision,
    n412 double precision,
    n413 double precision,
    n414 double precision,
    n415 double precision,
    n416 double precision,
    n417 double precision,
    n418 double precision,
    n419 double precision,
    n420 double precision,
    n421 double precision,
    n422 double precision,
    n423 double precision,
    n424 double precision,
    n425 double precision,
    n426 double precision,
    n427 double precision,
    n428 double precision,
    n429 double precision,
    n430 double precision,
    n431 double precision,
    n432 double precision,
    n433 double precision,
    n434 double precision,
    n435 double precision,
    n436 double precision,
    n437 double precision,
    n438 double precision,
    n439 double precision,
    n440 double precision,
    n441 double precision,
    n442 double precision,
    n443 double precision,
    n444 double precision,
    n445 double precision,
    n446 double precision,
    n447 double precision,
    n448 double precision,
    n449 double precision,
    n450 double precision,
    n451 double precision,
    n452 double precision,
    n453 double precision,
    n454 double precision,
    n455 double precision,
    n456 double precision,
    n457 double precision,
    n458 double precision,
    n459 double precision,
    n460 double precision,
    n461 double precision,
    n462 double precision,
    n463 double precision,
    n464 double precision,
    n465 double precision,
    n466 double precision,
    n467 double precision,
    n468 double precision,
    n469 double precision,
    n470 double precision,
    n471 double precision,
    n472 double precision,
    n473 double precision,
    n474 double precision,
    n475 double precision,
    n476 double precision,
    n477 double precision,
    n478 double precision,
    n479 double precision,
    n480 double precision,
    n481 double precision,
    n482 double precision,
    n483 double precision,
    n484 double precision,
    n485 double precision,
    n486 double precision,
    n487 double precision,
    n488 double precision,
    n489 double precision,
    n490 double precision,
    n491 double precision,
    n492 double precision,
    n493 double precision,
    n494 double precision,
    n495 double precision,
    n496 double precision,
    n497 double precision,
    n498 double precision,
    n499 double precision,
    n500 double precision,
    t01 character varying(250),
    t02 character varying(250),
    t03 character varying(250),
    t04 character varying(250),
    t05 character varying(250),
    t06 character varying(250),
    t07 character varying(250),
    t08 character varying(250),
    t09 character varying(250),
    t10 character varying(250),
    t11 character varying(250),
    t12 character varying(250),
    t13 character varying(250),
    t14 character varying(250),
    t15 character varying(250),
    t16 character varying(250),
    t17 character varying(250),
    t18 character varying(250),
    t19 character varying(250),
    t20 character varying(250)
)
WITH (autovacuum_vacuum_scale_factor='0.01');


ALTER TABLE public.obj_field OWNER TO postgres;

--
-- Name: obj_head; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.obj_head (
    objid bigint NOT NULL,
    projid integer NOT NULL,
    latitude double precision,
    longitude double precision,
    objdate date,
    objtime time without time zone,
    depth_min double precision,
    depth_max double precision,
    classif_id integer,
    classif_qual character(1),
    classif_who integer,
    classif_when timestamp without time zone,
    classif_auto_id integer,
    classif_auto_score double precision,
    classif_auto_when timestamp without time zone,
    classif_crossvalidation_id integer,
    img0id bigint,
    imgcount integer,
    complement_info character varying,
    similarity double precision,
    sunpos character(1),
    random_value integer,
    sampleid integer,
    acquisid integer,
    processid integer
)
WITH (autovacuum_vacuum_scale_factor='0.01');


ALTER TABLE public.obj_head OWNER TO postgres;

--
-- Name: objects; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.objects AS
 SELECT oh.objid,
    oh.projid,
    oh.latitude,
    oh.longitude,
    oh.objdate,
    oh.objtime,
    oh.depth_min,
    oh.depth_max,
    oh.classif_id,
    oh.classif_qual,
    oh.classif_who,
    oh.classif_when,
    oh.classif_auto_id,
    oh.classif_auto_score,
    oh.classif_auto_when,
    oh.classif_crossvalidation_id,
    oh.img0id,
    oh.imgcount,
    oh.complement_info,
    oh.similarity,
    oh.sunpos,
    oh.random_value,
    oh.sampleid,
    oh.acquisid,
    oh.processid,
    ofi.objfid,
    ofi.orig_id,
    ofi.object_link,
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
   FROM (public.obj_head oh
     LEFT JOIN public.obj_field ofi ON ((oh.objid = ofi.objfid)));


ALTER TABLE public.objects OWNER TO postgres;

--
-- Name: objectsclassifhisto; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.objectsclassifhisto (
    objid bigint NOT NULL,
    classif_date timestamp without time zone NOT NULL,
    classif_type character(1),
    classif_id integer,
    classif_qual character(1),
    classif_who integer,
    classif_score double precision
);


ALTER TABLE public.objectsclassifhisto OWNER TO postgres;

--
-- Name: part_ctd; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_ctd (
    psampleid integer NOT NULL,
    lineno integer NOT NULL,
    depth double precision,
    datetime timestamp without time zone,
    chloro_fluo double precision,
    conductivity double precision,
    cpar double precision,
    depth_salt_water double precision,
    fcdom_factory double precision,
    in_situ_density_anomaly double precision,
    neutral_density double precision,
    nitrate double precision,
    oxygen_mass double precision,
    oxygen_vol double precision,
    par double precision,
    part_backscattering_coef_470_nm double precision,
    pot_temperature double precision,
    potential_density_anomaly double precision,
    potential_temperature double precision,
    practical_salinity double precision,
    practical_salinity__from_conductivity double precision,
    qc_flag integer,
    sound_speed_c double precision,
    spar double precision,
    temperature double precision,
    extrames01 double precision,
    extrames02 double precision,
    extrames03 double precision,
    extrames04 double precision,
    extrames05 double precision,
    extrames06 double precision,
    extrames07 double precision,
    extrames08 double precision,
    extrames09 double precision,
    extrames10 double precision,
    extrames11 double precision,
    extrames12 double precision,
    extrames13 double precision,
    extrames14 double precision,
    extrames15 double precision,
    extrames16 double precision,
    extrames17 double precision,
    extrames18 double precision,
    extrames19 double precision,
    extrames20 double precision
);


ALTER TABLE public.part_ctd OWNER TO postgres;

--
-- Name: part_histocat; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_histocat (
    psampleid integer NOT NULL,
    classif_id integer NOT NULL,
    lineno integer NOT NULL,
    depth double precision,
    datetime timestamp without time zone,
    watervolume double precision,
    nbr double precision,
    avgesd double precision,
    totalbiovolume double precision
);


ALTER TABLE public.part_histocat OWNER TO postgres;

--
-- Name: part_histocat_lst; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_histocat_lst (
    psampleid integer NOT NULL,
    classif_id integer NOT NULL
);


ALTER TABLE public.part_histocat_lst OWNER TO postgres;

--
-- Name: part_histopart_det; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_histopart_det (
    psampleid integer NOT NULL,
    lineno integer NOT NULL,
    depth double precision,
    datetime timestamp without time zone,
    watervolume double precision,
    class01 integer,
    class02 integer,
    class03 integer,
    class04 integer,
    class05 integer,
    class06 integer,
    class07 integer,
    class08 integer,
    class09 integer,
    class10 integer,
    class11 integer,
    class12 integer,
    class13 integer,
    class14 integer,
    class15 integer,
    class16 integer,
    class17 integer,
    class18 integer,
    class19 integer,
    class20 integer,
    class21 integer,
    class22 integer,
    class23 integer,
    class24 integer,
    class25 integer,
    class26 integer,
    class27 integer,
    class28 integer,
    class29 integer,
    class30 integer,
    class31 integer,
    class32 integer,
    class33 integer,
    class34 integer,
    class35 integer,
    class36 integer,
    class37 integer,
    class38 integer,
    class39 integer,
    class40 integer,
    class41 integer,
    class42 integer,
    class43 integer,
    class44 integer,
    class45 integer,
    biovol01 double precision,
    biovol02 double precision,
    biovol03 double precision,
    biovol04 double precision,
    biovol05 double precision,
    biovol06 double precision,
    biovol07 double precision,
    biovol08 double precision,
    biovol09 double precision,
    biovol10 double precision,
    biovol11 double precision,
    biovol12 double precision,
    biovol13 double precision,
    biovol14 double precision,
    biovol15 double precision,
    biovol16 double precision,
    biovol17 double precision,
    biovol18 double precision,
    biovol19 double precision,
    biovol20 double precision,
    biovol21 double precision,
    biovol22 double precision,
    biovol23 double precision,
    biovol24 double precision,
    biovol25 double precision,
    biovol26 double precision,
    biovol27 double precision,
    biovol28 double precision,
    biovol29 double precision,
    biovol30 double precision,
    biovol31 double precision,
    biovol32 double precision,
    biovol33 double precision,
    biovol34 double precision,
    biovol35 double precision,
    biovol36 double precision,
    biovol37 double precision,
    biovol38 double precision,
    biovol39 double precision,
    biovol40 double precision,
    biovol41 double precision,
    biovol42 double precision,
    biovol43 double precision,
    biovol44 double precision,
    biovol45 double precision
);


ALTER TABLE public.part_histopart_det OWNER TO postgres;

--
-- Name: part_histopart_reduit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_histopart_reduit (
    psampleid integer NOT NULL,
    lineno integer NOT NULL,
    depth double precision,
    datetime timestamp without time zone,
    watervolume double precision,
    class01 integer,
    class02 integer,
    class03 integer,
    class04 integer,
    class05 integer,
    class06 integer,
    class07 integer,
    class08 integer,
    class09 integer,
    class10 integer,
    class11 integer,
    class12 integer,
    class13 integer,
    class14 integer,
    class15 integer,
    biovol01 double precision,
    biovol02 double precision,
    biovol03 double precision,
    biovol04 double precision,
    biovol05 double precision,
    biovol06 double precision,
    biovol07 double precision,
    biovol08 double precision,
    biovol09 double precision,
    biovol10 double precision,
    biovol11 double precision,
    biovol12 double precision,
    biovol13 double precision,
    biovol14 double precision,
    biovol15 double precision
);


ALTER TABLE public.part_histopart_reduit OWNER TO postgres;

--
-- Name: part_projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_projects (
    pprojid integer NOT NULL,
    ptitle character varying(250) NOT NULL,
    rawfolder character varying(250) NOT NULL,
    ownerid integer,
    projid integer,
    instrumtype character varying(50),
    op_name character varying(100),
    op_email character varying(100),
    cs_name character varying(100),
    cs_email character varying(100),
    do_name character varying(100),
    do_email character varying(100),
    prj_info character varying(1000),
    prj_acronym character varying(100),
    cruise character varying(100),
    ship character varying(100),
    default_instrumsn character varying(50),
    default_depthoffset double precision,
    oldestsampledate timestamp without time zone,
    public_partexport_deferral_month integer,
    public_visibility_deferral_month integer,
    public_zooexport_deferral_month integer
);


ALTER TABLE public.part_projects OWNER TO postgres;

--
-- Name: part_projects_pprojid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.part_projects_pprojid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.part_projects_pprojid_seq OWNER TO postgres;

--
-- Name: part_projects_pprojid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.part_projects_pprojid_seq OWNED BY public.part_projects.pprojid;


--
-- Name: part_samples; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.part_samples (
    psampleid integer NOT NULL,
    pprojid integer,
    profileid character varying(250) NOT NULL,
    filename character varying(250) NOT NULL,
    sampleid integer,
    latitude double precision,
    longitude double precision,
    organizedbydeepth boolean,
    histobrutavailable boolean,
    qualitytaxo character varying(20),
    qualitypart character varying(20),
    daterecalculhistotaxo timestamp without time zone,
    winddir integer,
    winspeed integer,
    seastate integer,
    nebuloussness integer,
    comment character varying(1000),
    stationid character varying(100),
    firstimage integer,
    lastimg bigint,
    lastimgused bigint,
    bottomdepth integer,
    yoyo boolean,
    sampledate timestamp without time zone,
    op_sample_name character varying(100),
    op_sample_email character varying(100),
    ctd_desc character varying(1000),
    ctd_origfilename character varying(250),
    ctd_import_name character varying(100),
    ctd_import_email character varying(100),
    ctd_import_datetime timestamp without time zone,
    ctd_status character varying(50),
    instrumsn character varying(50),
    acq_aa double precision,
    acq_exp double precision,
    acq_volimage double precision,
    acq_depthoffset double precision,
    acq_pixel double precision,
    acq_shutterspeed integer,
    acq_smzoo integer,
    acq_exposure integer,
    acq_gain integer,
    acq_filedescription character varying(200),
    acq_eraseborder integer,
    acq_tasktype integer,
    acq_threshold integer,
    acq_choice integer,
    acq_disktype integer,
    acq_smbase integer,
    acq_ratio integer,
    acq_descent_filter boolean,
    acq_presure_gain double precision,
    acq_xsize integer,
    acq_ysize integer,
    acq_barcode character varying(50),
    proc_datetime timestamp without time zone,
    proc_gamma double precision,
    proc_soft character varying(250),
    lisst_zscat_filename character varying(200),
    lisst_kernel character varying(200),
    lisst_year integer,
    txt_data01 character varying(200),
    txt_data02 character varying(200),
    txt_data03 character varying(200),
    txt_data04 character varying(200),
    txt_data05 character varying(200),
    txt_data06 character varying(200),
    txt_data07 character varying(200),
    txt_data08 character varying(200),
    txt_data09 character varying(200),
    txt_data10 character varying(200),
    imp_descent_filtered_row integer,
    imp_removed_empty_slice integer,
    proc_process_ratio integer
);


ALTER TABLE public.part_samples OWNER TO postgres;

--
-- Name: part_samples_psampleid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.part_samples_psampleid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.part_samples_psampleid_seq OWNER TO postgres;

--
-- Name: part_samples_psampleid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.part_samples_psampleid_seq OWNED BY public.part_samples.psampleid;


--
-- Name: persistantdatatable; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.persistantdatatable (
    id integer NOT NULL,
    lastserverversioncheck_datetime timestamp(0) without time zone
);


ALTER TABLE public.persistantdatatable OWNER TO postgres;

--
-- Name: persistantdatatable_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.persistantdatatable_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.persistantdatatable_id_seq OWNER TO postgres;

--
-- Name: persistantdatatable_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.persistantdatatable_id_seq OWNED BY public.persistantdatatable.id;


--
-- Name: process; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.process (
    processid bigint NOT NULL,
    projid integer,
    orig_id character varying(255),
    t01 character varying(250),
    t02 character varying(250),
    t03 character varying(250),
    t04 character varying(250),
    t05 character varying(250),
    t06 character varying(250),
    t07 character varying(250),
    t08 character varying(250),
    t09 character varying(250),
    t10 character varying(250),
    t11 character varying(250),
    t12 character varying(250),
    t13 character varying(250),
    t14 character varying(250),
    t15 character varying(250),
    t16 character varying(250),
    t17 character varying(250),
    t18 character varying(250),
    t19 character varying(250),
    t20 character varying(250),
    t21 character varying(250),
    t22 character varying(250),
    t23 character varying(250),
    t24 character varying(250),
    t25 character varying(250),
    t26 character varying(250),
    t27 character varying(250),
    t28 character varying(250),
    t29 character varying(250),
    t30 character varying(250)
);


ALTER TABLE public.process OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    projid integer NOT NULL,
    title character varying(255) NOT NULL,
    visible boolean,
    status character varying(40),
    mappingobj character varying,
    mappingsample character varying,
    mappingacq character varying,
    mappingprocess character varying,
    objcount double precision,
    pctvalidated double precision,
    pctclassified double precision,
    classifsettings character varying,
    initclassiflist character varying,
    classiffieldlist character varying,
    popoverfieldlist character varying,
    comments character varying,
    projtype character varying(50),
    fileloaded character varying,
    cnn_network_id character varying(50),
    rf_models_used character varying
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: projects_taxo_stat; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects_taxo_stat (
    projid integer NOT NULL,
    id integer NOT NULL,
    nbr integer,
    nbr_v integer,
    nbr_d integer,
    nbr_p integer
);


ALTER TABLE public.projects_taxo_stat OWNER TO postgres;

--
-- Name: projectspriv; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projectspriv (
    id integer NOT NULL,
    projid integer NOT NULL,
    member integer,
    privilege character varying(255) NOT NULL
);


ALTER TABLE public.projectspriv OWNER TO postgres;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(80) NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.roles_id_seq OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: samples; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.samples (
    sampleid bigint NOT NULL,
    projid integer,
    orig_id character varying(255),
    latitude double precision,
    longitude double precision,
    dataportal_descriptor character varying(8000),
    t01 character varying(250),
    t02 character varying(250),
    t03 character varying(250),
    t04 character varying(250),
    t05 character varying(250),
    t06 character varying(250),
    t07 character varying(250),
    t08 character varying(250),
    t09 character varying(250),
    t10 character varying(250),
    t11 character varying(250),
    t12 character varying(250),
    t13 character varying(250),
    t14 character varying(250),
    t15 character varying(250),
    t16 character varying(250),
    t17 character varying(250),
    t18 character varying(250),
    t19 character varying(250),
    t20 character varying(250),
    t21 character varying(250),
    t22 character varying(250),
    t23 character varying(250),
    t24 character varying(250),
    t25 character varying(250),
    t26 character varying(250),
    t27 character varying(250),
    t28 character varying(250),
    t29 character varying(250),
    t30 character varying(250)
);


ALTER TABLE public.samples OWNER TO postgres;

--
-- Name: seq_acquisitions; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_acquisitions
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_acquisitions OWNER TO postgres;

--
-- Name: seq_images; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_images
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_images OWNER TO postgres;

--
-- Name: seq_objects; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_objects
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_objects OWNER TO postgres;

--
-- Name: seq_process; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_process
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_process OWNER TO postgres;

--
-- Name: seq_projects; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_projects
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_projects OWNER TO postgres;

--
-- Name: seq_projectspriv; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_projectspriv
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_projectspriv OWNER TO postgres;

--
-- Name: seq_samples; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_samples
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_samples OWNER TO postgres;

--
-- Name: seq_taxonomy; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_taxonomy
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_taxonomy OWNER TO postgres;

--
-- Name: seq_temp_tasks; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_temp_tasks
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_temp_tasks OWNER TO postgres;

--
-- Name: seq_users; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seq_users
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_users OWNER TO postgres;

--
-- Name: taxonomy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.taxonomy (
    id integer NOT NULL,
    parent_id integer,
    name character varying(100) NOT NULL,
    id_source character varying(20),
    nbrobj integer,
    nbrobjcum integer,
    creation_datetime timestamp(0) without time zone,
    creator_email character varying(255),
    display_name character varying(200),
    id_instance integer,
    lastupdate_datetime timestamp(0) without time zone,
    rename_to integer,
    source_desc character varying(1000),
    source_url character varying(200),
    taxostatus character(1) DEFAULT 'A'::bpchar NOT NULL,
    taxotype character(1) DEFAULT 'P'::bpchar NOT NULL
);

ALTER TABLE public.taxonomy OWNER TO postgres;

--
-- Name: temp_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.temp_tasks (
    id integer NOT NULL,
    owner_id integer,
    taskclass character varying(80),
    taskstate character varying(80),
    taskstep integer,
    progresspct integer,
    progressmsg character varying,
    inputparam character varying,
    creationdate timestamp without time zone,
    lastupdate timestamp without time zone,
    questiondata character varying,
    answerdata character varying
);


ALTER TABLE public.temp_tasks OWNER TO postgres;

--
-- Name: temp_taxo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.temp_taxo (
    idtaxo character varying(20) NOT NULL,
    idparent character varying(20),
    name character varying(100),
    status character(1),
    typetaxo character varying(20),
    idfinal integer
);


ALTER TABLE public.temp_taxo OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password character varying(255),
    name character varying(255) NOT NULL,
    organisation character varying(255),
    active boolean,
    preferences character varying(40000),
    country character varying(50),
    usercreationdate timestamp without time zone,
    usercreationreason character varying(1000)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users_roles (
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.users_roles OWNER TO postgres;

--
-- Name: part_projects pprojid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_projects ALTER COLUMN pprojid SET DEFAULT nextval('public.part_projects_pprojid_seq'::regclass);


--
-- Name: part_samples psampleid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_samples ALTER COLUMN psampleid SET DEFAULT nextval('public.part_samples_psampleid_seq'::regclass);


--
-- Name: persistantdatatable id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.persistantdatatable ALTER COLUMN id SET DEFAULT nextval('public.persistantdatatable_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: acquisitions acquisitions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.acquisitions
    ADD CONSTRAINT acquisitions_pkey PRIMARY KEY (acquisid);


--
-- Name: countrylist countrylist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.countrylist
    ADD CONSTRAINT countrylist_pkey PRIMARY KEY (countryname);


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (imgid);


--
-- Name: obj_cnn_features obj_cnn_features_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_cnn_features
    ADD CONSTRAINT obj_cnn_features_pkey PRIMARY KEY (objcnnid);


--
-- Name: obj_field obj_field_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_field
    ADD CONSTRAINT obj_field_pkey PRIMARY KEY (objfid);


--
-- Name: obj_head obj_head_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_pkey PRIMARY KEY (objid);


--
-- Name: objectsclassifhisto objectsclassifhisto_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_pkey PRIMARY KEY (objid, classif_date);


--
-- Name: part_ctd part_ctd_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_ctd
    ADD CONSTRAINT part_ctd_pkey PRIMARY KEY (psampleid, lineno);


--
-- Name: part_histocat_lst part_histocat_lst_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histocat_lst
    ADD CONSTRAINT part_histocat_lst_pkey PRIMARY KEY (psampleid, classif_id);


--
-- Name: part_histocat part_histocat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histocat
    ADD CONSTRAINT part_histocat_pkey PRIMARY KEY (psampleid, classif_id, lineno);


--
-- Name: part_histopart_det part_histopart_det_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histopart_det
    ADD CONSTRAINT part_histopart_det_pkey PRIMARY KEY (psampleid, lineno);


--
-- Name: part_histopart_reduit part_histopart_reduit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histopart_reduit
    ADD CONSTRAINT part_histopart_reduit_pkey PRIMARY KEY (psampleid, lineno);


--
-- Name: part_projects part_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_projects
    ADD CONSTRAINT part_projects_pkey PRIMARY KEY (pprojid);


--
-- Name: part_samples part_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_samples
    ADD CONSTRAINT part_samples_pkey PRIMARY KEY (psampleid);


--
-- Name: persistantdatatable persistantdatatable_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.persistantdatatable
    ADD CONSTRAINT persistantdatatable_pkey PRIMARY KEY (id);


--
-- Name: process process_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.process
    ADD CONSTRAINT process_pkey PRIMARY KEY (processid);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (projid);


--
-- Name: projects_taxo_stat projects_taxo_stat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects_taxo_stat
    ADD CONSTRAINT projects_taxo_stat_pkey PRIMARY KEY (projid, id);


--
-- Name: projectspriv projectspriv_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projectspriv
    ADD CONSTRAINT projectspriv_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: samples samples_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_pkey PRIMARY KEY (sampleid);


--
-- Name: taxonomy taxonomy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taxonomy
    ADD CONSTRAINT taxonomy_pkey PRIMARY KEY (id);


--
-- Name: temp_tasks temp_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_tasks
    ADD CONSTRAINT temp_tasks_pkey PRIMARY KEY (id);


--
-- Name: temp_taxo temp_taxo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_taxo
    ADD CONSTRAINT temp_taxo_pkey PRIMARY KEY (idtaxo);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users_roles users_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users_roles
    ADD CONSTRAINT users_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: IS_AcquisitionsProject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_AcquisitionsProject" ON public.acquisitions USING btree (projid);


--
-- Name: IS_ImagesObjects; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_ImagesObjects" ON public.images USING btree (objid);


--
-- Name: IS_ProcessProject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_ProcessProject" ON public.process USING btree (projid);


--
-- Name: IS_ProjectsPriv; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "IS_ProjectsPriv" ON public.projectspriv USING btree (projid, member);


--
-- Name: IS_SamplesProject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_SamplesProject" ON public.samples USING btree (projid);


--
-- Name: IS_TaxonomyNameLow; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_TaxonomyNameLow" ON public.taxonomy USING btree (lower((name)::text));


--
-- Name: IS_TaxonomyParent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_TaxonomyParent" ON public.taxonomy USING btree (parent_id);


--
-- Name: IS_TaxonomySource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_TaxonomySource" ON public.taxonomy USING btree (id_source);


--
-- Name: IS_TempTaxoIdFinal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_TempTaxoIdFinal" ON public.temp_taxo USING btree (idfinal);


--
-- Name: IS_TempTaxoParent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IS_TempTaxoParent" ON public.temp_taxo USING btree (idparent);


--
-- Name: is_objectfieldsorigid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectfieldsorigid ON public.obj_field USING btree (orig_id);


--
-- Name: is_objectsdate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectsdate ON public.obj_head USING btree (objdate, projid);


--
-- Name: is_objectsdepth; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectsdepth ON public.obj_head USING btree (depth_max, depth_min, projid);


--
-- Name: is_objectslatlong; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectslatlong ON public.obj_head USING btree (latitude, longitude);


--
-- Name: is_objectsprojclassifqual; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectsprojclassifqual ON public.obj_head USING btree (projid, classif_id, classif_qual);


--
-- Name: is_objectsprojectonly; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectsprojectonly ON public.obj_head USING btree (projid);


--
-- Name: is_objectsprojrandom; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectsprojrandom ON public.obj_head USING btree (projid, random_value, classif_qual);


--
-- Name: is_objectssample; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectssample ON public.obj_head USING btree (sampleid);


--
-- Name: is_objectstime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_objectstime ON public.obj_head USING btree (objtime, projid);


--
-- Name: is_part_projects_projid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_part_projects_projid ON public.part_projects USING btree (projid);


--
-- Name: is_part_samples_prj; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_part_samples_prj ON public.part_samples USING btree (pprojid);


--
-- Name: is_part_samples_sampleid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_part_samples_sampleid ON public.part_samples USING btree (sampleid);


--
-- Name: is_taxonomydispnamelow; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX is_taxonomydispnamelow ON public.taxonomy USING btree (lower((display_name)::text));


--
-- Name: acquisitions acquisitions_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.acquisitions
    ADD CONSTRAINT acquisitions_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid);


--
-- Name: images images_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head(objid);


--
-- Name: obj_cnn_features obj_cnn_features_objcnnid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_cnn_features
    ADD CONSTRAINT obj_cnn_features_objcnnid_fkey FOREIGN KEY (objcnnid) REFERENCES public.obj_head(objid) ON DELETE CASCADE;


--
-- Name: obj_field obj_field_objfid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_field
    ADD CONSTRAINT obj_field_objfid_fkey FOREIGN KEY (objfid) REFERENCES public.obj_head(objid) ON DELETE CASCADE;


--
-- Name: obj_head obj_head_acquisid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid) REFERENCES public.acquisitions(acquisid);


--
-- Name: obj_head obj_head_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);


--
-- Name: obj_head obj_head_processid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_processid_fkey FOREIGN KEY (processid) REFERENCES public.process(processid);


--
-- Name: obj_head obj_head_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid);


--
-- Name: obj_head obj_head_sampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.obj_head
    ADD CONSTRAINT obj_head_sampleid_fkey FOREIGN KEY (sampleid) REFERENCES public.samples(sampleid);


--
-- Name: objectsclassifhisto objectsclassifhisto_classif_who_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_classif_who_fkey FOREIGN KEY (classif_who) REFERENCES public.users(id);


--
-- Name: objectsclassifhisto objectsclassifhisto_objid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objectsclassifhisto
    ADD CONSTRAINT objectsclassifhisto_objid_fkey FOREIGN KEY (objid) REFERENCES public.obj_head(objid) ON DELETE CASCADE;


--
-- Name: part_ctd part_ctd_psampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_ctd
    ADD CONSTRAINT part_ctd_psampleid_fkey FOREIGN KEY (psampleid) REFERENCES public.part_samples(psampleid);


--
-- Name: part_histocat_lst part_histocat_lst_psampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histocat_lst
    ADD CONSTRAINT part_histocat_lst_psampleid_fkey FOREIGN KEY (psampleid) REFERENCES public.part_samples(psampleid);


--
-- Name: part_histocat part_histocat_psampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histocat
    ADD CONSTRAINT part_histocat_psampleid_fkey FOREIGN KEY (psampleid) REFERENCES public.part_samples(psampleid);


--
-- Name: part_histopart_det part_histopart_det_psampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histopart_det
    ADD CONSTRAINT part_histopart_det_psampleid_fkey FOREIGN KEY (psampleid) REFERENCES public.part_samples(psampleid);


--
-- Name: part_histopart_reduit part_histopart_reduit_psampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_histopart_reduit
    ADD CONSTRAINT part_histopart_reduit_psampleid_fkey FOREIGN KEY (psampleid) REFERENCES public.part_samples(psampleid);


--
-- Name: part_projects part_projects_ownerid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_projects
    ADD CONSTRAINT part_projects_ownerid_fkey FOREIGN KEY (ownerid) REFERENCES public.users(id);


--
-- Name: part_projects part_projects_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_projects
    ADD CONSTRAINT part_projects_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid);


--
-- Name: part_samples part_samples_pprojid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_samples
    ADD CONSTRAINT part_samples_pprojid_fkey FOREIGN KEY (pprojid) REFERENCES public.part_projects(pprojid);


--
-- Name: part_samples part_samples_sampleid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.part_samples
    ADD CONSTRAINT part_samples_sampleid_fkey FOREIGN KEY (sampleid) REFERENCES public.samples(sampleid);


--
-- Name: process process_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.process
    ADD CONSTRAINT process_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid);


--
-- Name: projects_taxo_stat projects_taxo_stat_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects_taxo_stat
    ADD CONSTRAINT projects_taxo_stat_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid) ON DELETE CASCADE;


--
-- Name: projectspriv projectspriv_member_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projectspriv
    ADD CONSTRAINT projectspriv_member_fkey FOREIGN KEY (member) REFERENCES public.users(id);


--
-- Name: projectspriv projectspriv_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projectspriv
    ADD CONSTRAINT projectspriv_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid) ON DELETE CASCADE;


--
-- Name: samples samples_projid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.samples
    ADD CONSTRAINT samples_projid_fkey FOREIGN KEY (projid) REFERENCES public.projects(projid);


--
-- Name: temp_tasks temp_tasks_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_tasks
    ADD CONSTRAINT temp_tasks_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: users_roles users_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users_roles
    ADD CONSTRAINT users_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: users_roles users_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users_roles
    ADD CONSTRAINT users_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES  FROM postgres;


--
-- PostgreSQL database dump complete
--
COPY public.roles (id, name) FROM stdin;
1	Application Administrator
2	Users Administrator
\.

COPY public.users (id, email, password, name, organisation, active, preferences, country, usercreationdate, usercreationreason) FROM stdin;
1	admin	$6$rounds=656000$cpR/DTfGpK/L/N19$DnR/n7AZeqFNfoGkBM05o6GUoxPgolw01TglHbNVpB2522LLlUI6soZ5b4eW7TjeYj.uMC3G79NGeaX1baHCP1	Application Administrator	\N	t	{"1": {"sortby": "", "ts": 1589266843.5535243, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}, "2": {"sortby": "", "ts": 1589267270.5538993, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}}	\N	2020-05-12 08:59:48.70106	\N
\.

COPY public.users_roles (user_id, role_id) FROM stdin;
1	1
\.

COPY public.taxonomy (id, parent_id, name, id_source, nbrobj, nbrobjcum, creation_datetime, creator_email, display_name, id_instance, lastupdate_datetime, rename_to, source_desc, source_url, taxostatus, taxotype) FROM stdin;
1	\N	living	0	8	6	\N	\N	Living	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
45072	1	Cyclopoida	48740	68979	502724	\N	\N	Cyclopoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
78418	1	Oncaeidae	87064	199577	64180	\N	\N	Oncaeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
84963	1	detritus	m002	8206157	2131844	\N	\N	detritus	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85011	1	other	m004	1175412	992515	\N	\N	other<living	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
99999	1	other	m004	0	0	\N	\N	other<dead	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85012	1	t001	m142	180622	\N	\N	\N	t001	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85078	1	egg	m129	142336	3465	\N	\N	egg<other	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
\.

