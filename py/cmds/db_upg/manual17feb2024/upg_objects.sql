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
