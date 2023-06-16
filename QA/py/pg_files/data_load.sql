--- Extra read-only role
CREATE ROLE readerole WITH
  LOGIN
  NOSUPERUSER
  INHERIT
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION
  PASSWORD 'Ec0t1x1Rd4';

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole;

delete from users where id > 1;

COPY public.users (id, email, password, name, organisation, active, preferences, country, usercreationdate, usercreationreason) FROM stdin;
2	user	$6$	Ordinary User	Homework	t	{}	\N	2020-05-13 08:59:48.70106	\N
3	creator	$6$rounds=656000$iPCU2dUnIQjcUnuW$JxMguozUT9nTun/N19yx.ugzTlUL4bZTRB9eOqECLx83kNSarP6uAMze1qu1ULjJ/OugQAMyAYxFI4EHy0yn9/	User Creating Projects	\N	t	{}	\N	2020-05-13 08:59:48.70106	\N
4	user2	$6$	Ordinary User 2	\N	t	{}	\N	2020-09-27 06:39:48.70106	\N
5	old_admin	nimda_dlo	Application Administrator Now Retired	\N	f	{"1": {"sortby": "", "ts": 1589266843.5535243, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}, "2": {"sortby": "", "ts": 1589267270.5538993, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}}	\N	2020-05-12 08:59:48.70106	\N
6	real@users.com	fake_pwd	Real User	Institut de la Mer de Villefranche - IMEV	f	{"1": {"sortby": "", "ts": 1589266843.5535243, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}}	France	2020-10-26 08:59:48.70106	\N
7	ucrank4@gov.uk	fake_pwd	Udale Crank	Institut de la Mer de Villefranche - IMEV	f	{"1": {"sortby": "", "ts": 1589266843.5535243, "sortorder": "asc", "dispfield": "", "statusfilter": "", "ipp": "100", "zoom": "100", "magenabled": "0", "popupenabled": "0"}}	UK	2020-10-26 08:59:48.70106	\N
8	real2@users.com	fake_pwd	Real User 3	Double Dash - Institute - DDORG	f	{}	Chile	2023-01-01 08:59:48.70106	\N
\.

SELECT setval('seq_users', (SELECT max(id) FROM public.users), true);

COPY public.users_roles (user_id, role_id) FROM stdin;
3	3
6	3
\.

-- The used ones are in first
-- e.g. to get some data with lineage:
-- ecotaxa4=# copy (select * from taxonomy where id in (92731, 85117, 56693, 25928, 16656, 12861,11513,2367,382,8)) to '/tmp/cp.sql';
-- in case of problem during tests, 'data_load.log' in tests can show the COPY issues
COPY public.taxonomy (id, parent_id, name, id_source, nbrobj, nbrobjcum, creation_datetime, creator_email, display_name, id_instance, lastupdate_datetime, rename_to, source_desc, source_url, taxostatus, taxotype) FROM stdin;
45072	1	Cyclopoida	48740	68979	502724	\N	\N	Cyclopoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
78418	1	Oncaeidae	87064	199577	64180	\N	\N	Oncaeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
84963	1	detritus	m002	8206157	2131844	\N	\N	detritus	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85011	1	other	m004	1175412	992515	\N	\N	other<living	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
99999	1	other	m004	0	0	\N	\N	other<dead	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85012	1	t001	m142	180622	\N	\N	\N	t001	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85078	1	egg	m129	142336	3465	\N	\N	egg<other	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
8	2	Opisthokonta	29367	0	26545188	\N	\N	Opisthokonta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
382	8	Holozoa	40247	0	26542007	\N	\N	Holozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2367	382	Metazoa	40455	445	26541560	\N	\N	Metazoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
11513	2367	Chordata	66472	84	1633987	\N	\N	Chordata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
12861	11513	Craniata	66478	0	519587	\N	\N	Craniata<Chordata	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
16656	12861	Vertebrata	66656	10	519587	\N	\N	Vertebrata<Craniata	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
56693	25928	Actinopterygii	66657	47270	509496	\N	\N	Actinopterygii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
85117	56693	egg	m723	95376	100961	\N	\N	egg<Actinopterygii	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
92731	85117	small		510	510	2019-01-29 13:57:46	christophe.loots@ifremer.fr	small<egg	1	2019-01-29 13:59:45	\N	Small eggs in the eastern English Channel and southern North Sea during winter. Gathers mainly dab, flounder and rocklings eggs.		N	M
1	\N	living	0	\N	\N	\N	\N	living<	\N	2020-07-31 13:51:26	\N	\N	\N	A	P
2	1	Eukaryota	11831	\N	\N	\N	\N	Eukaryota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3	1	Bacteria	424	\N	\N	\N	\N	Bacteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4	1	Archaea	1	\N	\N	\N	\N	Archaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5	2	Harosa	87173	\N	\N	\N	\N	Harosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
6	2	Unknowns	85352	\N	\N	\N	\N	Unknowns	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
7	2	Orphans	79922	\N	\N	\N	\N	Orphans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
9	2	Excavata	28400	\N	\N	\N	\N	Excavata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
10	2	Eukaryota X	28398	\N	\N	\N	\N	Eukaryota X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
11	2	environmental samples	28390	\N	\N	\N	\N	environmental samples<Eukaryota	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
12	2	Archaeplastida	18850	\N	\N	\N	\N	Archaeplastida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
13	2	Amoebozoa	17765	\N	\N	\N	\N	Amoebozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
14	3	Xanthomonadaceae	11686	\N	\N	\N	\N	Xanthomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
15	3	Xanthobacteraceae	11653	\N	\N	\N	\N	Xanthobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
16	3	Waddliaceae	11650	\N	\N	\N	\N	Waddliaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
17	3	Victivallaceae	11647	\N	\N	\N	\N	Victivallaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
18	3	Vibrionaceae	11538	\N	\N	\N	\N	Vibrionaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
19	3	Verrucomicrobiaceae	11514	\N	\N	\N	\N	Verrucomicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
20	3	Veillonellaceae	11432	\N	\N	\N	\N	Veillonellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
21	3	Tsukamurellaceae	11419	\N	\N	\N	\N	Tsukamurellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
22	3	Trueperaceae	11416	\N	\N	\N	\N	Trueperaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
23	3	Thiotrichales	11410	\N	\N	\N	\N	Thiotrichales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
24	3	Thiotrichaceae	11394	\N	\N	\N	\N	Thiotrichaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25	3	Thioalkalispiraceae	11388	\N	\N	\N	\N	Thioalkalispiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26	3	Thermotogaceae	11343	\N	\N	\N	\N	Thermotogaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27	3	Thermosporotrichaceae	11340	\N	\N	\N	\N	Thermosporotrichaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28	3	Thermomonosporaceae	11262	\N	\N	\N	\N	Thermomonosporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
29	3	Thermomicrobiaceae	11259	\N	\N	\N	\N	Thermomicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
30	3	Thermolithobacteraceae	11255	\N	\N	\N	\N	Thermolithobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
31	3	Thermoleophilaceae	11251	\N	\N	\N	\N	Thermoleophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
32	3	Thermogemmatisporaceae	11247	\N	\N	\N	\N	Thermogemmatisporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
33	3	Thermodesulfobiaceae	11243	\N	\N	\N	\N	Thermodesulfobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
34	3	Thermodesulfobacteriaceae	11234	\N	\N	\N	\N	Thermodesulfobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
35	3	Thermoanaerobacterales	11206	\N	\N	\N	\N	Thermoanaerobacterales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
36	3	Thermoanaerobacteraceae	11152	\N	\N	\N	\N	Thermoanaerobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
37	3	Thermoactinomycetaceae	11124	\N	\N	\N	\N	Thermoactinomycetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
38	3	Thermithiobacillaceae	11121	\N	\N	\N	\N	Thermithiobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
39	3	Thermaceae	11089	\N	\N	\N	\N	Thermaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
40	3	Syntrophorhabdaceae	11086	\N	\N	\N	\N	Syntrophorhabdaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
41	3	Syntrophomonadaceae	11064	\N	\N	\N	\N	Syntrophomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
42	3	Syntrophobacteraceae	11045	\N	\N	\N	\N	Syntrophobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
43	3	Syntrophaceae	11036	\N	\N	\N	\N	Syntrophaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
44	3	Synergistaceae	11014	\N	\N	\N	\N	Synergistaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
45	3	Sutterellaceae	11006	\N	\N	\N	\N	Sutterellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
46	3	Succinivibrionaceae	10994	\N	\N	\N	\N	Succinivibrionaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
47	3	Streptosporangineae	10991	\N	\N	\N	\N	Streptosporangineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
48	3	Streptosporangiaceae	10899	\N	\N	\N	\N	Streptosporangiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
49	3	Streptomycetaceae	10336	\N	\N	\N	\N	Streptomycetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
50	3	Streptococcaceae	10253	\N	\N	\N	\N	Streptococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
51	3	Stigonematales	10250	\N	\N	\N	\N	Stigonematales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
52	3	Staphylococcaceae	10162	\N	\N	\N	\N	Staphylococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
53	3	Sporolactobacillaceae	10146	\N	\N	\N	\N	Sporolactobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
54	3	Sporichthyaceae	10142	\N	\N	\N	\N	Sporichthyaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
55	3	Spiroplasmataceae	10106	\N	\N	\N	\N	Spiroplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
56	3	Spirochaetales	10103	\N	\N	\N	\N	Spirochaetales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
57	3	Spirochaetaceae	10050	\N	\N	\N	\N	Spirochaetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
58	3	Spirillaceae	10046	\N	\N	\N	\N	Spirillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
59	3	Sphingomonadaceae	9910	\N	\N	\N	\N	Sphingomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
60	3	Sphingobacteriales	9907	\N	\N	\N	\N	Sphingobacteriales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
61	3	Sphingobacteriaceae	9833	\N	\N	\N	\N	Sphingobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
62	3	Sphaerobacteraceae	9830	\N	\N	\N	\N	Sphaerobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
63	3	Solirubrobacteraceae	9826	\N	\N	\N	\N	Solirubrobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
64	3	Sneathiellaceae	9822	\N	\N	\N	\N	Sneathiellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
65	3	Sinobacteraceae	9819	\N	\N	\N	\N	Sinobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
66	3	Simkaniaceae	9816	\N	\N	\N	\N	Simkaniaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
67	3	Shewanellaceae	9759	\N	\N	\N	\N	Shewanellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
68	3	Segniliparaceae	9755	\N	\N	\N	\N	Segniliparaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
69	3	Schleiferiaceae	9752	\N	\N	\N	\N	Schleiferiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
70	3	Saprospiraceae	9739	\N	\N	\N	\N	Saprospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
71	3	Sanguibacteraceae	9731	\N	\N	\N	\N	Sanguibacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
72	3	Sandaracinaceae	9728	\N	\N	\N	\N	Sandaracinaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
73	3	Salinisphaeraceae	9723	\N	\N	\N	\N	Salinisphaeraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
74	3	Saccharospirillaceae	9718	\N	\N	\N	\N	Saccharospirillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
75	3	Ruminococcaceae	9688	\N	\N	\N	\N	Ruminococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
76	3	Rubrobacteraceae	9683	\N	\N	\N	\N	Rubrobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
77	3	Rubritaleaceae	9675	\N	\N	\N	\N	Rubritaleaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
78	3	Ruaniaceae	9670	\N	\N	\N	\N	Ruaniaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
79	3	Rikenellaceae	9661	\N	\N	\N	\N	Rikenellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
80	3	Rickettsiaceae	9638	\N	\N	\N	\N	Rickettsiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
81	3	Rhodothermaceae	9626	\N	\N	\N	\N	Rhodothermaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
82	3	Rhodospirillales	9621	\N	\N	\N	\N	Rhodospirillales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
83	3	Rhodospirillaceae	9537	\N	\N	\N	\N	Rhodospirillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
84	3	Rhodocyclaceae	9479	\N	\N	\N	\N	Rhodocyclaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
85	3	Rhodobiaceae	9461	\N	\N	\N	\N	Rhodobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
86	3	Rhodobacteraceae	9138	\N	\N	\N	\N	Rhodobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
87	3	Rhizobiales	9128	\N	\N	\N	\N	Rhizobiales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
88	3	Rhizobiaceae	9049	\N	\N	\N	\N	Rhizobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
89	3	Rarobacteraceae	9045	\N	\N	\N	\N	Rarobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
90	3	Puniceicoccaceae	9033	\N	\N	\N	\N	Puniceicoccaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
91	3	Psychromonadaceae	9017	\N	\N	\N	\N	Psychromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
92	3	Pseudonocardiaceae	8785	\N	\N	\N	\N	Pseudonocardiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
93	3	Pseudomonadales	8782	\N	\N	\N	\N	Pseudomonadales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
94	3	Pseudomonadaceae	8611	\N	\N	\N	\N	Pseudomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
95	3	Pseudoalteromonadaceae	8571	\N	\N	\N	\N	Pseudoalteromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
96	3	Proteobacteria	8357	\N	\N	\N	\N	Proteobacteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
97	3	Propionibacteriaceae	8300	\N	\N	\N	\N	Propionibacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
98	3	Promicromonosporaceae	8271	\N	\N	\N	\N	Promicromonosporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
99	3	Prochlorotrichaceae	8268	\N	\N	\N	\N	Prochlorotrichaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
100	3	Prochlorococcaceae	8264	\N	\N	\N	\N	Prochlorococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
101	3	Prevotellaceae	8215	\N	\N	\N	\N	Prevotellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
102	3	Porphyromonadaceae	8168	\N	\N	\N	\N	Porphyromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
103	3	Polyangiaceae	8159	\N	\N	\N	\N	Polyangiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
104	3	Planococcaceae	8099	\N	\N	\N	\N	Planococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
105	3	Planctomycetaceae	8075	\N	\N	\N	\N	Planctomycetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
106	3	Piscirickettsiaceae	8046	\N	\N	\N	\N	Piscirickettsiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
107	3	Phyllobacteriaceae	7988	\N	\N	\N	\N	Phyllobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
108	3	Phycisphaeraceae	7985	\N	\N	\N	\N	Phycisphaeraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
109	3	Phaselicystidaceae	7982	\N	\N	\N	\N	Phaselicystidaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
110	3	Peptostreptococcaceae	7967	\N	\N	\N	\N	Peptostreptococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
111	3	Peptococcaceae	7909	\N	\N	\N	\N	Peptococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
112	3	Patulibacteraceae	7904	\N	\N	\N	\N	Patulibacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
113	3	Pasteurellaceae	7860	\N	\N	\N	\N	Pasteurellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
114	3	Parvularculaceae	7856	\N	\N	\N	\N	Parvularculaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
115	3	Parachlamydiaceae	7851	\N	\N	\N	\N	Parachlamydiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
116	3	Paenibacillaceae	7675	\N	\N	\N	\N	Paenibacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
117	3	Oxalobacteraceae	7609	\N	\N	\N	\N	Oxalobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
118	3	Oscillospiraceae	7606	\N	\N	\N	\N	Oscillospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
119	3	Oscillatoriales	7599	\N	\N	\N	\N	Oscillatoriales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
120	3	Opitutaceae	7594	\N	\N	\N	\N	Opitutaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
121	3	Oleiphilaceae	7591	\N	\N	\N	\N	Oleiphilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
122	3	Oceanospirillales	7585	\N	\N	\N	\N	Oceanospirillales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
123	3	Oceanospirillaceae	7531	\N	\N	\N	\N	Oceanospirillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
124	3	Nocardiopsaceae	7473	\N	\N	\N	\N	Nocardiopsaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
125	3	Nocardioidaceae	7376	\N	\N	\N	\N	Nocardioidaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
126	3	Nocardiaceae	7213	\N	\N	\N	\N	Nocardiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
127	3	Nitrospiraceae	7202	\N	\N	\N	\N	Nitrospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
128	3	Nitrosomonadaceae	7197	\N	\N	\N	\N	Nitrosomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
129	3	Nitriliruptoraceae	7194	\N	\N	\N	\N	Nitriliruptoraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
130	3	Nevskiaceae	7186	\N	\N	\N	\N	Nevskiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
131	3	Neisseriaceae	7094	\N	\N	\N	\N	Neisseriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
132	3	Nautiliaceae	7080	\N	\N	\N	\N	Nautiliaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
133	3	Natranaerobiaceae	7076	\N	\N	\N	\N	Natranaerobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
134	3	Nannocystaceae	7068	\N	\N	\N	\N	Nannocystaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
135	3	Nakamurellaceae	7061	\N	\N	\N	\N	Nakamurellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
136	3	Myxococcaceae	7050	\N	\N	\N	\N	Myxococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
137	3	Mycoplasmataceae	6934	\N	\N	\N	\N	Mycoplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
138	3	Mycobacteriaceae	6789	\N	\N	\N	\N	Mycobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
139	3	Moritellaceae	6778	\N	\N	\N	\N	Moritellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
140	3	Moraxellaceae	6706	\N	\N	\N	\N	Moraxellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
141	3	Micromonosporaceae	6539	\N	\N	\N	\N	Micromonosporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
142	3	Micrococcineae	6534	\N	\N	\N	\N	Micrococcineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
143	3	Micrococcaceae	6404	\N	\N	\N	\N	Micrococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
144	3	Microbacteriaceae	6170	\N	\N	\N	\N	Microbacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
145	3	Methylophilaceae	6155	\N	\N	\N	\N	Methylophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
146	3	Methylocystaceae	6133	\N	\N	\N	\N	Methylocystaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
147	3	Methylococcaceae	6088	\N	\N	\N	\N	Methylococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
148	3	Methylobacteriaceae	6042	\N	\N	\N	\N	Methylobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
149	3	Mariprofundaceae	6039	\N	\N	\N	\N	Mariprofundaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
150	3	Marinilabiliaceae	6026	\N	\N	\N	\N	Marinilabiliaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
151	3	Litoricolaceae	6022	\N	\N	\N	\N	Litoricolaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
152	3	Listeriaceae	6010	\N	\N	\N	\N	Listeriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
153	3	Leuconostocaceae	5969	\N	\N	\N	\N	Leuconostocaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
154	3	Leptotrichiaceae	5957	\N	\N	\N	\N	Leptotrichiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
155	3	Leptospiraceae	5939	\N	\N	\N	\N	Leptospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
156	3	Lentisphaeraceae	5936	\N	\N	\N	\N	Lentisphaeraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
157	3	Legionellaceae	5897	\N	\N	\N	\N	Legionellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
158	3	Lactobacillaceae	5730	\N	\N	\N	\N	Lactobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
159	3	Lachnospiraceae	5680	\N	\N	\N	\N	Lachnospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
160	3	Ktedonobacteraceae	5677	\N	\N	\N	\N	Ktedonobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
161	3	Kordiimonadaceae	5673	\N	\N	\N	\N	Kordiimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
162	3	Kofleriaceae	5670	\N	\N	\N	\N	Kofleriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
163	3	Kineosporiaceae	5653	\N	\N	\N	\N	Kineosporiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
164	3	Kiloniellaceae	5650	\N	\N	\N	\N	Kiloniellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
165	3	Jonesiaceae	5646	\N	\N	\N	\N	Jonesiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
166	3	Jiangellaceae	5638	\N	\N	\N	\N	Jiangellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
167	3	Intrasporangiaceae	5564	\N	\N	\N	\N	Intrasporangiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
168	3	Ignavibacteriaceae	5561	\N	\N	\N	\N	Ignavibacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
169	3	Idiomarinaceae	5536	\N	\N	\N	\N	Idiomarinaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
170	3	Iamiaceae	5533	\N	\N	\N	\N	Iamiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
171	3	Hyphomonadaceae	5504	\N	\N	\N	\N	Hyphomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
172	3	Hyphomicrobiaceae	5442	\N	\N	\N	\N	Hyphomicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
173	3	Hydrogenothermaceae	5429	\N	\N	\N	\N	Hydrogenothermaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
174	3	Hydrogenophilaceae	5414	\N	\N	\N	\N	Hydrogenophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
175	3	Holophagaceae	5409	\N	\N	\N	\N	Holophagaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
176	3	Herpetosiphonaceae	5405	\N	\N	\N	\N	Herpetosiphonaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
177	3	Heliobacteriaceae	5393	\N	\N	\N	\N	Heliobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
178	3	Helicobacteraceae	5352	\N	\N	\N	\N	Helicobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
179	3	Halothiobacillaceae	5341	\N	\N	\N	\N	Halothiobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
180	3	Halomonadaceae	5242	\N	\N	\N	\N	Halomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
181	3	Halobacteroidaceae	5221	\N	\N	\N	\N	Halobacteroidaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
182	3	Haliangiaceae	5217	\N	\N	\N	\N	Haliangiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
183	3	Halanaerobiaceae	5202	\N	\N	\N	\N	Halanaerobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
184	3	Hahellaceae	5189	\N	\N	\N	\N	Hahellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
185	3	Granulosicoccaceae	5185	\N	\N	\N	\N	Granulosicoccaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
186	3	Gracilibacteraceae	5182	\N	\N	\N	\N	Gracilibacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
187	3	Glycomycetaceae	5165	\N	\N	\N	\N	Glycomycetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
188	3	Geodermatophilaceae	5153	\N	\N	\N	\N	Geodermatophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
189	3	Geobacteraceae	5136	\N	\N	\N	\N	Geobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
190	3	Gemmatimonadaceae	5133	\N	\N	\N	\N	Gemmatimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
191	3	Gammaproteobacteria	5089	\N	\N	\N	\N	Gammaproteobacteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
192	3	Gaiellaceae	5086	\N	\N	\N	\N	Gaiellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
193	3	Fusobacteriaceae	5059	\N	\N	\N	\N	Fusobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
194	3	Frankineae	5056	\N	\N	\N	\N	Frankineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
195	3	Francisellaceae	5046	\N	\N	\N	\N	Francisellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
196	3	Flavobacteriaceae	4653	\N	\N	\N	\N	Flavobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
197	3	Flammeovirgaceae	4612	\N	\N	\N	\N	Flammeovirgaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
198	3	Fibrobacteraceae	4607	\N	\N	\N	\N	Fibrobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
199	3	Ferrimonadaceae	4598	\N	\N	\N	\N	Ferrimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
200	3	Euzebyaceae	4595	\N	\N	\N	\N	Euzebyaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
201	3	Eubacteriaceae	4534	\N	\N	\N	\N	Eubacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
202	3	Erythrobacteraceae	4499	\N	\N	\N	\N	Erythrobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
203	3	Erysipelotrichaceae	4476	\N	\N	\N	\N	Erysipelotrichaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
204	3	Entomoplasmataceae	4457	\N	\N	\N	\N	Entomoplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
205	3	Enterococcaceae	4397	\N	\N	\N	\N	Enterococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
206	3	Enterobacteriaceae	4142	\N	\N	\N	\N	Enterobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
207	3	Elusimicrobiaceae	4139	\N	\N	\N	\N	Elusimicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
208	3	Ectothiorhodospiraceae	4099	\N	\N	\N	\N	Ectothiorhodospiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
209	3	Dietziaceae	4084	\N	\N	\N	\N	Dietziaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
210	3	Dictyoglomaceae	4080	\N	\N	\N	\N	Dictyoglomaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
211	3	Desulfuromonadaceae	4058	\N	\N	\N	\N	Desulfuromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
212	3	Desulfurobacteriaceae	4048	\N	\N	\N	\N	Desulfurobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
213	3	Desulfurellaceae	4038	\N	\N	\N	\N	Desulfurellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
214	3	Desulfovibrionaceae	3972	\N	\N	\N	\N	Desulfovibrionaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
215	3	Desulfonatronaceae	3965	\N	\N	\N	\N	Desulfonatronaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
216	3	Desulfomicrobiaceae	3956	\N	\N	\N	\N	Desulfomicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
217	3	Desulfohalobiaceae	3942	\N	\N	\N	\N	Desulfohalobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
218	3	Desulfobulbaceae	3922	\N	\N	\N	\N	Desulfobulbaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
219	3	Desulfobacteraceae	3865	\N	\N	\N	\N	Desulfobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
220	3	Desulfarculaceae	3862	\N	\N	\N	\N	Desulfarculaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
221	3	Dermatophilaceae	3851	\N	\N	\N	\N	Dermatophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
222	3	Dermacoccaceae	3831	\N	\N	\N	\N	Dermacoccaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
223	3	Dermabacteraceae	3809	\N	\N	\N	\N	Dermabacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
224	3	Demequinaceae	3800	\N	\N	\N	\N	Demequinaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
225	3	Deinococcaceae	3750	\N	\N	\N	\N	Deinococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
226	3	Dehalococcoidetes	3747	\N	\N	\N	\N	Dehalococcoidetes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
227	3	Defluviitaleaceae	3744	\N	\N	\N	\N	Defluviitaleaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
228	3	Deferribacterales	3740	\N	\N	\N	\N	Deferribacterales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
229	3	Deferribacteraceae	3723	\N	\N	\N	\N	Deferribacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
230	3	Cytophagaceae	3624	\N	\N	\N	\N	Cytophagaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
231	3	Cystobacteraceae	3604	\N	\N	\N	\N	Cystobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
232	3	Cyclobacteriaceae	3560	\N	\N	\N	\N	Cyclobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
233	3	Cyanobacteria	2880	\N	\N	\N	\N	Cyanobacteria<Bacteria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
234	3	Cryptosporangiaceae	2872	\N	\N	\N	\N	Cryptosporangiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
235	3	Cryomorphaceae	2858	\N	\N	\N	\N	Cryomorphaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
236	3	Coxiellaceae	2850	\N	\N	\N	\N	Coxiellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
237	3	Corynebacterineae	2847	\N	\N	\N	\N	Corynebacterineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
238	3	Corynebacteriaceae	2776	\N	\N	\N	\N	Corynebacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
239	3	Coriobacteriaceae	2736	\N	\N	\N	\N	Coriobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
240	3	Conexibacteraceae	2733	\N	\N	\N	\N	Conexibacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
241	3	Comamonadaceae	2602	\N	\N	\N	\N	Comamonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
242	3	Colwelliaceae	2583	\N	\N	\N	\N	Colwelliaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
243	3	Cohaesibacteraceae	2579	\N	\N	\N	\N	Cohaesibacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
244	3	Clostridiales	2484	\N	\N	\N	\N	Clostridiales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
245	3	Clostridiaceae	2256	\N	\N	\N	\N	Clostridiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
246	3	Chthonomonadaceae	2253	\N	\N	\N	\N	Chthonomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
247	3	Chrysiogenaceae	2245	\N	\N	\N	\N	Chrysiogenaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
248	3	Chroococcales	2242	\N	\N	\N	\N	Chroococcales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
249	3	Chromatiaceae	2179	\N	\N	\N	\N	Chromatiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
250	3	Christensenellaceae	2176	\N	\N	\N	\N	Christensenellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
251	3	Chloroflexaceae	2170	\N	\N	\N	\N	Chloroflexaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
252	3	Chlorobiaceae	2157	\N	\N	\N	\N	Chlorobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
253	3	Chlamydiaceae	2145	\N	\N	\N	\N	Chlamydiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
254	3	Chitinophagaceae	2096	\N	\N	\N	\N	Chitinophagaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
255	3	Cellulomonadaceae	2068	\N	\N	\N	\N	Cellulomonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
256	3	Celerinatantimonadaceae	2065	\N	\N	\N	\N	Celerinatantimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
257	3	Caulobacteraceae	2021	\N	\N	\N	\N	Caulobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
258	3	Catenulisporaceae	2015	\N	\N	\N	\N	Catenulisporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
259	3	Carnobacteriaceae	1963	\N	\N	\N	\N	Carnobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
260	3	Cardiobacteriaceae	1956	\N	\N	\N	\N	Cardiobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
261	3	Campylobacteraceae	1923	\N	\N	\N	\N	Campylobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
262	3	Caldisericaceae	1920	\N	\N	\N	\N	Caldisericaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
263	3	Caldilineaceae	1916	\N	\N	\N	\N	Caldilineaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
264	3	Caldicoprobacteraceae	1912	\N	\N	\N	\N	Caldicoprobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
265	3	Burkholderiales	1861	\N	\N	\N	\N	Burkholderiales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
266	3	Burkholderiaceae	1759	\N	\N	\N	\N	Burkholderiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
267	3	Brucellaceae	1717	\N	\N	\N	\N	Brucellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
268	3	Brevinemataceae	1714	\N	\N	\N	\N	Brevinemataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
269	3	Brevibacteriaceae	1690	\N	\N	\N	\N	Brevibacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
270	3	Bradyrhizobiaceae	1641	\N	\N	\N	\N	Bradyrhizobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
271	3	Brachyspiraceae	1632	\N	\N	\N	\N	Brachyspiraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
272	3	Bogoriellaceae	1623	\N	\N	\N	\N	Bogoriellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
273	3	Bifidobacteriaceae	1566	\N	\N	\N	\N	Bifidobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
274	3	Beutenbergiaceae	1557	\N	\N	\N	\N	Beutenbergiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
275	3	Betaproteobacteria	1554	\N	\N	\N	\N	Betaproteobacteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
276	3	Beijerinckiaceae	1526	\N	\N	\N	\N	Beijerinckiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
277	3	Bdellovibrionaceae	1523	\N	\N	\N	\N	Bdellovibrionaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
278	3	Bartonellaceae	1498	\N	\N	\N	\N	Bartonellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
279	3	Bacteroidetes	1490	\N	\N	\N	\N	Bacteroidetes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
280	3	Bacteroidales	1485	\N	\N	\N	\N	Bacteroidales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
281	3	Bacteroidaceae	1446	\N	\N	\N	\N	Bacteroidaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
282	3	Bacteriovoracaceae	1440	\N	\N	\N	\N	Bacteriovoracaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
283	3	Bacillales	1414	\N	\N	\N	\N	Bacillales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
284	3	Bacillaceae	1048	\N	\N	\N	\N	Bacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
285	3	Aurantimonadaceae	1036	\N	\N	\N	\N	Aurantimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
286	3	Armatimonadaceae	1033	\N	\N	\N	\N	Armatimonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
287	3	Aquificaceae	1019	\N	\N	\N	\N	Aquificaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
288	3	Anaplasmataceae	1006	\N	\N	\N	\N	Anaplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
289	3	Anaeroplasmataceae	999	\N	\N	\N	\N	Anaeroplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
290	3	Anaerolineaceae	987	\N	\N	\N	\N	Anaerolineaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
291	3	Alteromonadales	976	\N	\N	\N	\N	Alteromonadales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
292	3	Alteromonadaceae	871	\N	\N	\N	\N	Alteromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
293	3	Alphaproteobacteria	863	\N	\N	\N	\N	Alphaproteobacteria<Bacteria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
294	3	Alicyclobacillaceae	835	\N	\N	\N	\N	Alicyclobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
295	3	Alcanivoracaceae	820	\N	\N	\N	\N	Alcanivoracaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
296	3	Alcaligenaceae	759	\N	\N	\N	\N	Alcaligenaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
297	3	Akkermansiaceae	756	\N	\N	\N	\N	Akkermansiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
298	3	Aeromonadaceae	709	\N	\N	\N	\N	Aeromonadaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
299	3	Aerococcaceae	694	\N	\N	\N	\N	Aerococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
300	3	Actinospicaceae	690	\N	\N	\N	\N	Actinospicaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
301	3	Actinopolysporaceae	683	\N	\N	\N	\N	Actinopolysporaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
302	3	Actinomycetaceae	638	\N	\N	\N	\N	Actinomycetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
303	3	Acidothermaceae	635	\N	\N	\N	\N	Acidothermaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
304	3	Acidobacteriaceae	614	\N	\N	\N	\N	Acidobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
305	3	Acidobacteria	611	\N	\N	\N	\N	Acidobacteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
306	3	Acidithiobacillaceae	604	\N	\N	\N	\N	Acidithiobacillaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
307	3	Acidimicrobineae	601	\N	\N	\N	\N	Acidimicrobineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
308	3	Acidimicrobiaceae	594	\N	\N	\N	\N	Acidimicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
309	3	Acidaminococcaceae	583	\N	\N	\N	\N	Acidaminococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
310	3	Acholeplasmataceae	567	\N	\N	\N	\N	Acholeplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
311	3	Acetobacteraceae	428	\N	\N	\N	\N	Acetobacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
312	3	Acanthopleuribacteraceae	425	\N	\N	\N	\N	Acanthopleuribacteraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
313	4	Lokiarchaeota	87179	\N	\N	\N	\N	Lokiarchaeota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
314	4	unclassified Euryarchaeota	421	\N	\N	\N	\N	unclassified Euryarchaeota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
315	4	Thermoproteaceae	405	\N	\N	\N	\N	Thermoproteaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
316	4	Thermoplasmataceae	401	\N	\N	\N	\N	Thermoplasmataceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
317	4	Thermofilaceae	398	\N	\N	\N	\N	Thermofilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
318	4	Thermococcaceae	365	\N	\N	\N	\N	Thermococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
319	4	Sulfolobaceae	343	\N	\N	\N	\N	Sulfolobaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
320	4	Pyrodictiaceae	340	\N	\N	\N	\N	Pyrodictiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
321	4	Picrophilaceae	336	\N	\N	\N	\N	Picrophilaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
322	4	Methanothermaceae	333	\N	\N	\N	\N	Methanothermaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
323	4	Methanosarcinaceae	300	\N	\N	\N	\N	Methanosarcinaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
324	4	Methanosaetaceae	296	\N	\N	\N	\N	Methanosaetaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
325	4	Methanoregulaceae	287	\N	\N	\N	\N	Methanoregulaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
326	4	Methanopyraceae	284	\N	\N	\N	\N	Methanopyraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
327	4	Methanomicrobia	281	\N	\N	\N	\N	Methanomicrobia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
328	4	Methanomicrobiales	277	\N	\N	\N	\N	Methanomicrobiales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
329	4	Methanomicrobiaceae	253	\N	\N	\N	\N	Methanomicrobiaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
330	4	Methanocorpusculaceae	249	\N	\N	\N	\N	Methanocorpusculaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
331	4	Methanococcaceae	243	\N	\N	\N	\N	Methanococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
332	4	Methanocellaceae	238	\N	\N	\N	\N	Methanocellaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
333	4	Methanocaldococcaceae	228	\N	\N	\N	\N	Methanocaldococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
334	4	Methanobacteriaceae	199	\N	\N	\N	\N	Methanobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
335	4	Halobacteriaceae	42	\N	\N	\N	\N	Halobacteriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
336	4	Ferroplasmaceae	37	\N	\N	\N	\N	Ferroplasmaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
337	4	Desulfurococcaceae	21	\N	\N	\N	\N	Desulfurococcaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
338	4	Caldisphaeraceae	18	\N	\N	\N	\N	Caldisphaeraceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
339	4	Archaeoglobaceae	6	\N	\N	\N	\N	Archaeoglobaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
340	4	Acidilobaceae	2	\N	\N	\N	\N	Acidilobaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
341	5	Stramenopiles	82900	\N	\N	\N	\N	Stramenopiles	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
342	5	Rhizaria	80819	\N	\N	\N	\N	Rhizaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
343	5	Alveolata	11832	\N	\N	\N	\N	Alveolata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
344	6	Eukaryota D3	85359	\N	\N	\N	\N	Eukaryota D3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
345	6	Eukaryota D2	85356	\N	\N	\N	\N	Eukaryota D2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
346	6	Eukaryota D1	85353	\N	\N	\N	\N	Eukaryota D1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
347	7	S25 1200	86686	\N	\N	\N	\N	S25 1200	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
348	7	Rappemonads	86662	\N	\N	\N	\N	Rappemonads	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
349	7	Katablepharidida X	85455	\N	\N	\N	\N	Katablepharidida X<Orphans	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
350	7	Telonemida	80807	\N	\N	\N	\N	Telonemida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
351	7	Rigifilida	80797	\N	\N	\N	\N	Rigifilida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
352	7	Planomonadida	80763	\N	\N	\N	\N	Planomonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
353	7	Picomonadida	80757	\N	\N	\N	\N	Picomonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
354	7	Palpitomonadida	80753	\N	\N	\N	\N	Palpitomonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
355	7	Microhelida	80745	\N	\N	\N	\N	Microhelida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
356	7	Mantamonadida	80740	\N	\N	\N	\N	Mantamonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
357	7	Katablepharidida	80697	\N	\N	\N	\N	Katablepharidida<Orphans<Eukaryota<living	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
358	7	Haptophyta	80426	\N	\N	\N	\N	Haptophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
359	7	Eukaryota U9	80419	\N	\N	\N	\N	Eukaryota U9	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
360	7	Eukaryota U8	80416	\N	\N	\N	\N	Eukaryota U8	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
361	7	Eukaryota U7	80413	\N	\N	\N	\N	Eukaryota U7	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
362	7	Eukaryota U6	80408	\N	\N	\N	\N	Eukaryota U6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
363	7	Eukaryota U5	80393	\N	\N	\N	\N	Eukaryota U5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
364	7	Eukaryota U4	80386	\N	\N	\N	\N	Eukaryota U4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
365	7	Eukaryota U3	80383	\N	\N	\N	\N	Eukaryota U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
366	7	Eukaryota U2	80378	\N	\N	\N	\N	Eukaryota U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
367	7	Eukaryota U1	80375	\N	\N	\N	\N	Eukaryota U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
368	7	Eukaryota U17	80370	\N	\N	\N	\N	Eukaryota U17	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
369	7	Eukaryota U16	80367	\N	\N	\N	\N	Eukaryota U16	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
370	7	Eukaryota U15	80364	\N	\N	\N	\N	Eukaryota U15	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
371	7	Eukaryota U14	80361	\N	\N	\N	\N	Eukaryota U14	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
372	7	Eukaryota U12	80358	\N	\N	\N	\N	Eukaryota U12	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
373	7	Eukaryota U11	80355	\N	\N	\N	\N	Eukaryota U11	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
374	7	Eukaryota U10	80352	\N	\N	\N	\N	Eukaryota U10	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
375	7	Diphylleida	80346	\N	\N	\N	\N	Diphylleida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
376	7	Cryptophyta	80191	\N	\N	\N	\N	Cryptophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
377	7	Centrohelida	80042	\N	\N	\N	\N	Centrohelida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
378	7	Breviatida	79994	\N	\N	\N	\N	Breviatida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
379	7	Apusomonadida	79923	\N	\N	\N	\N	Apusomonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
380	7	Katablepharidida	29362	\N	\N	\N	\N	Katablepharidida<Orphans<Eukaryota<living	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
381	8	Opisthokonta X	79914	\N	\N	\N	\N	Opisthokonta X<Opisthokonta	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
383	8	Holomycota	29368	\N	\N	\N	\N	Holomycota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
384	9	Metamonada	29018	\N	\N	\N	\N	Metamonada	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
385	9	Malawimonadidae	29014	\N	\N	\N	\N	Malawimonadidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
386	9	Discoba	28401	\N	\N	\N	\N	Discoba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
387	10	Eukaryota X sp.	28399	\N	\N	\N	\N	Eukaryota X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
388	11	uncultured rumen protozoa	28393	\N	\N	\N	\N	uncultured rumen protozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
389	11	uncultured marine eukaryote	28392	\N	\N	\N	\N	uncultured marine eukaryote	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
390	11	uncultured eukaryote	28391	\N	\N	\N	\N	uncultured eukaryote	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
391	12	Viridiplantae	20311	\N	\N	\N	\N	Viridiplantae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
392	12	Rhodophyta	18860	\N	\N	\N	\N	Rhodophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
393	12	Glaucophyta	18851	\N	\N	\N	\N	Glaucophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
394	13	Trichosida	18846	\N	\N	\N	\N	Trichosida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
395	13	Lobosa	18396	\N	\N	\N	\N	Lobosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
396	13	Conosa	17773	\N	\N	\N	\N	Conosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
397	13	Amoebozoa U1	17766	\N	\N	\N	\N	Amoebozoa U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
398	14	Xylella	11828	\N	\N	\N	\N	Xylella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
399	14	Xanthomonas	11800	\N	\N	\N	\N	Xanthomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
400	14	Wohlfahrtiimonas	11798	\N	\N	\N	\N	Wohlfahrtiimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
401	14	Thermomonas	11792	\N	\N	\N	\N	Thermomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
402	14	Stenotrophomonas	11780	\N	\N	\N	\N	Stenotrophomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
403	14	Rhodanobacter	11770	\N	\N	\N	\N	Rhodanobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
404	14	Pseudoxanthomonas	11757	\N	\N	\N	\N	Pseudoxanthomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
405	14	Panacagrimonas	11755	\N	\N	\N	\N	Panacagrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
406	14	Lysobacter	11730	\N	\N	\N	\N	Lysobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
407	14	Luteimonas	11722	\N	\N	\N	\N	Luteimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
408	14	Luteibacter	11718	\N	\N	\N	\N	Luteibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
409	14	Ignatzschineria	11714	\N	\N	\N	\N	Ignatzschineria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
410	14	Fulvimonas	11712	\N	\N	\N	\N	Fulvimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
411	14	Frateuria	11709	\N	\N	\N	\N	Frateuria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
412	14	Dyella	11701	\N	\N	\N	\N	Dyella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
413	14	Dokdonella	11696	\N	\N	\N	\N	Dokdonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
414	14	Arenimonas	11689	\N	\N	\N	\N	Arenimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
415	14	Aquimonas	11687	\N	\N	\N	\N	Aquimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
416	15	Xanthobacter	11679	\N	\N	\N	\N	Xanthobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
417	15	Starkeya	11676	\N	\N	\N	\N	Starkeya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
418	15	Pseudoxanthobacter	11674	\N	\N	\N	\N	Pseudoxanthobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
419	15	Pseudolabrys	11672	\N	\N	\N	\N	Pseudolabrys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
420	15	Labrys	11664	\N	\N	\N	\N	Labrys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
421	15	Azorhizobium	11661	\N	\N	\N	\N	Azorhizobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
422	15	Ancylobacter	11654	\N	\N	\N	\N	Ancylobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
423	16	Waddlia	11651	\N	\N	\N	\N	Waddlia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
424	17	Victivallis	11648	\N	\N	\N	\N	Victivallis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
425	18	Vibrio	11580	\N	\N	\N	\N	Vibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
426	18	Salinivibrio	11573	\N	\N	\N	\N	Salinivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
427	18	Photobacterium	11552	\N	\N	\N	\N	Photobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
428	18	Grimontia	11550	\N	\N	\N	\N	Grimontia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
429	18	Enterovibrio	11545	\N	\N	\N	\N	Enterovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
430	18	Aliivibrio	11539	\N	\N	\N	\N	Aliivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
431	19	Verrucomicrobium	11536	\N	\N	\N	\N	Verrucomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
432	19	Roseibacillus	11532	\N	\N	\N	\N	Roseibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
433	19	Prosthecobacter	11526	\N	\N	\N	\N	Prosthecobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
434	19	Persicirhabdus	11524	\N	\N	\N	\N	Persicirhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
435	19	Luteolibacter	11521	\N	\N	\N	\N	Luteolibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
436	19	Haloferula	11515	\N	\N	\N	\N	Haloferula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
437	20	Zymophilus	11512	\N	\N	\N	\N	Zymophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
438	20	Veillonella	11505	\N	\N	\N	\N	Veillonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
439	20	Thermosinus	11503	\N	\N	\N	\N	Thermosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
440	20	Sporomusa	11494	\N	\N	\N	\N	Sporomusa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
441	20	Sporolituus	11492	\N	\N	\N	\N	Sporolituus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
442	20	Selenomonas	11481	\N	\N	\N	\N	Selenomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
443	20	Schwartzia	11479	\N	\N	\N	\N	Schwartzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
444	20	Propionispora	11476	\N	\N	\N	\N	Propionispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
445	20	Propionispira	11474	\N	\N	\N	\N	Propionispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
446	20	Pelosinus	11470	\N	\N	\N	\N	Pelosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
447	20	Pectinatus	11466	\N	\N	\N	\N	Pectinatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
448	20	Mitsuokella	11463	\N	\N	\N	\N	Mitsuokella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
449	20	Megasphaera	11459	\N	\N	\N	\N	Megasphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
450	20	Megamonas	11456	\N	\N	\N	\N	Megamonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
451	20	Dialister	11451	\N	\N	\N	\N	Dialister	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
452	20	Dendrosporobacter	11449	\N	\N	\N	\N	Dendrosporobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
453	20	Centipeda	11447	\N	\N	\N	\N	Centipeda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
454	20	Anaerovibrio	11445	\N	\N	\N	\N	Anaerovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
455	20	Anaerosinus	11443	\N	\N	\N	\N	Anaerosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
456	20	Anaeromusa	11441	\N	\N	\N	\N	Anaeromusa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
457	20	Anaeroglobus	11439	\N	\N	\N	\N	Anaeroglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
458	20	Anaeroarcus	11437	\N	\N	\N	\N	Anaeroarcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
459	20	Allisonella	11435	\N	\N	\N	\N	Allisonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
460	20	Acetonema	11433	\N	\N	\N	\N	Acetonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
461	21	Tsukamurella	11420	\N	\N	\N	\N	Tsukamurella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
462	22	Truepera	11417	\N	\N	\N	\N	Truepera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
463	23	Fangia	11414	\N	\N	\N	\N	Fangia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
464	23	Caedibacter	11411	\N	\N	\N	\N	Caedibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
465	24	Thiothrix	11401	\N	\N	\N	\N	Thiothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
466	24	Leucothrix	11399	\N	\N	\N	\N	Leucothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
467	24	Cocleimonas	11397	\N	\N	\N	\N	Cocleimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
468	24	Beggiatoa	11395	\N	\N	\N	\N	Beggiatoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
469	25	Thioprofundum	11391	\N	\N	\N	\N	Thioprofundum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
470	25	Thioalkalispira	11389	\N	\N	\N	\N	Thioalkalispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
471	26	Thermotoga	11378	\N	\N	\N	\N	Thermotoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
472	26	Thermosipho	11372	\N	\N	\N	\N	Thermosipho	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
473	26	Thermococcoides	11370	\N	\N	\N	\N	Thermococcoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
474	26	Petrotoga	11363	\N	\N	\N	\N	Petrotoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
475	26	Oceanotoga	11361	\N	\N	\N	\N	Oceanotoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
476	26	Marinitoga	11357	\N	\N	\N	\N	Marinitoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
477	26	Kosmotoga	11354	\N	\N	\N	\N	Kosmotoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
478	26	Geotoga	11351	\N	\N	\N	\N	Geotoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
479	26	Fervidobacterium	11346	\N	\N	\N	\N	Fervidobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
480	26	Defluviitoga	11344	\N	\N	\N	\N	Defluviitoga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
481	27	Thermosporothrix	11341	\N	\N	\N	\N	Thermosporothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
482	28	Thermomonospora	11337	\N	\N	\N	\N	Thermomonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
483	28	Spirillospora	11334	\N	\N	\N	\N	Spirillospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
484	28	Actinomadura	11284	\N	\N	\N	\N	Actinomadura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
485	28	Actinocorallia	11276	\N	\N	\N	\N	Actinocorallia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
486	28	Actinoallomurus	11263	\N	\N	\N	\N	Actinoallomurus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
487	29	Thermomicrobium	11260	\N	\N	\N	\N	Thermomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
488	30	Thermolithobacter	11256	\N	\N	\N	\N	Thermolithobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
489	31	Thermoleophilum	11252	\N	\N	\N	\N	Thermoleophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
490	32	Thermogemmatispora	11248	\N	\N	\N	\N	Thermogemmatispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
491	33	Coprothermobacter	11244	\N	\N	\N	\N	Coprothermobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
492	34	Thermodesulfobacterium	11238	\N	\N	\N	\N	Thermodesulfobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
493	34	Thermodesulfatator	11235	\N	\N	\N	\N	Thermodesulfatator	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
494	35	Thermovorax	11232	\N	\N	\N	\N	Thermovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
495	35	Thermovenabulum	11230	\N	\N	\N	\N	Thermovenabulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
496	35	Thermosediminibacter	11228	\N	\N	\N	\N	Thermosediminibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
497	35	Thermoanaerobacterium	11220	\N	\N	\N	\N	Thermoanaerobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
498	35	Mahella	11218	\N	\N	\N	\N	Mahella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
499	35	Caldicellulosiruptor	11209	\N	\N	\N	\N	Caldicellulosiruptor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
500	35	Caldanaerovirga	11207	\N	\N	\N	\N	Caldanaerovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
501	36	Thermoanaerobacter	11188	\N	\N	\N	\N	Thermoanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
502	36	Thermanaeromonas	11186	\N	\N	\N	\N	Thermanaeromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
503	36	Thermacetogenium	11184	\N	\N	\N	\N	Thermacetogenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
504	36	Tepidanaerobacter	11182	\N	\N	\N	\N	Tepidanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
505	36	Moorella	11176	\N	\N	\N	\N	Moorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
506	36	Gelria	11174	\N	\N	\N	\N	Gelria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
507	36	Desulfovirgula	11172	\N	\N	\N	\N	Desulfovirgula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
508	36	Carboxydothermus	11167	\N	\N	\N	\N	Carboxydothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
509	36	Caloribacterium	11165	\N	\N	\N	\N	Caloribacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
510	36	Caldanaerobius	11161	\N	\N	\N	\N	Caldanaerobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
511	36	Caldanaerobacter	11156	\N	\N	\N	\N	Caldanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
512	36	Ammonifex	11153	\N	\N	\N	\N	Ammonifex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
513	37	Thermoflavimicrobium	11150	\N	\N	\N	\N	Thermoflavimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
514	37	Thermoactinomyces	11147	\N	\N	\N	\N	Thermoactinomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
515	37	Shimazuella	11145	\N	\N	\N	\N	Shimazuella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
516	37	Seinonella	11143	\N	\N	\N	\N	Seinonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
517	37	Planifilum	11139	\N	\N	\N	\N	Planifilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
518	37	Melghirimyces	11137	\N	\N	\N	\N	Melghirimyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
519	37	Mechercharimyces	11135	\N	\N	\N	\N	Mechercharimyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
520	37	Marininema	11133	\N	\N	\N	\N	Marininema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
521	37	Laceyella	11129	\N	\N	\N	\N	Laceyella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
522	37	Kroppenstedtia	11127	\N	\N	\N	\N	Kroppenstedtia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
523	37	Desmospora	11125	\N	\N	\N	\N	Desmospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
524	38	Thermithiobacillus	11122	\N	\N	\N	\N	Thermithiobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
525	39	Vulcanithermus	11119	\N	\N	\N	\N	Vulcanithermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
526	39	Thermus	11107	\N	\N	\N	\N	Thermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
527	39	Rhabdothermus	11105	\N	\N	\N	\N	Rhabdothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
528	39	Oceanithermus	11103	\N	\N	\N	\N	Oceanithermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
529	39	Meiothermus	11092	\N	\N	\N	\N	Meiothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
530	39	Marinithermus	11090	\N	\N	\N	\N	Marinithermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
531	40	Syntrophorhabdus	11087	\N	\N	\N	\N	Syntrophorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
532	41	Thermosyntropha	11083	\N	\N	\N	\N	Thermosyntropha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
533	41	Thermohydrogenium	11081	\N	\N	\N	\N	Thermohydrogenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
534	41	Syntrophothermus	11079	\N	\N	\N	\N	Syntrophothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
535	41	Syntrophomonas	11071	\N	\N	\N	\N	Syntrophomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
536	41	Pelospora	11069	\N	\N	\N	\N	Pelospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
537	41	Fervidicola	11067	\N	\N	\N	\N	Fervidicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
538	41	Dethiobacter	11065	\N	\N	\N	\N	Dethiobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
539	42	Thermodesulforhabdus	11062	\N	\N	\N	\N	Thermodesulforhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
540	42	Syntrophobacter	11057	\N	\N	\N	\N	Syntrophobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
541	42	Desulfovirga	11055	\N	\N	\N	\N	Desulfovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
542	42	Desulfosoma	11053	\N	\N	\N	\N	Desulfosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
543	42	Desulforhabdus	11051	\N	\N	\N	\N	Desulforhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
544	42	Desulfoglaeba	11049	\N	\N	\N	\N	Desulfoglaeba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
545	42	Desulfacinum	11046	\N	\N	\N	\N	Desulfacinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
546	43	Syntrophus	11041	\N	\N	\N	\N	Syntrophus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
547	43	Desulfomonile	11039	\N	\N	\N	\N	Desulfomonile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
548	43	Desulfobacca	11037	\N	\N	\N	\N	Desulfobacca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
549	44	Thermovirga	11034	\N	\N	\N	\N	Thermovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
550	44	Thermanaerovibrio	11031	\N	\N	\N	\N	Thermanaerovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
551	44	Pyramidobacter	11029	\N	\N	\N	\N	Pyramidobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
552	44	Jonquetella	11027	\N	\N	\N	\N	Jonquetella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
553	44	Dethiosulfovibrio	11021	\N	\N	\N	\N	Dethiosulfovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
554	44	Anaerobaculum	11018	\N	\N	\N	\N	Anaerobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
555	44	Aminobacterium	11015	\N	\N	\N	\N	Aminobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
556	45	Sutterella	11010	\N	\N	\N	\N	Sutterella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
557	45	Parasutterella	11007	\N	\N	\N	\N	Parasutterella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
558	46	Succinivibrio	11004	\N	\N	\N	\N	Succinivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
559	46	Succinimonas	11002	\N	\N	\N	\N	Succinimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
560	46	Succinatimonas	11000	\N	\N	\N	\N	Succinatimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
561	46	Ruminobacter	10998	\N	\N	\N	\N	Ruminobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
562	46	Anaerobiospirillum	10995	\N	\N	\N	\N	Anaerobiospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
563	47	Sinosporangium	10992	\N	\N	\N	\N	Sinosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
564	48	Thermopolyspora	10989	\N	\N	\N	\N	Thermopolyspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
565	48	Streptosporangium	10972	\N	\N	\N	\N	Streptosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
566	48	Sphaerisporangium	10964	\N	\N	\N	\N	Sphaerisporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
567	48	Planotetraspora	10959	\N	\N	\N	\N	Planotetraspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
568	48	Planomonospora	10953	\N	\N	\N	\N	Planomonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
569	48	Planobispora	10950	\N	\N	\N	\N	Planobispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
570	48	Nonomuraea	10921	\N	\N	\N	\N	Nonomuraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
571	48	Microtetraspora	10916	\N	\N	\N	\N	Microtetraspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
572	48	Microbispora	10910	\N	\N	\N	\N	Microbispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
573	48	Herbidospora	10904	\N	\N	\N	\N	Herbidospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
574	48	Acrocarpospora	10900	\N	\N	\N	\N	Acrocarpospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
575	49	Streptomyces	10370	\N	\N	\N	\N	Streptomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
576	49	Streptacidiphilus	10361	\N	\N	\N	\N	Streptacidiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
577	49	Kitasatospora	10337	\N	\N	\N	\N	Kitasatospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
578	50	Streptococcus	10266	\N	\N	\N	\N	Streptococcus<Streptococcaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
579	50	Lactovum	10264	\N	\N	\N	\N	Lactovum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
580	50	Lactococcus	10254	\N	\N	\N	\N	Lactococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
581	51	Iphinoe	10251	\N	\N	\N	\N	Iphinoe	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
582	52	Staphylococcus	10195	\N	\N	\N	\N	Staphylococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
583	52	Salinicoccus	10180	\N	\N	\N	\N	Salinicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
584	52	Nosocomiicoccus	10178	\N	\N	\N	\N	Nosocomiicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
585	52	Macrococcus	10170	\N	\N	\N	\N	Macrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
586	52	Jeotgalicoccus	10163	\N	\N	\N	\N	Jeotgalicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
587	53	Tuberibacillus	10160	\N	\N	\N	\N	Tuberibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
588	53	Sporolactobacillus	10151	\N	\N	\N	\N	Sporolactobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
589	53	Sinobaca	10149	\N	\N	\N	\N	Sinobaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
590	53	Pullulanibacillus	10147	\N	\N	\N	\N	Pullulanibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
591	54	Sporichthya	10143	\N	\N	\N	\N	Sporichthya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
592	55	Spiroplasma	10107	\N	\N	\N	\N	Spiroplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
593	56	Exilispira	10104	\N	\N	\N	\N	Exilispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
594	57	Treponema	10083	\N	\N	\N	\N	Treponema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
595	57	Spirochaeta	10064	\N	\N	\N	\N	Spirochaeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
596	57	Sphaerochaeta	10061	\N	\N	\N	\N	Sphaerochaeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
597	57	Borrelia	10051	\N	\N	\N	\N	Borrelia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
598	58	Spirillum	10047	\N	\N	\N	\N	Spirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
599	59	Zymomonas	10043	\N	\N	\N	\N	Zymomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
600	59	Stakelama	10041	\N	\N	\N	\N	Stakelama	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
601	59	Sphingosinicella	10037	\N	\N	\N	\N	Sphingosinicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
602	59	Sphingopyxis	10023	\N	\N	\N	\N	Sphingopyxis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
603	59	Sphingomonas	9958	\N	\N	\N	\N	Sphingomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
604	59	Sphingomicrobium	9956	\N	\N	\N	\N	Sphingomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
605	59	Sphingobium	9932	\N	\N	\N	\N	Sphingobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
606	59	Sandarakinorhabdus	9930	\N	\N	\N	\N	Sandarakinorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
607	59	Sandaracinobacter	9928	\N	\N	\N	\N	Sandaracinobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
608	59	Novosphingobium	9913	\N	\N	\N	\N	Novosphingobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
609	59	Blastomonas	9911	\N	\N	\N	\N	Blastomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
610	60	Fodinibius	9908	\N	\N	\N	\N	Fodinibius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
611	61	Sphingobacterium	9893	\N	\N	\N	\N	Sphingobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
612	61	Solitalea	9890	\N	\N	\N	\N	Solitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
613	61	Pseudosphingobacterium	9888	\N	\N	\N	\N	Pseudosphingobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
614	61	Pedobacter	9856	\N	\N	\N	\N	Pedobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
615	61	Parapedobacter	9852	\N	\N	\N	\N	Parapedobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
616	61	Olivibacter	9846	\N	\N	\N	\N	Olivibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
617	61	Nubsella	9844	\N	\N	\N	\N	Nubsella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
618	61	Mucilaginibacter	9834	\N	\N	\N	\N	Mucilaginibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
619	62	Sphaerobacter	9831	\N	\N	\N	\N	Sphaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
620	63	Solirubrobacter	9827	\N	\N	\N	\N	Solirubrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
621	64	Sneathiella	9823	\N	\N	\N	\N	Sneathiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
622	65	Alkanibacter	9820	\N	\N	\N	\N	Alkanibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
623	66	Simkania	9817	\N	\N	\N	\N	Simkania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
624	67	Shewanella	9760	\N	\N	\N	\N	Shewanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
625	68	Segniliparus	9756	\N	\N	\N	\N	Segniliparus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
626	69	Schleiferia	9753	\N	\N	\N	\N	Schleiferia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
627	70	Lewinella	9744	\N	\N	\N	\N	Lewinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
628	70	Haliscomenobacter	9742	\N	\N	\N	\N	Haliscomenobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
629	70	Aureispira	9740	\N	\N	\N	\N	Aureispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
630	71	Sanguibacter	9732	\N	\N	\N	\N	Sanguibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
631	72	Sandaracinus	9729	\N	\N	\N	\N	Sandaracinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
632	73	Salinisphaera	9724	\N	\N	\N	\N	Salinisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
633	74	Saccharospirillum	9719	\N	\N	\N	\N	Saccharospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
634	75	Subdoligranulum	9716	\N	\N	\N	\N	Subdoligranulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
635	75	Sporobacter	9714	\N	\N	\N	\N	Sporobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
636	75	Ruminococcus	9708	\N	\N	\N	\N	Ruminococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
637	75	Papillibacter	9706	\N	\N	\N	\N	Papillibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
638	75	Hydrogenoanaerobacterium	9704	\N	\N	\N	\N	Hydrogenoanaerobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
639	75	Fastidiosipila	9702	\N	\N	\N	\N	Fastidiosipila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
640	75	Faecalibacterium	9700	\N	\N	\N	\N	Faecalibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
641	75	Ethanoligenens	9698	\N	\N	\N	\N	Ethanoligenens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
642	75	Anaerofilum	9695	\N	\N	\N	\N	Anaerofilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
643	75	Acetivibrio	9691	\N	\N	\N	\N	Acetivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
644	75	Acetanaerobacterium	9689	\N	\N	\N	\N	Acetanaerobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
645	76	Rubrobacter	9684	\N	\N	\N	\N	Rubrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
646	77	Rubritalea	9676	\N	\N	\N	\N	Rubritalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
647	78	Ruania	9673	\N	\N	\N	\N	Ruania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
648	78	Haloactinobacterium	9671	\N	\N	\N	\N	Haloactinobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
649	79	Rikenella	9668	\N	\N	\N	\N	Rikenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
650	79	Alistipes	9662	\N	\N	\N	\N	Alistipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
651	80	Rickettsia	9641	\N	\N	\N	\N	Rickettsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
652	80	Orientia	9639	\N	\N	\N	\N	Orientia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
653	81	Salisaeta	9636	\N	\N	\N	\N	Salisaeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
654	81	Salinibacter	9632	\N	\N	\N	\N	Salinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
655	81	Rubricoccus	9630	\N	\N	\N	\N	Rubricoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
656	81	Rhodothermus	9627	\N	\N	\N	\N	Rhodothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
657	82	Reyranella	9624	\N	\N	\N	\N	Reyranella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
658	82	Elioraea	9622	\N	\N	\N	\N	Elioraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
659	83	Tistrella	9618	\N	\N	\N	\N	Tistrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
660	83	Thalassospira	9612	\N	\N	\N	\N	Thalassospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
661	83	Skermanella	9607	\N	\N	\N	\N	Skermanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
662	83	Roseospira	9603	\N	\N	\N	\N	Roseospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
663	83	Rhodovibrio	9600	\N	\N	\N	\N	Rhodovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
664	83	Rhodospirillum	9596	\N	\N	\N	\N	Rhodospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
665	83	Rhodospira	9594	\N	\N	\N	\N	Rhodospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
666	83	Rhodocista	9592	\N	\N	\N	\N	Rhodocista	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
667	83	Phaeovibrio	9590	\N	\N	\N	\N	Phaeovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
668	83	Phaeospirillum	9584	\N	\N	\N	\N	Phaeospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
669	83	Pelagibius	9582	\N	\N	\N	\N	Pelagibius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
670	83	Oceanibaculum	9579	\N	\N	\N	\N	Oceanibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
671	83	Novispirillum	9576	\N	\N	\N	\N	Novispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
672	83	Marispirillum	9574	\N	\N	\N	\N	Marispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
673	83	Magnetospirillum	9571	\N	\N	\N	\N	Magnetospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
674	83	Insolitispirillum	9568	\N	\N	\N	\N	Insolitispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
675	83	Inquilinus	9565	\N	\N	\N	\N	Inquilinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
676	83	Fodinicurvata	9562	\N	\N	\N	\N	Fodinicurvata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
677	83	Elstera	9560	\N	\N	\N	\N	Elstera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
678	83	Dongia	9558	\N	\N	\N	\N	Dongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
679	83	Desertibacter	9556	\N	\N	\N	\N	Desertibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
680	83	Defluviicoccus	9554	\N	\N	\N	\N	Defluviicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
681	83	Constrictibacter	9552	\N	\N	\N	\N	Constrictibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
682	83	Caenispirillum	9549	\N	\N	\N	\N	Caenispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
683	83	Azospirillum	9538	\N	\N	\N	\N	Azospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
684	84	Zoogloea	9532	\N	\N	\N	\N	Zoogloea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
685	84	Uliginosibacterium	9530	\N	\N	\N	\N	Uliginosibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
686	84	Thauera	9520	\N	\N	\N	\N	Thauera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
687	84	Sulfuritalea	9518	\N	\N	\N	\N	Sulfuritalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
688	84	Sterolibacterium	9516	\N	\N	\N	\N	Sterolibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
689	84	Rhodocyclus	9513	\N	\N	\N	\N	Rhodocyclus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
690	84	Quatrionicoccus	9511	\N	\N	\N	\N	Quatrionicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
691	84	Propionivibrio	9507	\N	\N	\N	\N	Propionivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
692	84	Georgfuchsia	9505	\N	\N	\N	\N	Georgfuchsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
693	84	Ferribacterium	9503	\N	\N	\N	\N	Ferribacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
694	84	Denitratisoma	9501	\N	\N	\N	\N	Denitratisoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
695	84	Dechloromonas	9497	\N	\N	\N	\N	Dechloromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
696	84	Azovibrio	9495	\N	\N	\N	\N	Azovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
697	84	Azospira	9492	\N	\N	\N	\N	Azospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
698	84	Azonexus	9488	\N	\N	\N	\N	Azonexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
699	84	Azoarcus	9480	\N	\N	\N	\N	Azoarcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
700	85	Tepidamorphus	9477	\N	\N	\N	\N	Tepidamorphus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
701	85	Rhodoligotrophos	9475	\N	\N	\N	\N	Rhodoligotrophos	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
702	85	Rhodobium	9472	\N	\N	\N	\N	Rhodobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
703	85	Parvibaculum	9469	\N	\N	\N	\N	Parvibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
704	85	Lutibaculum	9467	\N	\N	\N	\N	Lutibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
705	85	Anderseniella	9465	\N	\N	\N	\N	Anderseniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
706	85	Afifella	9462	\N	\N	\N	\N	Afifella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
707	86	Yangia	9459	\N	\N	\N	\N	Yangia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
708	86	Wenxinia	9457	\N	\N	\N	\N	Wenxinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
709	86	Vadicella	9455	\N	\N	\N	\N	Vadicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
710	86	Tropicimonas	9452	\N	\N	\N	\N	Tropicimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
711	86	Tropicibacter	9449	\N	\N	\N	\N	Tropicibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
712	86	Tranquillimonas	9447	\N	\N	\N	\N	Tranquillimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
713	86	Thioclava	9445	\N	\N	\N	\N	Thioclava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
714	86	Thalassococcus	9443	\N	\N	\N	\N	Thalassococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
715	86	Thalassobius	9438	\N	\N	\N	\N	Thalassobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
716	86	Thalassobacter	9436	\N	\N	\N	\N	Thalassobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
717	86	Tateyamaria	9434	\N	\N	\N	\N	Tateyamaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
718	86	Sulfitobacter	9424	\N	\N	\N	\N	Sulfitobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
719	86	Stappia	9421	\N	\N	\N	\N	Stappia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
720	86	Silicibacter	9419	\N	\N	\N	\N	Silicibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
721	86	Shimia	9416	\N	\N	\N	\N	Shimia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
722	86	Seohaeicola	9414	\N	\N	\N	\N	Seohaeicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
723	86	Sediminimonas	9412	\N	\N	\N	\N	Sediminimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
724	86	Salipiger	9410	\N	\N	\N	\N	Salipiger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
725	86	Salinihabitans	9408	\N	\N	\N	\N	Salinihabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
726	86	Sagittula	9406	\N	\N	\N	\N	Sagittula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
727	86	Ruegeria	9399	\N	\N	\N	\N	Ruegeria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
728	86	Rubribacterium	9397	\N	\N	\N	\N	Rubribacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
729	86	Rubellimicrobium	9393	\N	\N	\N	\N	Rubellimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
730	86	Roseovarius	9381	\N	\N	\N	\N	Roseovarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
731	86	Roseobacter	9379	\N	\N	\N	\N	Roseobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
732	86	Roseivivax	9373	\N	\N	\N	\N	Roseivivax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
733	86	Roseisalinus	9371	\N	\N	\N	\N	Roseisalinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
734	86	Roseinatronobacter	9369	\N	\N	\N	\N	Roseinatronobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
735	86	Roseicyclus	9367	\N	\N	\N	\N	Roseicyclus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
736	86	Roseicitreum	9365	\N	\N	\N	\N	Roseicitreum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
737	86	Roseibium	9362	\N	\N	\N	\N	Roseibium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
738	86	Roseibacterium	9360	\N	\N	\N	\N	Roseibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
739	86	Roseibaca	9358	\N	\N	\N	\N	Roseibaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
740	86	Rhodovulum	9345	\N	\N	\N	\N	Rhodovulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
741	86	Rhodobacter	9334	\N	\N	\N	\N	Rhodobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
742	86	Rhodobaca	9331	\N	\N	\N	\N	Rhodobaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
743	86	Pseudovibrio	9327	\N	\N	\N	\N	Pseudovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
744	86	Pseudoruegeria	9324	\N	\N	\N	\N	Pseudoruegeria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
745	86	Pseudorhodobacter	9321	\N	\N	\N	\N	Pseudorhodobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
746	86	Primorskyibacter	9319	\N	\N	\N	\N	Primorskyibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
747	86	Poseidonocella	9316	\N	\N	\N	\N	Poseidonocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
748	86	Ponticoccus	9314	\N	\N	\N	\N	Ponticoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
749	86	Pontibaca	9312	\N	\N	\N	\N	Pontibaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
750	86	Planktotalea	9310	\N	\N	\N	\N	Planktotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
751	86	Phaeobacter	9304	\N	\N	\N	\N	Phaeobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
752	86	Pelagicola	9302	\N	\N	\N	\N	Pelagicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
753	86	Pelagibaca	9300	\N	\N	\N	\N	Pelagibaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
754	86	Paracoccus	9267	\N	\N	\N	\N	Paracoccus<Rhodobacteraceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
755	86	Pannonibacter	9265	\N	\N	\N	\N	Pannonibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
756	86	Palleronia	9263	\N	\N	\N	\N	Palleronia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
757	86	Pacificibacter	9261	\N	\N	\N	\N	Pacificibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
758	86	Octadecabacter	9258	\N	\N	\N	\N	Octadecabacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
759	86	Oceanicola	9251	\N	\N	\N	\N	Oceanicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
760	86	Oceanibulbus	9249	\N	\N	\N	\N	Oceanibulbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
761	86	Nesiotobacter	9247	\N	\N	\N	\N	Nesiotobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
762	86	Nereida	9245	\N	\N	\N	\N	Nereida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
763	86	Nautella	9243	\N	\N	\N	\N	Nautella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
764	86	Methylarcula	9241	\N	\N	\N	\N	Methylarcula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
765	86	Marivita	9236	\N	\N	\N	\N	Marivita	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
766	86	Maritimibacter	9234	\N	\N	\N	\N	Maritimibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
767	86	Marinovum	9232	\N	\N	\N	\N	Marinovum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
768	86	Maribius	9229	\N	\N	\N	\N	Maribius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
769	86	Mameliella	9227	\N	\N	\N	\N	Mameliella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
770	86	Lutimaribacter	9225	\N	\N	\N	\N	Lutimaribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
771	86	Loktanella	9213	\N	\N	\N	\N	Loktanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
772	86	Litorimicrobium	9211	\N	\N	\N	\N	Litorimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
773	86	Litoreibacter	9206	\N	\N	\N	\N	Litoreibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
774	86	Lentibacter	9204	\N	\N	\N	\N	Lentibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
775	86	Leisingera	9200	\N	\N	\N	\N	Leisingera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
776	86	Labrenzia	9196	\N	\N	\N	\N	Labrenzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
777	86	Ketogulonicigenium	9193	\N	\N	\N	\N	Ketogulonicigenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
778	86	Jhaorihella	9191	\N	\N	\N	\N	Jhaorihella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
779	86	Jannaschia	9184	\N	\N	\N	\N	Jannaschia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
780	86	Hwanghaeicola	9182	\N	\N	\N	\N	Hwanghaeicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
781	86	Huaishuia	9180	\N	\N	\N	\N	Huaishuia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
782	86	Hasllibacter	9178	\N	\N	\N	\N	Hasllibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
783	86	Haematobacter	9175	\N	\N	\N	\N	Haematobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
784	86	Gemmobacter	9173	\N	\N	\N	\N	Gemmobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
785	86	Donghicola	9170	\N	\N	\N	\N	Donghicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
786	86	Citreimonas	9168	\N	\N	\N	\N	Citreimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
787	86	Citreicella	9164	\N	\N	\N	\N	Citreicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
788	86	Celeribacter	9161	\N	\N	\N	\N	Celeribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
789	86	Catellibacterium	9155	\N	\N	\N	\N	Catellibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
790	86	Antarctobacter	9153	\N	\N	\N	\N	Antarctobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
791	86	Amaricoccus	9148	\N	\N	\N	\N	Amaricoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
792	86	Albimonas	9146	\N	\N	\N	\N	Albimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
793	86	Albidovulum	9143	\N	\N	\N	\N	Albidovulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
794	86	Ahrensia	9141	\N	\N	\N	\N	Ahrensia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
795	86	Agaricicola	9139	\N	\N	\N	\N	Agaricicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
796	87	Vasilyevaea	9135	\N	\N	\N	\N	Vasilyevaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
797	87	Bauldia	9132	\N	\N	\N	\N	Bauldia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
798	87	Amorphus	9129	\N	\N	\N	\N	Amorphus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
799	88	Sinorhizobium	9126	\N	\N	\N	\N	Sinorhizobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
800	88	Shinella	9119	\N	\N	\N	\N	Shinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
801	88	Rhizobium	9071	\N	\N	\N	\N	Rhizobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
802	88	Kaistia	9064	\N	\N	\N	\N	Kaistia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
803	88	Ensifer	9050	\N	\N	\N	\N	Ensifer	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
804	89	Rarobacter	9046	\N	\N	\N	\N	Rarobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
805	90	Puniceicoccus	9043	\N	\N	\N	\N	Puniceicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
806	90	Pelagicoccus	9038	\N	\N	\N	\N	Pelagicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
807	90	Coraliomargarita	9036	\N	\N	\N	\N	Coraliomargarita	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
808	90	Cerasicoccus	9034	\N	\N	\N	\N	Cerasicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
809	91	Psychromonas	9018	\N	\N	\N	\N	Psychromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
810	92	Yuhushiella	9015	\N	\N	\N	\N	Yuhushiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
811	92	Umezawaea	9013	\N	\N	\N	\N	Umezawaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
812	92	Thermocrispum	9011	\N	\N	\N	\N	Thermocrispum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
813	92	Thermobispora	9009	\N	\N	\N	\N	Thermobispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
814	92	Streptoalloteichus	9006	\N	\N	\N	\N	Streptoalloteichus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
815	92	Sciscionella	9004	\N	\N	\N	\N	Sciscionella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
816	92	Saccharothrix	8992	\N	\N	\N	\N	Saccharothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
817	92	Saccharopolyspora	8971	\N	\N	\N	\N	Saccharopolyspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
818	92	Saccharomonospora	8961	\N	\N	\N	\N	Saccharomonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
819	92	Pseudonocardia	8923	\N	\N	\N	\N	Pseudonocardia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
820	92	Prauserella	8913	\N	\N	\N	\N	Prauserella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
821	92	Lentzea	8906	\N	\N	\N	\N	Lentzea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
822	92	Lechevalieria	8899	\N	\N	\N	\N	Lechevalieria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
823	92	Labedaea	8897	\N	\N	\N	\N	Labedaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
824	92	Kutzneria	8893	\N	\N	\N	\N	Kutzneria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
825	92	Kibdelosporangium	8889	\N	\N	\N	\N	Kibdelosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
826	92	Haloechinothrix	8887	\N	\N	\N	\N	Haloechinothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
827	92	Goodfellowiella	8885	\N	\N	\N	\N	Goodfellowiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
828	92	Crossiella	8882	\N	\N	\N	\N	Crossiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
829	92	Amycolatopsis	8829	\N	\N	\N	\N	Amycolatopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
830	92	Allokutzneria	8827	\N	\N	\N	\N	Allokutzneria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
831	92	Alloactinosynnema	8825	\N	\N	\N	\N	Alloactinosynnema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
832	92	Actinosynnema	8821	\N	\N	\N	\N	Actinosynnema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
833	92	Actinophytocola	8815	\N	\N	\N	\N	Actinophytocola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
834	92	Actinomycetospora	8804	\N	\N	\N	\N	Actinomycetospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
835	92	Actinokineospora	8791	\N	\N	\N	\N	Actinokineospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
836	92	Actinoalloteichus	8786	\N	\N	\N	\N	Actinoalloteichus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
837	93	Dasania	8783	\N	\N	\N	\N	Dasania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
838	94	Serpens	8780	\N	\N	\N	\N	Serpens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
839	94	Rugamonas	8778	\N	\N	\N	\N	Rugamonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
840	94	Rhizobacter	8775	\N	\N	\N	\N	Rhizobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
841	94	Pseudomonas	8632	\N	\N	\N	\N	Pseudomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
842	94	Cellvibrio	8624	\N	\N	\N	\N	Cellvibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
843	94	Azotobacter	8617	\N	\N	\N	\N	Azotobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
844	94	Azorhizophilus	8615	\N	\N	\N	\N	Azorhizophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
845	94	Azomonas	8612	\N	\N	\N	\N	Azomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
846	95	Psychrosphaera	8609	\N	\N	\N	\N	Psychrosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
847	95	Pseudoalteromonas	8575	\N	\N	\N	\N	Pseudoalteromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
848	95	Algicola	8572	\N	\N	\N	\N	Algicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
849	96	Cyanobacteria	8566	\N	\N	\N	\N	Cyanobacteria<Proteobacteria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
850	96	Alphaproteobacteria	8358	\N	\N	\N	\N	Alphaproteobacteria<Proteobacteria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
851	97	Tessaracoccus	8352	\N	\N	\N	\N	Tessaracoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
852	97	Propionimicrobium	8350	\N	\N	\N	\N	Propionimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
853	97	Propioniferax	8348	\N	\N	\N	\N	Propioniferax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
854	97	Propionicimonas	8346	\N	\N	\N	\N	Propionicimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
855	97	Propioniciclava	8344	\N	\N	\N	\N	Propioniciclava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
856	97	Propionicicella	8342	\N	\N	\N	\N	Propionicicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
857	97	Propionibacterium	8328	\N	\N	\N	\N	Propionibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
858	97	Micropruina	8326	\N	\N	\N	\N	Micropruina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
859	97	Microlunatus	8319	\N	\N	\N	\N	Microlunatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
860	97	Luteococcus	8316	\N	\N	\N	\N	Luteococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
861	97	Friedmanniella	8307	\N	\N	\N	\N	Friedmanniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
862	97	Brooklawnia	8305	\N	\N	\N	\N	Brooklawnia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
863	97	Auraticoccus	8303	\N	\N	\N	\N	Auraticoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
864	97	Aestuariimicrobium	8301	\N	\N	\N	\N	Aestuariimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
865	98	Xylanimonas	8298	\N	\N	\N	\N	Xylanimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
866	98	Xylanimicrobium	8296	\N	\N	\N	\N	Xylanimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
867	98	Xylanibacterium	8294	\N	\N	\N	\N	Xylanibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
868	98	Promicromonospora	8287	\N	\N	\N	\N	Promicromonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
869	98	Myceligenerans	8284	\N	\N	\N	\N	Myceligenerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
870	98	Isoptericola	8276	\N	\N	\N	\N	Isoptericola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
871	98	Cellulosimicrobium	8272	\N	\N	\N	\N	Cellulosimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
872	99	Prochlorothrix	8269	\N	\N	\N	\N	Prochlorothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
873	100	Prochlorococcus	8265	\N	\N	\N	\N	Prochlorococcus<Prochlorococcaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
874	101	Prevotella	8221	\N	\N	\N	\N	Prevotella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
875	101	Paraprevotella	8218	\N	\N	\N	\N	Paraprevotella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
876	101	Hallella	8216	\N	\N	\N	\N	Hallella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
877	102	Tannerella	8213	\N	\N	\N	\N	Tannerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
878	102	Proteiniphilum	8211	\N	\N	\N	\N	Proteiniphilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
879	102	Porphyromonas	8194	\N	\N	\N	\N	Porphyromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
880	102	Petrimonas	8192	\N	\N	\N	\N	Petrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
881	102	Parabacteroides	8186	\N	\N	\N	\N	Parabacteroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
882	102	Paludibacter	8184	\N	\N	\N	\N	Paludibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
883	102	Odoribacter	8180	\N	\N	\N	\N	Odoribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
884	102	Dysgonomonas	8175	\N	\N	\N	\N	Dysgonomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
885	102	Butyricimonas	8172	\N	\N	\N	\N	Butyricimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
886	102	Barnesiella	8169	\N	\N	\N	\N	Barnesiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
887	103	Sorangium	8166	\N	\N	\N	\N	Sorangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
888	103	Jahnella	8164	\N	\N	\N	\N	Jahnella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
889	103	Chondromyces	8162	\N	\N	\N	\N	Chondromyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
890	103	Byssovorax	8160	\N	\N	\N	\N	Byssovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
891	104	Ureibacillus	8153	\N	\N	\N	\N	Ureibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
892	104	Sporosarcina	8140	\N	\N	\N	\N	Sporosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
893	104	Planomicrobium	8131	\N	\N	\N	\N	Planomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
894	104	Planococcus	8122	\N	\N	\N	\N	Planococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
895	104	Paenisporosarcina	8119	\N	\N	\N	\N	Paenisporosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
896	104	Kurthia	8115	\N	\N	\N	\N	Kurthia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
897	104	Jeotgalibacillus	8109	\N	\N	\N	\N	Jeotgalibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
898	104	Filibacter	8107	\N	\N	\N	\N	Filibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
899	104	Chryseomicrobium	8105	\N	\N	\N	\N	Chryseomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
900	104	Caryophanon	8102	\N	\N	\N	\N	Caryophanon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
901	104	Bhargavaea	8100	\N	\N	\N	\N	Bhargavaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
902	105	Zavarzinella	8097	\N	\N	\N	\N	Zavarzinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
903	105	Singulisphaera	8094	\N	\N	\N	\N	Singulisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
904	105	Schlesneria	8092	\N	\N	\N	\N	Schlesneria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
905	105	Rhodopirellula	8090	\N	\N	\N	\N	Rhodopirellula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
906	105	Planctomyces	8086	\N	\N	\N	\N	Planctomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
907	105	Pirellula	8084	\N	\N	\N	\N	Pirellula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
908	105	Isosphaera	8082	\N	\N	\N	\N	Isosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
909	105	Gemmata	8080	\N	\N	\N	\N	Gemmata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
910	105	Blastopirellula	8078	\N	\N	\N	\N	Blastopirellula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
911	105	Aquisphaera	8076	\N	\N	\N	\N	Aquisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
912	106	Thiomicrospira	8065	\N	\N	\N	\N	Thiomicrospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
913	106	Thioalkalimicrobium	8062	\N	\N	\N	\N	Thioalkalimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
914	106	Sulfurivirga	8060	\N	\N	\N	\N	Sulfurivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
915	106	Piscirickettsia	8058	\N	\N	\N	\N	Piscirickettsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
916	106	Methylophaga	8049	\N	\N	\N	\N	Methylophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
917	106	Cycloclasticus	8047	\N	\N	\N	\N	Cycloclasticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
918	107	Pseudaminobacter	8043	\N	\N	\N	\N	Pseudaminobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
919	107	Phyllobacterium	8035	\N	\N	\N	\N	Phyllobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
920	107	Nitratireductor	8029	\N	\N	\N	\N	Nitratireductor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
921	107	Mesorhizobium	8007	\N	\N	\N	\N	Mesorhizobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
922	107	Hoeflea	8002	\N	\N	\N	\N	Hoeflea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
923	107	Chelativorans	7999	\N	\N	\N	\N	Chelativorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
924	107	Aquamicrobium	7995	\N	\N	\N	\N	Aquamicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
925	107	Aminobacter	7989	\N	\N	\N	\N	Aminobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
926	108	Phycisphaera	7986	\N	\N	\N	\N	Phycisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
927	109	Phaselicystis	7983	\N	\N	\N	\N	Phaselicystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
928	110	Tepidibacter	7978	\N	\N	\N	\N	Tepidibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
929	110	Sporacetigenium	7976	\N	\N	\N	\N	Sporacetigenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
930	110	Peptostreptococcus	7972	\N	\N	\N	\N	Peptostreptococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
931	110	Filifactor	7970	\N	\N	\N	\N	Filifactor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
932	110	Anaerosphaera	7968	\N	\N	\N	\N	Anaerosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
933	111	Thermincola	7964	\N	\N	\N	\N	Thermincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
934	111	Sporotomaculum	7961	\N	\N	\N	\N	Sporotomaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
935	111	Pelotomaculum	7955	\N	\N	\N	\N	Pelotomaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
936	111	Desulfurispora	7953	\N	\N	\N	\N	Desulfurispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
937	111	Desulfotomaculum	7933	\N	\N	\N	\N	Desulfotomaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
938	111	Desulfosporosinus	7925	\N	\N	\N	\N	Desulfosporosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
939	111	Desulfonispora	7923	\N	\N	\N	\N	Desulfonispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
940	111	Desulfitobacterium	7918	\N	\N	\N	\N	Desulfitobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
941	111	Desulfitispora	7916	\N	\N	\N	\N	Desulfitispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
942	111	Desulfitibacter	7914	\N	\N	\N	\N	Desulfitibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
943	111	Dehalobacter	7912	\N	\N	\N	\N	Dehalobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
944	111	Cryptanaerobacter	7910	\N	\N	\N	\N	Cryptanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
945	112	Patulibacter	7905	\N	\N	\N	\N	Patulibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
946	113	Volucribacter	7901	\N	\N	\N	\N	Volucribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
947	113	Phocoenobacter	7899	\N	\N	\N	\N	Phocoenobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
948	113	Pasteurella	7896	\N	\N	\N	\N	Pasteurella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
949	113	Mannheimia	7889	\N	\N	\N	\N	Mannheimia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
950	113	Lonepinella	7887	\N	\N	\N	\N	Lonepinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
951	113	Haemophilus	7880	\N	\N	\N	\N	Haemophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
952	113	Gallibacterium	7876	\N	\N	\N	\N	Gallibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
953	113	Avibacterium	7872	\N	\N	\N	\N	Avibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
954	113	Aggregatibacter	7869	\N	\N	\N	\N	Aggregatibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
955	113	Actinobacillus	7861	\N	\N	\N	\N	Actinobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
956	114	Parvularcula	7857	\N	\N	\N	\N	Parvularcula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
957	115	Parachlamydia	7854	\N	\N	\N	\N	Parachlamydia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
958	115	Neochlamydia	7852	\N	\N	\N	\N	Neochlamydia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
959	116	Thermobacillus	7848	\N	\N	\N	\N	Thermobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
960	116	Saccharibacillus	7845	\N	\N	\N	\N	Saccharibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
961	116	Paenibacillus	7721	\N	\N	\N	\N	Paenibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
962	116	Oxalophagus	7719	\N	\N	\N	\N	Oxalophagus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
963	116	Fontibacillus	7716	\N	\N	\N	\N	Fontibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
964	116	Cohnella	7700	\N	\N	\N	\N	Cohnella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
965	116	Brevibacillus	7684	\N	\N	\N	\N	Brevibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
966	116	Aneurinibacillus	7679	\N	\N	\N	\N	Aneurinibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
967	116	Ammoniphilus	7676	\N	\N	\N	\N	Ammoniphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
968	117	Undibacterium	7671	\N	\N	\N	\N	Undibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
969	117	Telluria	7668	\N	\N	\N	\N	Telluria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
970	117	Oxalobacter	7665	\N	\N	\N	\N	Oxalobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
971	117	Oxalicibacterium	7660	\N	\N	\N	\N	Oxalicibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
972	117	Massilia	7642	\N	\N	\N	\N	Massilia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
973	117	Janthinobacterium	7639	\N	\N	\N	\N	Janthinobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
974	117	Herminiimonas	7634	\N	\N	\N	\N	Herminiimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
975	117	Herbaspirillum	7619	\N	\N	\N	\N	Herbaspirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
976	117	Glaciimonas	7617	\N	\N	\N	\N	Glaciimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
977	117	Duganella	7614	\N	\N	\N	\N	Duganella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
978	117	Collimonas	7610	\N	\N	\N	\N	Collimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
979	118	Oscillibacter	7607	\N	\N	\N	\N	Oscillibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
980	119	Planktothricoides	7604	\N	\N	\N	\N	Planktothricoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
981	119	Halospirulina	7602	\N	\N	\N	\N	Halospirulina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
982	119	Crinalium	7600	\N	\N	\N	\N	Crinalium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
983	120	Opitutus	7597	\N	\N	\N	\N	Opitutus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
984	120	Alterococcus	7595	\N	\N	\N	\N	Alterococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
985	121	Oleiphilus	7592	\N	\N	\N	\N	Oleiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
986	122	Spongiispira	7589	\N	\N	\N	\N	Spongiispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
987	122	Salicola	7586	\N	\N	\N	\N	Salicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
988	123	Reinekea	7581	\N	\N	\N	\N	Reinekea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
989	123	Pseudospirillum	7579	\N	\N	\N	\N	Pseudospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
990	123	Oleispira	7577	\N	\N	\N	\N	Oleispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
991	123	Oleibacter	7575	\N	\N	\N	\N	Oleibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
992	123	Oceanospirillum	7571	\N	\N	\N	\N	Oceanospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
993	123	Oceanobacter	7569	\N	\N	\N	\N	Oceanobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
994	123	Oceaniserpentilla	7567	\N	\N	\N	\N	Oceaniserpentilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
995	123	Nitrincola	7565	\N	\N	\N	\N	Nitrincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
996	123	Neptunomonas	7561	\N	\N	\N	\N	Neptunomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
997	123	Neptuniibacter	7558	\N	\N	\N	\N	Neptuniibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
998	123	Marinospirillum	7552	\N	\N	\N	\N	Marinospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
999	123	Marinomonas	7537	\N	\N	\N	\N	Marinomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1000	123	Bermanella	7535	\N	\N	\N	\N	Bermanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1001	123	Amphritea	7532	\N	\N	\N	\N	Amphritea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1002	124	Thermobifida	7526	\N	\N	\N	\N	Thermobifida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1003	124	Streptomonospora	7520	\N	\N	\N	\N	Streptomonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1004	124	Spinactinospora	7518	\N	\N	\N	\N	Spinactinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1005	124	Salinactinospora	7516	\N	\N	\N	\N	Salinactinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1006	124	Nocardiopsis	7480	\N	\N	\N	\N	Nocardiopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1007	124	Murinocardiopsis	7478	\N	\N	\N	\N	Murinocardiopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1008	124	Marinactinospora	7476	\N	\N	\N	\N	Marinactinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1009	124	Haloactinospora	7474	\N	\N	\N	\N	Haloactinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1010	125	Thermasporomyces	7471	\N	\N	\N	\N	Thermasporomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1011	125	Pimelobacter	7469	\N	\N	\N	\N	Pimelobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1012	125	Nocardioides	7417	\N	\N	\N	\N	Nocardioides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1013	125	Marmoricola	7411	\N	\N	\N	\N	Marmoricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1014	125	Kribbella	7394	\N	\N	\N	\N	Kribbella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1015	125	Flindersiella	7392	\N	\N	\N	\N	Flindersiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1016	125	Aeromicrobium	7383	\N	\N	\N	\N	Aeromicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1017	125	Actinopolymorpha	7377	\N	\N	\N	\N	Actinopolymorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1018	126	Williamsia	7367	\N	\N	\N	\N	Williamsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1019	126	Smaragdicoccus	7365	\N	\N	\N	\N	Smaragdicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1020	126	Skermania	7363	\N	\N	\N	\N	Skermania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1021	126	Rhodococcus	7333	\N	\N	\N	\N	Rhodococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1022	126	Nocardia	7250	\N	\N	\N	\N	Nocardia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1023	126	Millisia	7248	\N	\N	\N	\N	Millisia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1024	126	Micropolyspora	7246	\N	\N	\N	\N	Micropolyspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1025	126	Gordonia	7214	\N	\N	\N	\N	Gordonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1026	127	Thermodesulfovibrio	7208	\N	\N	\N	\N	Thermodesulfovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1027	127	Nitrospira	7206	\N	\N	\N	\N	Nitrospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1028	127	Leptospirillum	7203	\N	\N	\N	\N	Leptospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1029	128	Nitrosospira	7200	\N	\N	\N	\N	Nitrosospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1030	128	Nitrosomonas	7198	\N	\N	\N	\N	Nitrosomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1031	129	Nitriliruptor	7195	\N	\N	\N	\N	Nitriliruptor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1032	130	Nevskia	7190	\N	\N	\N	\N	Nevskia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1033	130	Hydrocarboniphaga	7187	\N	\N	\N	\N	Hydrocarboniphaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1034	131	Vogesella	7181	\N	\N	\N	\N	Vogesella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1035	131	Vitreoscilla	7178	\N	\N	\N	\N	Vitreoscilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1036	131	Uruburuella	7176	\N	\N	\N	\N	Uruburuella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1037	131	Stenoxybacter	7174	\N	\N	\N	\N	Stenoxybacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1038	131	Simonsiella	7172	\N	\N	\N	\N	Simonsiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1039	131	Silvimonas	7168	\N	\N	\N	\N	Silvimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1040	131	Pseudogulbenkiania	7166	\N	\N	\N	\N	Pseudogulbenkiania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1041	131	Paludibacterium	7164	\N	\N	\N	\N	Paludibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1042	131	Neisseria	7151	\N	\N	\N	\N	Neisseria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1043	131	Microvirgula	7149	\N	\N	\N	\N	Microvirgula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1044	131	Leeia	7147	\N	\N	\N	\N	Leeia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1045	131	Laribacter	7145	\N	\N	\N	\N	Laribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1046	131	Kingella	7141	\N	\N	\N	\N	Kingella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1047	131	Jeongeupia	7139	\N	\N	\N	\N	Jeongeupia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1048	131	Iodobacter	7137	\N	\N	\N	\N	Iodobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1049	131	Gulbenkiania	7134	\N	\N	\N	\N	Gulbenkiania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1050	131	Formivibrio	7132	\N	\N	\N	\N	Formivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1051	131	Eikenella	7130	\N	\N	\N	\N	Eikenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1052	131	Deefgea	7127	\N	\N	\N	\N	Deefgea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1053	131	Conchiformibius	7124	\N	\N	\N	\N	Conchiformibius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1054	131	Chromobacterium	7119	\N	\N	\N	\N	Chromobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1055	131	Chitiniphilus	7117	\N	\N	\N	\N	Chitiniphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1056	131	Chitinilyticum	7114	\N	\N	\N	\N	Chitinilyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1057	131	Chitinibacter	7111	\N	\N	\N	\N	Chitinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1058	131	Bergeriella	7109	\N	\N	\N	\N	Bergeriella<Neisseriaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
1059	131	Aquitalea	7106	\N	\N	\N	\N	Aquitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1060	131	Aquaspirillum	7101	\N	\N	\N	\N	Aquaspirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1061	131	Andreprevotia	7098	\N	\N	\N	\N	Andreprevotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1062	131	Alysiella	7095	\N	\N	\N	\N	Alysiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1063	132	Thioreductor	7092	\N	\N	\N	\N	Thioreductor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1064	132	Nitratifractor	7090	\N	\N	\N	\N	Nitratifractor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1065	132	Nautilia	7086	\N	\N	\N	\N	Nautilia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1066	132	Lebetimonas	7084	\N	\N	\N	\N	Lebetimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1067	132	Caminibacter	7081	\N	\N	\N	\N	Caminibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1068	133	Natranaerobius	7077	\N	\N	\N	\N	Natranaerobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1069	134	Plesiocystis	7074	\N	\N	\N	\N	Plesiocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1070	134	Nannocystis	7071	\N	\N	\N	\N	Nannocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1071	134	Enhygromyxa	7069	\N	\N	\N	\N	Enhygromyxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1072	135	Saxeibacter	7066	\N	\N	\N	\N	Saxeibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1073	135	Nakamurella	7064	\N	\N	\N	\N	Nakamurella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1074	135	Humicoccus	7062	\N	\N	\N	\N	Humicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1075	136	Pyxidicoccus	7059	\N	\N	\N	\N	Pyxidicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1076	136	Myxococcus	7055	\N	\N	\N	\N	Myxococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1077	136	Corallococcus	7051	\N	\N	\N	\N	Corallococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1078	137	Ureaplasma	7042	\N	\N	\N	\N	Ureaplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1079	137	Mycoplasma	6935	\N	\N	\N	\N	Mycoplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1080	138	Mycobacterium	6792	\N	\N	\N	\N	Mycobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1081	138	Amycolicicoccus	6790	\N	\N	\N	\N	Amycolicicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1082	139	Paramoritella	6787	\N	\N	\N	\N	Paramoritella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1083	139	Moritella	6779	\N	\N	\N	\N	Moritella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1084	140	Psychrobacter	6747	\N	\N	\N	\N	Psychrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1085	140	Perlucidibaca	6745	\N	\N	\N	\N	Perlucidibaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1086	140	Paraperlucidibaca	6743	\N	\N	\N	\N	Paraperlucidibaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1087	140	Moraxella	6727	\N	\N	\N	\N	Moraxella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1088	140	Enhydrobacter	6725	\N	\N	\N	\N	Enhydrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1089	140	Alkanindiges	6723	\N	\N	\N	\N	Alkanindiges	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1090	140	Acinetobacter	6707	\N	\N	\N	\N	Acinetobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1091	141	Virgisporangium	6702	\N	\N	\N	\N	Virgisporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1092	141	Verrucosispora	6697	\N	\N	\N	\N	Verrucosispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1093	141	Spirilliplanes	6695	\N	\N	\N	\N	Spirilliplanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1094	141	Salinispora	6692	\N	\N	\N	\N	Salinispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1095	141	Rugosimonospora	6689	\N	\N	\N	\N	Rugosimonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1096	141	Pseudosporangium	6687	\N	\N	\N	\N	Pseudosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1097	141	Polymorphospora	6685	\N	\N	\N	\N	Polymorphospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1098	141	Plantactinospora	6683	\N	\N	\N	\N	Plantactinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1099	141	Planosporangium	6680	\N	\N	\N	\N	Planosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1100	141	Pilimelia	6676	\N	\N	\N	\N	Pilimelia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1101	141	Phytomonospora	6674	\N	\N	\N	\N	Phytomonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1102	141	Phytohabitans	6672	\N	\N	\N	\N	Phytohabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1103	141	Micromonospora	6628	\N	\N	\N	\N	Micromonospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1104	141	Luedemannella	6625	\N	\N	\N	\N	Luedemannella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1105	141	Longispora	6622	\N	\N	\N	\N	Longispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1106	141	Krasilnikovia	6620	\N	\N	\N	\N	Krasilnikovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1107	141	Jishengella	6618	\N	\N	\N	\N	Jishengella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1108	141	Hamadaea	6616	\N	\N	\N	\N	Hamadaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1109	141	Dactylosporangium	6603	\N	\N	\N	\N	Dactylosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1110	141	Couchioplanes	6600	\N	\N	\N	\N	Couchioplanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1111	141	Catenuloplanes	6592	\N	\N	\N	\N	Catenuloplanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1112	141	Catelliglobosispora	6590	\N	\N	\N	\N	Catelliglobosispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1113	141	Catellatospora	6584	\N	\N	\N	\N	Catellatospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1114	141	Asanoa	6579	\N	\N	\N	\N	Asanoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1115	141	Allocatelliglobosispora	6577	\N	\N	\N	\N	Allocatelliglobosispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1116	141	Actinoplanes	6546	\N	\N	\N	\N	Actinoplanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1117	141	Actinocatenispora	6542	\N	\N	\N	\N	Actinocatenispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1118	141	Actinaurispora	6540	\N	\N	\N	\N	Actinaurispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1119	142	Luteimicrobium	6537	\N	\N	\N	\N	Luteimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1120	142	Koreibacter	6535	\N	\N	\N	\N	Koreibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1121	143	Zhihengliuella	6530	\N	\N	\N	\N	Zhihengliuella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1122	143	Yaniella	6526	\N	\N	\N	\N	Yaniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1123	143	Sinomonas	6521	\N	\N	\N	\N	Sinomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1124	143	Rothia	6515	\N	\N	\N	\N	Rothia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1125	143	Renibacterium	6513	\N	\N	\N	\N	Renibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1126	143	Nesterenkonia	6501	\N	\N	\N	\N	Nesterenkonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1127	143	Micrococcus	6492	\N	\N	\N	\N	Micrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1128	143	Kocuria	6474	\N	\N	\N	\N	Kocuria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1129	143	Citricoccus	6468	\N	\N	\N	\N	Citricoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1130	143	Auritidibacter	6466	\N	\N	\N	\N	Auritidibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1131	143	Arthrobacter	6407	\N	\N	\N	\N	Arthrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1132	143	Acaricomes	6405	\N	\N	\N	\N	Acaricomes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1133	144	Zimmermannella	6401	\N	\N	\N	\N	Zimmermannella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1134	144	Yonghaparkia	6399	\N	\N	\N	\N	Yonghaparkia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1135	144	Subtercola	6396	\N	\N	\N	\N	Subtercola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1136	144	Schumannella	6394	\N	\N	\N	\N	Schumannella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1137	144	Salinibacterium	6391	\N	\N	\N	\N	Salinibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1138	144	Rhodoglobus	6388	\N	\N	\N	\N	Rhodoglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1139	144	Rathayibacter	6382	\N	\N	\N	\N	Rathayibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1140	144	Pseudoclavibacter	6378	\N	\N	\N	\N	Pseudoclavibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1141	144	Plantibacter	6375	\N	\N	\N	\N	Plantibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1142	144	Phycicola	6373	\N	\N	\N	\N	Phycicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1143	144	Okibacterium	6371	\N	\N	\N	\N	Okibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1144	144	Mycetocola	6366	\N	\N	\N	\N	Mycetocola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1145	144	Microterricola	6364	\N	\N	\N	\N	Microterricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1146	144	Microcella	6361	\N	\N	\N	\N	Microcella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1147	144	Microbacterium	6288	\N	\N	\N	\N	Microbacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1148	144	Marisediminicola	6286	\N	\N	\N	\N	Marisediminicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1149	144	Leucobacter	6269	\N	\N	\N	\N	Leucobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1150	144	Leifsonia	6256	\N	\N	\N	\N	Leifsonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1151	144	Labedella	6254	\N	\N	\N	\N	Labedella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1152	144	Klugiella	6252	\N	\N	\N	\N	Klugiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1153	144	Humibacter	6250	\N	\N	\N	\N	Humibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1154	144	Herbiconiux	6245	\N	\N	\N	\N	Herbiconiux	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1155	144	Gulosibacter	6242	\N	\N	\N	\N	Gulosibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1156	144	Glaciibacter	6240	\N	\N	\N	\N	Glaciibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1157	144	Frondihabitans	6236	\N	\N	\N	\N	Frondihabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1158	144	Frigoribacterium	6233	\N	\N	\N	\N	Frigoribacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1159	144	Curtobacterium	6224	\N	\N	\N	\N	Curtobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1160	144	Cryobacterium	6217	\N	\N	\N	\N	Cryobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1161	144	Clavibacter	6211	\N	\N	\N	\N	Clavibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1162	144	Chryseoglobus	6209	\N	\N	\N	\N	Chryseoglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1163	144	Amnibacterium	6207	\N	\N	\N	\N	Amnibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1164	144	Agromyces	6184	\N	\N	\N	\N	Agromyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1165	144	Agrococcus	6174	\N	\N	\N	\N	Agrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1166	144	Agreia	6171	\N	\N	\N	\N	Agreia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1167	145	Methylovorus	6167	\N	\N	\N	\N	Methylovorus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1168	145	Methylotenera	6165	\N	\N	\N	\N	Methylotenera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1169	145	Methylophilus	6158	\N	\N	\N	\N	Methylophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1170	145	Methylobacillus	6156	\N	\N	\N	\N	Methylobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1171	146	Terasakiella	6153	\N	\N	\N	\N	Terasakiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1172	146	Pleomorphomonas	6150	\N	\N	\N	\N	Pleomorphomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1173	146	Methylosinus	6147	\N	\N	\N	\N	Methylosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1174	146	Methylopila	6145	\N	\N	\N	\N	Methylopila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1175	146	Methylocystis	6139	\N	\N	\N	\N	Methylocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1176	146	Hansschlegelia	6136	\N	\N	\N	\N	Hansschlegelia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1177	146	Albibacter	6134	\N	\N	\N	\N	Albibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1178	147	Methylovulum	6131	\N	\N	\N	\N	Methylovulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1179	147	Methylothermus	6128	\N	\N	\N	\N	Methylothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1180	147	Methylosphaera	6126	\N	\N	\N	\N	Methylosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1181	147	Methylosoma	6124	\N	\N	\N	\N	Methylosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1182	147	Methylosarcina	6120	\N	\N	\N	\N	Methylosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1183	147	Methylomonas	6114	\N	\N	\N	\N	Methylomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1184	147	Methylomicrobium	6106	\N	\N	\N	\N	Methylomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1185	147	Methylohalobius	6104	\N	\N	\N	\N	Methylohalobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1186	147	Methylogaea	6102	\N	\N	\N	\N	Methylogaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1187	147	Methylococcus	6099	\N	\N	\N	\N	Methylococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1188	147	Methylocaldum	6095	\N	\N	\N	\N	Methylocaldum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1189	147	Methylobacter	6089	\N	\N	\N	\N	Methylobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1190	148	Microvirga	6082	\N	\N	\N	\N	Microvirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1191	148	Methylobacterium	6045	\N	\N	\N	\N	Methylobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1192	148	Meganema	6043	\N	\N	\N	\N	Meganema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1193	149	Mariprofundus	6040	\N	\N	\N	\N	Mariprofundus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1194	150	Natronoflexus	6037	\N	\N	\N	\N	Natronoflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1195	150	Marinilabilia	6035	\N	\N	\N	\N	Marinilabilia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1196	150	Mangroviflexus	6033	\N	\N	\N	\N	Mangroviflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1197	150	Geofilum	6031	\N	\N	\N	\N	Geofilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1198	150	Anaerophaga	6029	\N	\N	\N	\N	Anaerophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1199	150	Alkaliflexus	6027	\N	\N	\N	\N	Alkaliflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1200	151	Litoricola	6023	\N	\N	\N	\N	Litoricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1201	152	Listeria	6013	\N	\N	\N	\N	Listeria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1202	152	Brochothrix	6011	\N	\N	\N	\N	Brochothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1203	153	Weissella	5995	\N	\N	\N	\N	Weissella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1204	153	Oenococcus	5992	\N	\N	\N	\N	Oenococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1205	153	Leuconostoc	5976	\N	\N	\N	\N	Leuconostoc	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1206	153	Fructobacillus	5970	\N	\N	\N	\N	Fructobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1207	154	Streptobacillus	5967	\N	\N	\N	\N	Streptobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1208	154	Sebaldella	5965	\N	\N	\N	\N	Sebaldella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1209	154	Leptotrichia	5958	\N	\N	\N	\N	Leptotrichia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1210	155	Turneriella	5955	\N	\N	\N	\N	Turneriella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1211	155	Leptospira	5942	\N	\N	\N	\N	Leptospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1212	155	Leptonema	5940	\N	\N	\N	\N	Leptonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1213	156	Lentisphaera	5937	\N	\N	\N	\N	Lentisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1214	157	Legionella	5898	\N	\N	\N	\N	Legionella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1215	158	Sharpea	5895	\N	\N	\N	\N	Sharpea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1216	158	Pediococcus	5881	\N	\N	\N	\N	Pediococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1217	158	Paralactobacillus	5879	\N	\N	\N	\N	Paralactobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1218	158	Lactobacillus	5731	\N	\N	\N	\N	Lactobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1219	159	Syntrophococcus	5728	\N	\N	\N	\N	Syntrophococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1220	159	Sporobacterium	5726	\N	\N	\N	\N	Sporobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1221	159	Shuttleworthia	5724	\N	\N	\N	\N	Shuttleworthia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1222	159	Roseburia	5718	\N	\N	\N	\N	Roseburia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1223	159	Robinsoniella	5716	\N	\N	\N	\N	Robinsoniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1224	159	Pseudobutyrivibrio	5713	\N	\N	\N	\N	Pseudobutyrivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1225	159	Parasporobacterium	5711	\N	\N	\N	\N	Parasporobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1226	159	Marvinbryantia	5709	\N	\N	\N	\N	Marvinbryantia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1227	159	Lachnospira	5707	\N	\N	\N	\N	Lachnospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1228	159	Lachnobacterium	5705	\N	\N	\N	\N	Lachnobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1229	159	Johnsonella	5703	\N	\N	\N	\N	Johnsonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1230	159	Hespellia	5700	\N	\N	\N	\N	Hespellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1231	159	Dorea	5698	\N	\N	\N	\N	Dorea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1232	159	Coprococcus	5695	\N	\N	\N	\N	Coprococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1233	159	Cellulosilyticum	5692	\N	\N	\N	\N	Cellulosilyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1234	159	Catonella	5690	\N	\N	\N	\N	Catonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1235	159	Butyrivibrio	5685	\N	\N	\N	\N	Butyrivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1236	159	Anaerostipes	5683	\N	\N	\N	\N	Anaerostipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1237	159	Acetitomaculum	5681	\N	\N	\N	\N	Acetitomaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1238	160	Ktedonobacter	5678	\N	\N	\N	\N	Ktedonobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1239	161	Kordiimonas	5674	\N	\N	\N	\N	Kordiimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1240	162	Kofleria	5671	\N	\N	\N	\N	Kofleria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1241	163	Quadrisphaera	5668	\N	\N	\N	\N	Quadrisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1242	163	Pseudokineococcus	5666	\N	\N	\N	\N	Pseudokineococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1243	163	Kineosporia	5659	\N	\N	\N	\N	Kineosporia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1244	163	Kineococcus	5656	\N	\N	\N	\N	Kineococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1245	163	Angustibacter	5654	\N	\N	\N	\N	Angustibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1246	164	Kiloniella	5651	\N	\N	\N	\N	Kiloniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1247	165	Jonesia	5647	\N	\N	\N	\N	Jonesia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1248	166	Jiangella	5641	\N	\N	\N	\N	Jiangella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1249	166	Haloactinopolyspora	5639	\N	\N	\N	\N	Haloactinopolyspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1250	167	Tetrasphaera	5629	\N	\N	\N	\N	Tetrasphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1251	167	Terracoccus	5627	\N	\N	\N	\N	Terracoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1252	167	Terrabacter	5618	\N	\N	\N	\N	Terrabacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1253	167	Serinicoccus	5614	\N	\N	\N	\N	Serinicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1254	167	Phycicoccus	5607	\N	\N	\N	\N	Phycicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1255	167	Oryzihumus	5605	\N	\N	\N	\N	Oryzihumus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1256	167	Ornithinimicrobium	5602	\N	\N	\N	\N	Ornithinimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1257	167	Ornithinicoccus	5600	\N	\N	\N	\N	Ornithinicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1258	167	Ornithinibacter	5598	\N	\N	\N	\N	Ornithinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1259	167	Marihabitans	5596	\N	\N	\N	\N	Marihabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1260	167	Lapillicoccus	5594	\N	\N	\N	\N	Lapillicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1261	167	Kribbia	5592	\N	\N	\N	\N	Kribbia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1262	167	Knoellia	5586	\N	\N	\N	\N	Knoellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1263	167	Janibacter	5579	\N	\N	\N	\N	Janibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1264	167	Intrasporangium	5574	\N	\N	\N	\N	Intrasporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1265	167	Humibacillus	5572	\N	\N	\N	\N	Humibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1266	167	Fodinibacter	5570	\N	\N	\N	\N	Fodinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1267	167	Arsenicicoccus	5567	\N	\N	\N	\N	Arsenicicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1268	167	Aquipuribacter	5565	\N	\N	\N	\N	Aquipuribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1269	168	Ignavibacterium	5562	\N	\N	\N	\N	Ignavibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1270	169	Pseudidiomarina	5558	\N	\N	\N	\N	Pseudidiomarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1271	169	Idiomarina	5539	\N	\N	\N	\N	Idiomarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1272	169	Aliidiomarina	5537	\N	\N	\N	\N	Aliidiomarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1273	170	Iamia	5534	\N	\N	\N	\N	Iamia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1274	171	Woodsholea	5531	\N	\N	\N	\N	Woodsholea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1275	171	Robiginitomaculum	5529	\N	\N	\N	\N	Robiginitomaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1276	171	Ponticaulis	5527	\N	\N	\N	\N	Ponticaulis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1277	171	Oceanicaulis	5525	\N	\N	\N	\N	Oceanicaulis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1278	171	Maricaulis	5519	\N	\N	\N	\N	Maricaulis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1279	171	Litorimonas	5517	\N	\N	\N	\N	Litorimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1280	171	Hyphomonas	5514	\N	\N	\N	\N	Hyphomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1281	171	Hirschia	5511	\N	\N	\N	\N	Hirschia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1282	171	Henriciella	5507	\N	\N	\N	\N	Henriciella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1283	171	Hellea	5505	\N	\N	\N	\N	Hellea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1284	172	Rhodoplanes	5499	\N	\N	\N	\N	Rhodoplanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1285	172	Rhodomicrobium	5497	\N	\N	\N	\N	Rhodomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1286	172	Prosthecomicrobium	5494	\N	\N	\N	\N	Prosthecomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1287	172	Pelagibacterium	5491	\N	\N	\N	\N	Pelagibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1288	172	Pedomicrobium	5486	\N	\N	\N	\N	Pedomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1289	172	Maritalea	5482	\N	\N	\N	\N	Maritalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1290	172	Hyphomicrobium	5471	\N	\N	\N	\N	Hyphomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1291	172	Gemmiger	5469	\N	\N	\N	\N	Gemmiger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1292	172	Filomicrobium	5466	\N	\N	\N	\N	Filomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1293	172	Dichotomicrobium	5464	\N	\N	\N	\N	Dichotomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1294	172	Devosia	5452	\N	\N	\N	\N	Devosia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1295	172	Blastochloris	5448	\N	\N	\N	\N	Blastochloris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1296	172	Aquabacter	5446	\N	\N	\N	\N	Aquabacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1297	172	Angulomicrobium	5443	\N	\N	\N	\N	Angulomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1298	173	Venenivibrio	5440	\N	\N	\N	\N	Venenivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1299	173	Sulfurihydrogenibium	5434	\N	\N	\N	\N	Sulfurihydrogenibium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1300	173	Persephonella	5430	\N	\N	\N	\N	Persephonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1301	174	Thiobacillus	5425	\N	\N	\N	\N	Thiobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1302	174	Tepidiphilus	5423	\N	\N	\N	\N	Tepidiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1303	174	Sulfuricella	5421	\N	\N	\N	\N	Sulfuricella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1304	174	Petrobacter	5419	\N	\N	\N	\N	Petrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1305	174	Hydrogenophilus	5415	\N	\N	\N	\N	Hydrogenophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1306	175	Holophaga	5412	\N	\N	\N	\N	Holophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1307	175	Geothrix	5410	\N	\N	\N	\N	Geothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1308	176	Herpetosiphon	5406	\N	\N	\N	\N	Herpetosiphon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1309	177	Heliorestis	5402	\N	\N	\N	\N	Heliorestis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1310	177	Heliobacterium	5396	\N	\N	\N	\N	Heliobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1311	177	Heliobacillus	5394	\N	\N	\N	\N	Heliobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1312	178	Wolinella	5391	\N	\N	\N	\N	Wolinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1313	178	Sulfurovum	5389	\N	\N	\N	\N	Sulfurovum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1314	178	Sulfurimonas	5385	\N	\N	\N	\N	Sulfurimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1315	178	Helicobacter	5353	\N	\N	\N	\N	Helicobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1316	179	Thiovirga	5350	\N	\N	\N	\N	Thiovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1317	179	Thiofaba	5348	\N	\N	\N	\N	Thiofaba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1318	179	Thioalkalibacter	5346	\N	\N	\N	\N	Thioalkalibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1319	179	Halothiobacillus	5342	\N	\N	\N	\N	Halothiobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1320	180	Zymobacter	5339	\N	\N	\N	\N	Zymobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1321	180	Salinicola	5335	\N	\N	\N	\N	Salinicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1322	180	Modicisalibacter	5333	\N	\N	\N	\N	Modicisalibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1323	180	Kushneria	5327	\N	\N	\N	\N	Kushneria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1324	180	Halovibrio	5325	\N	\N	\N	\N	Halovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1325	180	Halotalea	5323	\N	\N	\N	\N	Halotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1326	180	Halomonas	5258	\N	\N	\N	\N	Halomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1327	180	Cobetia	5255	\N	\N	\N	\N	Cobetia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1328	180	Chromohalobacter	5247	\N	\N	\N	\N	Chromohalobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1329	180	Carnimonas	5245	\N	\N	\N	\N	Carnimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1330	180	Aidingimonas	5243	\N	\N	\N	\N	Aidingimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1331	181	Orenia	5239	\N	\N	\N	\N	Orenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1332	181	Natroniella	5236	\N	\N	\N	\N	Natroniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1333	181	Halonatronum	5234	\N	\N	\N	\N	Halonatronum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1334	181	Halobacteroides	5231	\N	\N	\N	\N	Halobacteroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1335	181	Halanaerobaculum	5229	\N	\N	\N	\N	Halanaerobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1336	181	Halanaerobacter	5226	\N	\N	\N	\N	Halanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1337	181	Fuchsiella	5224	\N	\N	\N	\N	Fuchsiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1338	181	Acetohalobium	5222	\N	\N	\N	\N	Acetohalobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1339	182	Haliangium	5218	\N	\N	\N	\N	Haliangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1340	183	Halothermothrix	5215	\N	\N	\N	\N	Halothermothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1341	183	Halocella	5213	\N	\N	\N	\N	Halocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1342	183	Halarsenatibacter	5211	\N	\N	\N	\N	Halarsenatibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1343	183	Halanaerobium	5203	\N	\N	\N	\N	Halanaerobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1344	184	Zooshikella	5200	\N	\N	\N	\N	Zooshikella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1345	184	Kistimonas	5198	\N	\N	\N	\N	Kistimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1346	184	Halospina	5196	\N	\N	\N	\N	Halospina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1347	184	Hahella	5192	\N	\N	\N	\N	Hahella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1348	184	Endozoicomonas	5190	\N	\N	\N	\N	Endozoicomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1349	185	Granulosicoccus	5186	\N	\N	\N	\N	Granulosicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1350	186	Gracilibacter	5183	\N	\N	\N	\N	Gracilibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1351	187	Stackebrandtia	5179	\N	\N	\N	\N	Stackebrandtia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1352	187	Haloglycomyces	5177	\N	\N	\N	\N	Haloglycomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1353	187	Glycomyces	5166	\N	\N	\N	\N	Glycomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1354	188	Modestobacter	5161	\N	\N	\N	\N	Modestobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1355	188	Geodermatophilus	5158	\N	\N	\N	\N	Geodermatophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1356	188	Blastococcus	5154	\N	\N	\N	\N	Blastococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1357	189	Geopsychrobacter	5151	\N	\N	\N	\N	Geopsychrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1358	189	Geobacter	5140	\N	\N	\N	\N	Geobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1359	189	Geoalkalibacter	5137	\N	\N	\N	\N	Geoalkalibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1360	190	Gemmatimonas	5134	\N	\N	\N	\N	Gemmatimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1361	191	Zhongshania	5130	\N	\N	\N	\N	Zhongshania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1362	191	Umboniibacter	5128	\N	\N	\N	\N	Umboniibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1363	191	Thiohalomonas	5126	\N	\N	\N	\N	Thiohalomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1364	191	Thiohalobacter	5124	\N	\N	\N	\N	Thiohalobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1365	191	Spongiibacter	5120	\N	\N	\N	\N	Spongiibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1366	191	Solimonas	5115	\N	\N	\N	\N	Solimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1367	191	Simiduia	5112	\N	\N	\N	\N	Simiduia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1368	191	Sedimenticola	5110	\N	\N	\N	\N	Sedimenticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1369	191	Porticoccus	5108	\N	\N	\N	\N	Porticoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1370	191	Plasticicumulans	5106	\N	\N	\N	\N	Plasticicumulans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1371	191	Orbus	5104	\N	\N	\N	\N	Orbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1372	191	Marinicella	5102	\N	\N	\N	\N	Marinicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1373	191	Halioglobus	5100	\N	\N	\N	\N	Halioglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1374	191	Congregibacter	5098	\N	\N	\N	\N	Congregibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1375	191	Chromatocurvus	5096	\N	\N	\N	\N	Chromatocurvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1376	191	Arenicella	5094	\N	\N	\N	\N	Arenicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1377	191	Alkalimonas	5090	\N	\N	\N	\N	Alkalimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1378	192	Gaiella	5087	\N	\N	\N	\N	Gaiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1379	193	Propionigenium	5083	\N	\N	\N	\N	Propionigenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1380	193	Ilyobacter	5078	\N	\N	\N	\N	Ilyobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1381	193	Fusobacterium	5063	\N	\N	\N	\N	Fusobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1382	193	Cetobacterium	5060	\N	\N	\N	\N	Cetobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1383	194	Motilibacter	5057	\N	\N	\N	\N	Motilibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1384	195	Francisella	5047	\N	\N	\N	\N	Francisella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1385	196	Zunongwangia	5044	\N	\N	\N	\N	Zunongwangia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1386	196	Zobellia	5040	\N	\N	\N	\N	Zobellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1387	196	Zhouia	5038	\N	\N	\N	\N	Zhouia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1388	196	Zeaxanthinibacter	5036	\N	\N	\N	\N	Zeaxanthinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1389	196	Yeosuana	5034	\N	\N	\N	\N	Yeosuana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1390	196	Winogradskyella	5026	\N	\N	\N	\N	Winogradskyella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1391	196	Weeksella	5024	\N	\N	\N	\N	Weeksella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1392	196	Wautersiella	5022	\N	\N	\N	\N	Wautersiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1393	196	Vitellibacter	5019	\N	\N	\N	\N	Vitellibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1394	196	Ulvibacter	5016	\N	\N	\N	\N	Ulvibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1395	196	Tenacibaculum	4999	\N	\N	\N	\N	Tenacibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1396	196	Tamlana	4996	\N	\N	\N	\N	Tamlana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1397	196	Subsaximicrobium	4993	\N	\N	\N	\N	Subsaximicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1398	196	Soonwooa	4991	\N	\N	\N	\N	Soonwooa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1399	196	Snuella	4989	\N	\N	\N	\N	Snuella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1400	196	Salinimicrobium	4984	\N	\N	\N	\N	Salinimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1401	196	Salegentibacter	4977	\N	\N	\N	\N	Salegentibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1402	196	Robiginitalea	4974	\N	\N	\N	\N	Robiginitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1403	196	Riemerella	4972	\N	\N	\N	\N	Riemerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1404	196	Psychroserpens	4969	\N	\N	\N	\N	Psychroserpens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1405	196	Psychroflexus	4963	\N	\N	\N	\N	Psychroflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1406	196	Pseudozobellia	4961	\N	\N	\N	\N	Pseudozobellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1407	196	Polaribacter	4954	\N	\N	\N	\N	Polaribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1408	196	Planobacterium	4952	\N	\N	\N	\N	Planobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1409	196	Ornithobacterium	4950	\N	\N	\N	\N	Ornithobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1410	196	Olleya	4948	\N	\N	\N	\N	Olleya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1411	196	Nonlabens	4944	\N	\N	\N	\N	Nonlabens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1412	196	Myroides	4937	\N	\N	\N	\N	Myroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1413	196	Muriicola	4935	\N	\N	\N	\N	Muriicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1414	196	Muricauda	4928	\N	\N	\N	\N	Muricauda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1415	196	Mesonia	4924	\N	\N	\N	\N	Mesonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1416	196	Mesoflavibacter	4922	\N	\N	\N	\N	Mesoflavibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1417	196	Meridianimaribacter	4920	\N	\N	\N	\N	Meridianimaribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1418	196	Maritimimonas	4918	\N	\N	\N	\N	Maritimimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1419	196	Mariniflexile	4914	\N	\N	\N	\N	Mariniflexile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1420	196	Maribacter	4906	\N	\N	\N	\N	Maribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1421	196	Lutibacter	4903	\N	\N	\N	\N	Lutibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1422	196	Lutaonella	4901	\N	\N	\N	\N	Lutaonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1423	196	Leptobacterium	4899	\N	\N	\N	\N	Leptobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1424	196	Leeuwenhoekiella	4894	\N	\N	\N	\N	Leeuwenhoekiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1425	196	Lacinutrix	4891	\N	\N	\N	\N	Lacinutrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1426	196	Kordia	4888	\N	\N	\N	\N	Kordia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1427	196	Joostella	4886	\N	\N	\N	\N	Joostella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1428	196	Jejuia	4884	\N	\N	\N	\N	Jejuia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1429	196	Hyunsoonleella	4882	\N	\N	\N	\N	Hyunsoonleella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1430	196	Gramella	4878	\N	\N	\N	\N	Gramella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1431	196	Gilvibacter	4876	\N	\N	\N	\N	Gilvibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1432	196	Gillisia	4871	\N	\N	\N	\N	Gillisia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1433	196	Gelidibacter	4867	\N	\N	\N	\N	Gelidibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1434	196	Gangjinia	4865	\N	\N	\N	\N	Gangjinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1435	196	Galbibacter	4863	\N	\N	\N	\N	Galbibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1436	196	Gaetbulibacter	4859	\N	\N	\N	\N	Gaetbulibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1437	196	Fulvibacter	4857	\N	\N	\N	\N	Fulvibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1438	196	Formosa	4854	\N	\N	\N	\N	Formosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1439	196	Flavobacterium	4785	\N	\N	\N	\N	Flavobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1440	196	Flaviramulus	4783	\N	\N	\N	\N	Flaviramulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1441	196	Flagellimonas	4781	\N	\N	\N	\N	Flagellimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1442	196	Euzebyella	4779	\N	\N	\N	\N	Euzebyella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1443	196	Epilithonimonas	4777	\N	\N	\N	\N	Epilithonimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1444	196	Empedobacter	4775	\N	\N	\N	\N	Empedobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1445	196	Dokdonia	4768	\N	\N	\N	\N	Dokdonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1446	196	Croceitalea	4765	\N	\N	\N	\N	Croceitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1447	196	Croceibacter	4763	\N	\N	\N	\N	Croceibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1448	196	Costertonia	4761	\N	\N	\N	\N	Costertonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1449	196	Coenonia	4759	\N	\N	\N	\N	Coenonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1450	196	Cloacibacterium	4756	\N	\N	\N	\N	Cloacibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1451	196	Chryseobacterium	4701	\N	\N	\N	\N	Chryseobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1452	196	Cellulophaga	4695	\N	\N	\N	\N	Cellulophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1453	196	Capnocytophaga	4686	\N	\N	\N	\N	Capnocytophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1454	196	Bizionia	4680	\N	\N	\N	\N	Bizionia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1455	196	Arenibacter	4675	\N	\N	\N	\N	Arenibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1456	196	Aquimarina	4665	\N	\N	\N	\N	Aquimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1457	196	Algibacter	4662	\N	\N	\N	\N	Algibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1458	196	Aestuariicola	4660	\N	\N	\N	\N	Aestuariicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1459	196	Aequorivita	4654	\N	\N	\N	\N	Aequorivita	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1460	197	Thermonema	4651	\N	\N	\N	\N	Thermonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1461	197	Roseivirga	4647	\N	\N	\N	\N	Roseivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1462	197	Reichenbachiella	4644	\N	\N	\N	\N	Reichenbachiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1463	197	Rapidithrix	4642	\N	\N	\N	\N	Rapidithrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1464	197	Persicobacter	4639	\N	\N	\N	\N	Persicobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1465	197	Perexilibacter	4637	\N	\N	\N	\N	Perexilibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1466	197	Marivirga	4634	\N	\N	\N	\N	Marivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1467	197	Marinoscillum	4631	\N	\N	\N	\N	Marinoscillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1468	197	Limibacter	4629	\N	\N	\N	\N	Limibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1469	197	Fulvivirga	4627	\N	\N	\N	\N	Fulvivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1470	197	Flexithrix	4625	\N	\N	\N	\N	Flexithrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1471	197	Flammeovirga	4619	\N	\N	\N	\N	Flammeovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1472	197	Fabibacter	4617	\N	\N	\N	\N	Fabibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1473	197	Cesiribacter	4615	\N	\N	\N	\N	Cesiribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1474	197	Aureibacter	4613	\N	\N	\N	\N	Aureibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1475	198	Fibrobacter	4608	\N	\N	\N	\N	Fibrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1476	199	Paraferrimonas	4605	\N	\N	\N	\N	Paraferrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1477	199	Ferrimonas	4599	\N	\N	\N	\N	Ferrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1478	200	Euzebya	4596	\N	\N	\N	\N	Euzebya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1479	201	Pseudoramibacter	4593	\N	\N	\N	\N	Pseudoramibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1480	201	Garciella	4591	\N	\N	\N	\N	Garciella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1481	201	Eubacterium	4550	\N	\N	\N	\N	Eubacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1482	201	Anaerofustis	4548	\N	\N	\N	\N	Anaerofustis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1483	201	Alkalibaculum	4546	\N	\N	\N	\N	Alkalibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1484	201	Alkalibacter	4544	\N	\N	\N	\N	Alkalibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1485	201	Acetobacterium	4535	\N	\N	\N	\N	Acetobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1486	202	Porphyrobacter	4527	\N	\N	\N	\N	Porphyrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1487	202	Erythromicrobium	4525	\N	\N	\N	\N	Erythromicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1488	202	Erythrobacter	4513	\N	\N	\N	\N	Erythrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1489	202	Croceicoccus	4511	\N	\N	\N	\N	Croceicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1490	202	Altererythrobacter	4500	\N	\N	\N	\N	Altererythrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1491	203	Turicibacter	4497	\N	\N	\N	\N	Turicibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1492	203	Solobacterium	4495	\N	\N	\N	\N	Solobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1493	203	Kandleria	4493	\N	\N	\N	\N	Kandleria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1494	203	Holdemania	4491	\N	\N	\N	\N	Holdemania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1495	203	Erysipelothrix	4487	\N	\N	\N	\N	Erysipelothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1496	203	Eggerthia	4485	\N	\N	\N	\N	Eggerthia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1497	203	Coprobacillus	4483	\N	\N	\N	\N	Coprobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1498	203	Catenibacterium	4481	\N	\N	\N	\N	Catenibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1499	203	Bulleidia	4479	\N	\N	\N	\N	Bulleidia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1500	203	Allobaculum	4477	\N	\N	\N	\N	Allobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1501	204	Mesoplasma	4464	\N	\N	\N	\N	Mesoplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1502	204	Entomoplasma	4458	\N	\N	\N	\N	Entomoplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1503	205	Vagococcus	4449	\N	\N	\N	\N	Vagococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1504	205	Tetragenococcus	4443	\N	\N	\N	\N	Tetragenococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1505	205	Pilibacter	4441	\N	\N	\N	\N	Pilibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1506	205	Melissococcus	4439	\N	\N	\N	\N	Melissococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1507	205	Enterococcus	4402	\N	\N	\N	\N	Enterococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1508	205	Catellicoccus	4400	\N	\N	\N	\N	Catellicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1509	205	Bavariicoccus	4398	\N	\N	\N	\N	Bavariicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1510	206	Yokenella	4395	\N	\N	\N	\N	Yokenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1511	206	Yersinia	4376	\N	\N	\N	\N	Yersinia<Enterobacteriaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
1512	206	Xenorhabdus	4353	\N	\N	\N	\N	Xenorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1513	206	Trabulsiella	4350	\N	\N	\N	\N	Trabulsiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1514	206	Thorsellia	4348	\N	\N	\N	\N	Thorsellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1515	206	Tatumella	4343	\N	\N	\N	\N	Tatumella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1516	206	Sodalis	4341	\N	\N	\N	\N	Sodalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1517	206	Shimwellia	4338	\N	\N	\N	\N	Shimwellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1518	206	Shigella	4334	\N	\N	\N	\N	Shigella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1519	206	Serratia	4317	\N	\N	\N	\N	Serratia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1520	206	Samsonia	4315	\N	\N	\N	\N	Samsonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1521	206	Salmonella	4308	\N	\N	\N	\N	Salmonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1522	206	Raoultella	4305	\N	\N	\N	\N	Raoultella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1523	206	Rahnella	4303	\N	\N	\N	\N	Rahnella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1524	206	Providencia	4294	\N	\N	\N	\N	Providencia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1525	206	Proteus	4289	\N	\N	\N	\N	Proteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1526	206	Pragia	4287	\N	\N	\N	\N	Pragia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1527	206	Plesiomonas	4285	\N	\N	\N	\N	Plesiomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1528	206	Photorhabdus	4270	\N	\N	\N	\N	Photorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1529	206	Pectobacterium	4263	\N	\N	\N	\N	Pectobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1530	206	Pantoea	4252	\N	\N	\N	\N	Pantoea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1531	206	Obesumbacterium	4250	\N	\N	\N	\N	Obesumbacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1532	206	Morganella	4248	\N	\N	\N	\N	Morganella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1533	206	Lonsdalea	4246	\N	\N	\N	\N	Lonsdalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1534	206	Leminorella	4244	\N	\N	\N	\N	Leminorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1535	206	Kluyvera	4240	\N	\N	\N	\N	Kluyvera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1536	206	Klebsiella	4236	\N	\N	\N	\N	Klebsiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1537	206	Hafnia	4233	\N	\N	\N	\N	Hafnia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1538	206	Gibbsiella	4231	\N	\N	\N	\N	Gibbsiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1539	206	Escherichia	4226	\N	\N	\N	\N	Escherichia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1540	206	Erwinia	4213	\N	\N	\N	\N	Erwinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1541	206	Enterobacter	4196	\N	\N	\N	\N	Enterobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1542	206	Edwardsiella	4192	\N	\N	\N	\N	Edwardsiella<Enterobacteriaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
1543	206	Dickeya	4188	\N	\N	\N	\N	Dickeya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1544	206	Cronobacter	4178	\N	\N	\N	\N	Cronobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1545	206	Cosenzaea	4176	\N	\N	\N	\N	Cosenzaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1546	206	Citrobacter	4164	\N	\N	\N	\N	Citrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1547	206	Cedecea	4162	\N	\N	\N	\N	Cedecea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1548	206	Buttiauxella	4154	\N	\N	\N	\N	Buttiauxella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1549	206	Budvicia	4152	\N	\N	\N	\N	Budvicia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1550	206	Brenneria	4147	\N	\N	\N	\N	Brenneria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1551	206	Biostraticola	4145	\N	\N	\N	\N	Biostraticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1552	206	Arsenophonus	4143	\N	\N	\N	\N	Arsenophonus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1553	207	Elusimicrobium	4140	\N	\N	\N	\N	Elusimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1554	208	Thiohalospira	4137	\N	\N	\N	\N	Thiohalospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1555	208	Thioalkalivibrio	4130	\N	\N	\N	\N	Thioalkalivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1556	208	Thioalbus	4128	\N	\N	\N	\N	Thioalbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1557	208	Nitrococcus	4126	\N	\N	\N	\N	Nitrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1558	208	Natronocella	4124	\N	\N	\N	\N	Natronocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1559	208	Halorhodospira	4120	\N	\N	\N	\N	Halorhodospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1560	208	Ectothiorhodospira	4113	\N	\N	\N	\N	Ectothiorhodospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1561	208	Ectothiorhodosinus	4111	\N	\N	\N	\N	Ectothiorhodosinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1562	208	Arhodomonas	4109	\N	\N	\N	\N	Arhodomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1563	208	Aquisalimonas	4107	\N	\N	\N	\N	Aquisalimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1564	208	Alkalispirillum	4105	\N	\N	\N	\N	Alkalispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1565	208	Alkalilimnicola	4102	\N	\N	\N	\N	Alkalilimnicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1566	208	Acidiferrobacter	4100	\N	\N	\N	\N	Acidiferrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1567	209	Dietzia	4085	\N	\N	\N	\N	Dietzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1568	210	Dictyoglomus	4081	\N	\N	\N	\N	Dictyoglomus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1569	211	Pelobacter	4073	\N	\N	\N	\N	Pelobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1570	211	Malonomonas	4071	\N	\N	\N	\N	Malonomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1571	211	Desulfuromusa	4066	\N	\N	\N	\N	Desulfuromusa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1572	211	Desulfuromonas	4059	\N	\N	\N	\N	Desulfuromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1573	212	Thermovibrio	4055	\N	\N	\N	\N	Thermovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1574	212	Desulfurobacterium	4051	\N	\N	\N	\N	Desulfurobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1575	212	Balnearium	4049	\N	\N	\N	\N	Balnearium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1576	213	Hippea	4044	\N	\N	\N	\N	Hippea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1577	213	Desulfurella	4039	\N	\N	\N	\N	Desulfurella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1578	214	Lawsonia	4036	\N	\N	\N	\N	Lawsonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1579	214	Desulfovibrio	3979	\N	\N	\N	\N	Desulfovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1580	214	Desulfocurvus	3977	\N	\N	\N	\N	Desulfocurvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1581	214	Desulfobaculum	3975	\N	\N	\N	\N	Desulfobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1582	214	Bilophila	3973	\N	\N	\N	\N	Bilophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1583	215	Desulfonatronum	3966	\N	\N	\N	\N	Desulfonatronum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1584	216	Desulfomicrobium	3957	\N	\N	\N	\N	Desulfomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1585	217	Desulfothermus	3954	\N	\N	\N	\N	Desulfothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1586	217	Desulfonauticus	3951	\N	\N	\N	\N	Desulfonauticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1587	217	Desulfonatronovibrio	3946	\N	\N	\N	\N	Desulfonatronovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1588	217	Desulfohalobium	3943	\N	\N	\N	\N	Desulfohalobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1589	218	Desulfotalea	3939	\N	\N	\N	\N	Desulfotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1590	218	Desulforhopalus	3936	\N	\N	\N	\N	Desulforhopalus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1591	218	Desulfopila	3933	\N	\N	\N	\N	Desulfopila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1592	218	Desulfofustis	3931	\N	\N	\N	\N	Desulfofustis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1593	218	Desulfocapsa	3928	\N	\N	\N	\N	Desulfocapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1594	218	Desulfobulbus	3923	\N	\N	\N	\N	Desulfobulbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1595	219	Desulfotignum	3919	\N	\N	\N	\N	Desulfotignum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1596	219	Desulfospira	3917	\N	\N	\N	\N	Desulfospira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1597	219	Desulfosarcina	3913	\N	\N	\N	\N	Desulfosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1598	219	Desulfosalsimonas	3911	\N	\N	\N	\N	Desulfosalsimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1599	219	Desulforegula	3909	\N	\N	\N	\N	Desulforegula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1600	219	Desulfonema	3906	\N	\N	\N	\N	Desulfonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1601	219	Desulfoluna	3903	\N	\N	\N	\N	Desulfoluna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1602	219	Desulfofrigus	3900	\N	\N	\N	\N	Desulfofrigus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1603	219	Desulfofaba	3897	\N	\N	\N	\N	Desulfofaba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1604	219	Desulfococcus	3894	\N	\N	\N	\N	Desulfococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1605	219	Desulfocella	3892	\N	\N	\N	\N	Desulfocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1606	219	Desulfobotulus	3890	\N	\N	\N	\N	Desulfobotulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1607	219	Desulfobacula	3887	\N	\N	\N	\N	Desulfobacula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1608	219	Desulfobacterium	3880	\N	\N	\N	\N	Desulfobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1609	219	Desulfobacter	3873	\N	\N	\N	\N	Desulfobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1610	219	Desulfatirhabdium	3871	\N	\N	\N	\N	Desulfatirhabdium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1611	219	Desulfatiferula	3869	\N	\N	\N	\N	Desulfatiferula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1612	219	Desulfatibacillum	3866	\N	\N	\N	\N	Desulfatibacillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1613	220	Desulfarculus	3863	\N	\N	\N	\N	Desulfarculus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1614	221	Piscicoccus	3860	\N	\N	\N	\N	Piscicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1615	221	Mobilicoccus	3858	\N	\N	\N	\N	Mobilicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1616	221	Kineosphaera	3856	\N	\N	\N	\N	Kineosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1617	221	Dermatophilus	3854	\N	\N	\N	\N	Dermatophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1618	221	Austwickia	3852	\N	\N	\N	\N	Austwickia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1619	222	Yimella	3849	\N	\N	\N	\N	Yimella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1620	222	Luteipulveratus	3847	\N	\N	\N	\N	Luteipulveratus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1621	222	Kytococcus	3843	\N	\N	\N	\N	Kytococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1622	222	Flexivirga	3841	\N	\N	\N	\N	Flexivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1623	222	Dermacoccus	3836	\N	\N	\N	\N	Dermacoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1624	222	Demetria	3834	\N	\N	\N	\N	Demetria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1625	222	Branchiibius	3832	\N	\N	\N	\N	Branchiibius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1626	223	Helcobacillus	3829	\N	\N	\N	\N	Helcobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1627	223	Devriesea	3827	\N	\N	\N	\N	Devriesea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1628	223	Dermabacter	3825	\N	\N	\N	\N	Dermabacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1629	223	Brachybacterium	3810	\N	\N	\N	\N	Brachybacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1630	224	Lysinimicrobium	3807	\N	\N	\N	\N	Lysinimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1631	224	Demequina	3801	\N	\N	\N	\N	Demequina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1632	225	Deinococcus	3753	\N	\N	\N	\N	Deinococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1633	225	Deinobacterium	3751	\N	\N	\N	\N	Deinobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1634	226	Dehalogenimonas	3748	\N	\N	\N	\N	Dehalogenimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1635	227	Defluviitalea	3745	\N	\N	\N	\N	Defluviitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1636	228	Caldithrix	3741	\N	\N	\N	\N	Caldithrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1637	229	Mucispirillum	3738	\N	\N	\N	\N	Mucispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1638	229	Geovibrio	3735	\N	\N	\N	\N	Geovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1639	229	Flexistipes	3733	\N	\N	\N	\N	Flexistipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1640	229	Denitrovibrio	3731	\N	\N	\N	\N	Denitrovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1641	229	Deferribacter	3726	\N	\N	\N	\N	Deferribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1642	229	Calditerrivibrio	3724	\N	\N	\N	\N	Calditerrivibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1643	230	Sporocytophaga	3721	\N	\N	\N	\N	Sporocytophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1644	230	Spirosoma	3717	\N	\N	\N	\N	Spirosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1645	230	Runella	3713	\N	\N	\N	\N	Runella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1646	230	Rudanella	3711	\N	\N	\N	\N	Rudanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1647	230	Rhodonellum	3709	\N	\N	\N	\N	Rhodonellum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1648	230	Rhodocytophaga	3707	\N	\N	\N	\N	Rhodocytophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1649	230	Pontibacter	3699	\N	\N	\N	\N	Pontibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1650	230	Persicitalea	3697	\N	\N	\N	\N	Persicitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1651	230	Microscilla	3695	\N	\N	\N	\N	Microscilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1652	230	Meniscus	3693	\N	\N	\N	\N	Meniscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1653	230	Litoribacter	3691	\N	\N	\N	\N	Litoribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1654	230	Leadbetterella	3689	\N	\N	\N	\N	Leadbetterella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1655	230	Larkinella	3685	\N	\N	\N	\N	Larkinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1656	230	Hymenobacter	3662	\N	\N	\N	\N	Hymenobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1657	230	Flexibacter	3654	\N	\N	\N	\N	Flexibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1658	230	Flectobacillus	3651	\N	\N	\N	\N	Flectobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1659	230	Fibrisoma	3649	\N	\N	\N	\N	Fibrisoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1660	230	Emticicia	3646	\N	\N	\N	\N	Emticicia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1661	230	Dyadobacter	3637	\N	\N	\N	\N	Dyadobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1662	230	Cytophaga	3633	\N	\N	\N	\N	Cytophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1663	230	Arcicella	3630	\N	\N	\N	\N	Arcicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1664	230	Adhaeribacter	3625	\N	\N	\N	\N	Adhaeribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1665	231	Stigmatella	3620	\N	\N	\N	\N	Stigmatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1666	231	Melittangium	3618	\N	\N	\N	\N	Melittangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1667	231	Hyalangium	3616	\N	\N	\N	\N	Hyalangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1668	231	Cystobacter	3609	\N	\N	\N	\N	Cystobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1669	231	Archangium	3607	\N	\N	\N	\N	Archangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1670	231	Anaeromyxobacter	3605	\N	\N	\N	\N	Anaeromyxobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1671	232	Nitritalea	3602	\N	\N	\N	\N	Nitritalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1672	232	Mongoliitalea	3600	\N	\N	\N	\N	Mongoliitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1673	232	Indibacter	3598	\N	\N	\N	\N	Indibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1674	232	Fontibacter	3596	\N	\N	\N	\N	Fontibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1675	232	Echinicola	3593	\N	\N	\N	\N	Echinicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1676	232	Cyclobacterium	3589	\N	\N	\N	\N	Cyclobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1677	232	Belliella	3586	\N	\N	\N	\N	Belliella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1678	232	Aquiflexum	3584	\N	\N	\N	\N	Aquiflexum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1679	232	Algoriphagus	3561	\N	\N	\N	\N	Algoriphagus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1680	233	Cyanophyceae	86694	\N	\N	\N	\N	Cyanophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1681	234	Fodinicola	2878	\N	\N	\N	\N	Fodinicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1682	234	Cryptosporangium	2873	\N	\N	\N	\N	Cryptosporangium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1683	235	Wandonia	2870	\N	\N	\N	\N	Wandonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1684	235	Owenweeksia	2868	\N	\N	\N	\N	Owenweeksia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1685	235	Lishizhenia	2865	\N	\N	\N	\N	Lishizhenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1686	235	Fluviicola	2863	\N	\N	\N	\N	Fluviicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1687	235	Cryomorpha	2861	\N	\N	\N	\N	Cryomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1688	235	Crocinitomix	2859	\N	\N	\N	\N	Crocinitomix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1689	236	Diplorickettsia	2856	\N	\N	\N	\N	Diplorickettsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1690	236	Coxiella	2854	\N	\N	\N	\N	Coxiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1691	236	Aquicella	2851	\N	\N	\N	\N	Aquicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1692	237	Tomitella	2848	\N	\N	\N	\N	Tomitella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1693	238	Turicella	2845	\N	\N	\N	\N	Turicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1694	238	Corynebacterium	2777	\N	\N	\N	\N	Corynebacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1695	239	Slackia	2770	\N	\N	\N	\N	Slackia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1696	239	Paraeggerthella	2768	\N	\N	\N	\N	Paraeggerthella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1697	239	Olsenella	2764	\N	\N	\N	\N	Olsenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1698	239	Gordonibacter	2762	\N	\N	\N	\N	Gordonibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1699	239	Enterorhabdus	2760	\N	\N	\N	\N	Enterorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1700	239	Eggerthella	2757	\N	\N	\N	\N	Eggerthella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1701	239	Denitrobacterium	2755	\N	\N	\N	\N	Denitrobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1702	239	Cryptobacterium	2753	\N	\N	\N	\N	Cryptobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1703	239	Coriobacterium	2751	\N	\N	\N	\N	Coriobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1704	239	Collinsella	2746	\N	\N	\N	\N	Collinsella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1705	239	Atopobium	2741	\N	\N	\N	\N	Atopobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1706	239	Asaccharobacter	2739	\N	\N	\N	\N	Asaccharobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1707	239	Adlercreutzia	2737	\N	\N	\N	\N	Adlercreutzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1708	240	Conexibacter	2734	\N	\N	\N	\N	Conexibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1709	241	Xenophilus	2730	\N	\N	\N	\N	Xenophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1710	241	Verminephrobacter	2728	\N	\N	\N	\N	Verminephrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1711	241	Variovorax	2721	\N	\N	\N	\N	Variovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1712	241	Tepidicella	2719	\N	\N	\N	\N	Tepidicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1713	241	Simplicispira	2715	\N	\N	\N	\N	Simplicispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1714	241	Schlegelella	2712	\N	\N	\N	\N	Schlegelella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1715	241	Roseateles	2708	\N	\N	\N	\N	Roseateles	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1716	241	Rhodoferax	2705	\N	\N	\N	\N	Rhodoferax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1717	241	Ramlibacter	2702	\N	\N	\N	\N	Ramlibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1718	241	Pseudorhodoferax	2699	\N	\N	\N	\N	Pseudorhodoferax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1719	241	Pseudacidovorax	2697	\N	\N	\N	\N	Pseudacidovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1720	241	Polaromonas	2692	\N	\N	\N	\N	Polaromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1721	241	Pelomonas	2689	\N	\N	\N	\N	Pelomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1722	241	Ottowia	2686	\N	\N	\N	\N	Ottowia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1723	241	Malikia	2683	\N	\N	\N	\N	Malikia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1724	241	Macromonas	2681	\N	\N	\N	\N	Macromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1725	241	Limnohabitans	2676	\N	\N	\N	\N	Limnohabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1726	241	Lampropedia	2674	\N	\N	\N	\N	Lampropedia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1727	241	Kinneretia	2672	\N	\N	\N	\N	Kinneretia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1728	241	Hylemonella	2670	\N	\N	\N	\N	Hylemonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1729	241	Hydrogenophaga	2660	\N	\N	\N	\N	Hydrogenophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1730	241	Giesbergeria	2654	\N	\N	\N	\N	Giesbergeria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1731	241	Diaphorobacter	2651	\N	\N	\N	\N	Diaphorobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1732	241	Delftia	2647	\N	\N	\N	\N	Delftia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1733	241	Curvibacter	2642	\N	\N	\N	\N	Curvibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1734	241	Comamonas	2630	\N	\N	\N	\N	Comamonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1735	241	Caldimonas	2627	\N	\N	\N	\N	Caldimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1736	241	Caenimonas	2625	\N	\N	\N	\N	Caenimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1737	241	Brachymonas	2622	\N	\N	\N	\N	Brachymonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1738	241	Alicycliphilus	2620	\N	\N	\N	\N	Alicycliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1739	241	Albidiferax	2618	\N	\N	\N	\N	Albidiferax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1740	241	Acidovorax	2603	\N	\N	\N	\N	Acidovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1741	242	Thalassomonas	2595	\N	\N	\N	\N	Thalassomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1742	242	Colwellia	2584	\N	\N	\N	\N	Colwellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1743	243	Cohaesibacter	2580	\N	\N	\N	\N	Cohaesibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1744	244	Tissierella	2577	\N	\N	\N	\N	Tissierella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1745	244	Thermaerobacter	2571	\N	\N	\N	\N	Thermaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1746	244	Symbiobacterium	2569	\N	\N	\N	\N	Symbiobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1747	244	Sulfobacillus	2564	\N	\N	\N	\N	Sulfobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1748	244	Sporanaerobacter	2562	\N	\N	\N	\N	Sporanaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1749	244	Soehngenia	2560	\N	\N	\N	\N	Soehngenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1750	244	Sedimentibacter	2557	\N	\N	\N	\N	Sedimentibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1751	244	Pseudoflavonifractor	2555	\N	\N	\N	\N	Pseudoflavonifractor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1752	244	Proteocatella	2553	\N	\N	\N	\N	Proteocatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1753	244	Proteiniborus	2551	\N	\N	\N	\N	Proteiniborus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1754	244	Peptoniphilus	2542	\N	\N	\N	\N	Peptoniphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1755	244	Parvimonas	2540	\N	\N	\N	\N	Parvimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1756	244	Natranaerovirga	2537	\N	\N	\N	\N	Natranaerovirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1757	244	Mogibacterium	2531	\N	\N	\N	\N	Mogibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1758	244	Howardella	2529	\N	\N	\N	\N	Howardella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1759	244	Helcococcus	2525	\N	\N	\N	\N	Helcococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1760	244	Guggenheimella	2523	\N	\N	\N	\N	Guggenheimella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1761	244	Fusibacter	2520	\N	\N	\N	\N	Fusibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1762	244	Flavonifractor	2518	\N	\N	\N	\N	Flavonifractor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1763	244	Finegoldia	2516	\N	\N	\N	\N	Finegoldia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1764	244	Dethiosulfatibacter	2514	\N	\N	\N	\N	Dethiosulfatibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1765	244	Carboxydocella	2510	\N	\N	\N	\N	Carboxydocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1766	244	Blautia	2503	\N	\N	\N	\N	Blautia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1767	244	Anaerovorax	2501	\N	\N	\N	\N	Anaerovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1768	244	Anaerovirgula	2499	\N	\N	\N	\N	Anaerovirgula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1769	244	Anaerococcus	2493	\N	\N	\N	\N	Anaerococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1770	244	Anaerobranca	2489	\N	\N	\N	\N	Anaerobranca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1771	244	Acidaminobacter	2487	\N	\N	\N	\N	Acidaminobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1772	244	Acetoanaerobium	2485	\N	\N	\N	\N	Acetoanaerobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1773	245	Tindallia	2480	\N	\N	\N	\N	Tindallia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1774	245	Thermotalea	2478	\N	\N	\N	\N	Thermotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1775	245	Thermohalobacter	2476	\N	\N	\N	\N	Thermohalobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1776	245	Thermobrachium	2474	\N	\N	\N	\N	Thermobrachium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1777	245	Tepidimicrobium	2471	\N	\N	\N	\N	Tepidimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1778	245	Sporosalibacterium	2469	\N	\N	\N	\N	Sporosalibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1779	245	Sarcina	2466	\N	\N	\N	\N	Sarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1780	245	Saccharofermentans	2464	\N	\N	\N	\N	Saccharofermentans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1781	245	Proteiniclasticum	2462	\N	\N	\N	\N	Proteiniclasticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1782	245	Oxobacter	2460	\N	\N	\N	\N	Oxobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1783	245	Natronincola	2456	\N	\N	\N	\N	Natronincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1784	245	Lutispora	2454	\N	\N	\N	\N	Lutispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1785	245	Geosporobacter	2452	\N	\N	\N	\N	Geosporobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1786	245	Fervidicella	2450	\N	\N	\N	\N	Fervidicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1787	245	Clostridium	2283	\N	\N	\N	\N	Clostridium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1788	245	Clostridiisalibacter	2281	\N	\N	\N	\N	Clostridiisalibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1789	245	Caminicella	2279	\N	\N	\N	\N	Caminicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1790	245	Caloranaerobacter	2277	\N	\N	\N	\N	Caloranaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1791	245	Caloramator	2268	\N	\N	\N	\N	Caloramator	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1792	245	Butyricicoccus	2266	\N	\N	\N	\N	Butyricicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1793	245	Anoxynatronum	2264	\N	\N	\N	\N	Anoxynatronum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1794	245	Anaerobacter	2262	\N	\N	\N	\N	Anaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1795	245	Alkaliphilus	2257	\N	\N	\N	\N	Alkaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1796	246	Chthonomonas	2254	\N	\N	\N	\N	Chthonomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1797	247	Desulfurispirillum	2250	\N	\N	\N	\N	Desulfurispirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1798	247	Desulfurispira	2248	\N	\N	\N	\N	Desulfurispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1799	247	Chrysiogenes	2246	\N	\N	\N	\N	Chrysiogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1800	248	Rubidibacter	2243	\N	\N	\N	\N	Rubidibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1801	249	Thiorhodovibrio	2240	\N	\N	\N	\N	Thiorhodovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1802	249	Thiorhodococcus	2234	\N	\N	\N	\N	Thiorhodococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1803	249	Thiophaeococcus	2232	\N	\N	\N	\N	Thiophaeococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1804	249	Thiolamprovum	2230	\N	\N	\N	\N	Thiolamprovum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1805	249	Thiohalocapsa	2228	\N	\N	\N	\N	Thiohalocapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1806	249	Thioflavicoccus	2226	\N	\N	\N	\N	Thioflavicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1807	249	Thiodictyon	2223	\N	\N	\N	\N	Thiodictyon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1808	249	Thiocystis	2219	\N	\N	\N	\N	Thiocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1809	249	Thiococcus	2217	\N	\N	\N	\N	Thiococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1810	249	Thiocapsa	2213	\N	\N	\N	\N	Thiocapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1811	249	Rheinheimera	2202	\N	\N	\N	\N	Rheinheimera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1812	249	Rhabdochromatium	2200	\N	\N	\N	\N	Rhabdochromatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1813	249	Nitrosococcus	2198	\N	\N	\N	\N	Nitrosococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1814	249	Marichromatium	2192	\N	\N	\N	\N	Marichromatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1815	249	Isochromatium	2190	\N	\N	\N	\N	Isochromatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1816	249	Halochromatium	2186	\N	\N	\N	\N	Halochromatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1817	249	Allochromatium	2180	\N	\N	\N	\N	Allochromatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1818	250	Christensenella	2177	\N	\N	\N	\N	Christensenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1819	251	Roseiflexus	2174	\N	\N	\N	\N	Roseiflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1820	251	Chloroflexus	2171	\N	\N	\N	\N	Chloroflexus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1821	252	Prosthecochloris	2167	\N	\N	\N	\N	Prosthecochloris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1822	252	Chloroherpeton	2165	\N	\N	\N	\N	Chloroherpeton	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1823	252	Chlorobium	2161	\N	\N	\N	\N	Chlorobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1824	252	Chlorobaculum	2158	\N	\N	\N	\N	Chlorobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1825	253	Chlamydophila	2150	\N	\N	\N	\N	Chlamydophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1826	253	Chlamydia	2146	\N	\N	\N	\N	Chlamydia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1827	254	Terrimonas	2142	\N	\N	\N	\N	Terrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1828	254	Segetibacter	2140	\N	\N	\N	\N	Segetibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1829	254	Sediminibacterium	2138	\N	\N	\N	\N	Sediminibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1830	254	Parasegetibacter	2136	\N	\N	\N	\N	Parasegetibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1831	254	Niastella	2132	\N	\N	\N	\N	Niastella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1832	254	Niabella	2127	\N	\N	\N	\N	Niabella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1833	254	Lacibacter	2125	\N	\N	\N	\N	Lacibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1834	254	Hydrotalea	2123	\N	\N	\N	\N	Hydrotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1835	254	Flavitalea	2121	\N	\N	\N	\N	Flavitalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1836	254	Flavisolibacter	2118	\N	\N	\N	\N	Flavisolibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1837	254	Filimonas	2116	\N	\N	\N	\N	Filimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1838	254	Ferruginibacter	2113	\N	\N	\N	\N	Ferruginibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1839	254	Chitinophaga	2099	\N	\N	\N	\N	Chitinophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1840	254	Balneola	2097	\N	\N	\N	\N	Balneola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1841	255	Tropheryma	2094	\N	\N	\N	\N	Tropheryma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1842	255	Paraoerskovia	2092	\N	\N	\N	\N	Paraoerskovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1843	255	Oerskovia	2087	\N	\N	\N	\N	Oerskovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1844	255	Cellulomonas	2071	\N	\N	\N	\N	Cellulomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1845	255	Actinotalea	2069	\N	\N	\N	\N	Actinotalea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1846	256	Celerinatantimonas	2066	\N	\N	\N	\N	Celerinatantimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1847	257	Phenylobacterium	2056	\N	\N	\N	\N	Phenylobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1848	257	Caulobacter	2049	\N	\N	\N	\N	Caulobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1849	257	Brevundimonas	2027	\N	\N	\N	\N	Brevundimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1850	257	Asticcacaulis	2022	\N	\N	\N	\N	Asticcacaulis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1851	258	Catenulispora	2016	\N	\N	\N	\N	Catenulispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1852	259	Trichococcus	2009	\N	\N	\N	\N	Trichococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1853	259	Pisciglobus	2007	\N	\N	\N	\N	Pisciglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1854	259	Marinilactibacillus	2004	\N	\N	\N	\N	Marinilactibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1855	259	Lacticigenium	2002	\N	\N	\N	\N	Lacticigenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1856	259	Isobaculum	2000	\N	\N	\N	\N	Isobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1857	259	Granulicatella	1998	\N	\N	\N	\N	Granulicatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1858	259	Dolosigranulum	1996	\N	\N	\N	\N	Dolosigranulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1859	259	Desemzia	1994	\N	\N	\N	\N	Desemzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1860	259	Carnobacterium	1984	\N	\N	\N	\N	Carnobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1861	259	Atopostipes	1982	\N	\N	\N	\N	Atopostipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1862	259	Atopococcus	1980	\N	\N	\N	\N	Atopococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1863	259	Atopobacter	1978	\N	\N	\N	\N	Atopobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1864	259	Alloiococcus	1976	\N	\N	\N	\N	Alloiococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1865	259	Allofustis	1974	\N	\N	\N	\N	Allofustis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1866	259	Alkalibacterium	1964	\N	\N	\N	\N	Alkalibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1867	260	Suttonella	1960	\N	\N	\N	\N	Suttonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1868	260	Cardiobacterium	1957	\N	\N	\N	\N	Cardiobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1869	261	Sulfurospirillum	1950	\N	\N	\N	\N	Sulfurospirillum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1870	261	Campylobacter	1935	\N	\N	\N	\N	Campylobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1871	261	Arcobacter	1924	\N	\N	\N	\N	Arcobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1872	262	Caldisericum	1921	\N	\N	\N	\N	Caldisericum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1873	263	Caldilinea	1917	\N	\N	\N	\N	Caldilinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1874	264	Caldicoprobacter	1913	\N	\N	\N	\N	Caldicoprobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1875	265	Xylophilus	1910	\N	\N	\N	\N	Xylophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1876	265	Thiomonas	1903	\N	\N	\N	\N	Thiomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1877	265	Thiobacter	1901	\N	\N	\N	\N	Thiobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1878	265	Tepidimonas	1896	\N	\N	\N	\N	Tepidimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1879	265	Sphaerotilus	1891	\N	\N	\N	\N	Sphaerotilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1880	265	Rubrivivax	1888	\N	\N	\N	\N	Rubrivivax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1881	265	Rivibacter	1886	\N	\N	\N	\N	Rivibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1882	265	Piscinibacter	1884	\N	\N	\N	\N	Piscinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1883	265	Paucibacter	1882	\N	\N	\N	\N	Paucibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1884	265	Mitsuaria	1880	\N	\N	\N	\N	Mitsuaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1885	265	Methylibium	1878	\N	\N	\N	\N	Methylibium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1886	265	Leptothrix	1875	\N	\N	\N	\N	Leptothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1887	265	Inhella	1872	\N	\N	\N	\N	Inhella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1888	265	Ideonella	1870	\N	\N	\N	\N	Ideonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1889	265	Aquincola	1868	\N	\N	\N	\N	Aquincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1890	265	Aquabacterium	1862	\N	\N	\N	\N	Aquabacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1891	266	Wautersia	1859	\N	\N	\N	\N	Wautersia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1892	266	Thermothrix	1857	\N	\N	\N	\N	Thermothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1893	266	Ralstonia	1851	\N	\N	\N	\N	Ralstonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1894	266	Polynucleobacter	1844	\N	\N	\N	\N	Polynucleobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1895	266	Paucimonas	1842	\N	\N	\N	\N	Paucimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1896	266	Pandoraea	1835	\N	\N	\N	\N	Pandoraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1897	266	Limnobacter	1832	\N	\N	\N	\N	Limnobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1898	266	Lautropia	1830	\N	\N	\N	\N	Lautropia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1899	266	Cupriavidus	1818	\N	\N	\N	\N	Cupriavidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1900	266	Chitinimonas	1815	\N	\N	\N	\N	Chitinimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1901	266	Burkholderia	1760	\N	\N	\N	\N	Burkholderia<Burkholderiaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
1902	267	Pseudochrobactrum	1754	\N	\N	\N	\N	Pseudochrobactrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1903	267	Paenochrobactrum	1751	\N	\N	\N	\N	Paenochrobactrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1904	267	Ochrobactrum	1733	\N	\N	\N	\N	Ochrobactrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1905	267	Mycoplana	1731	\N	\N	\N	\N	Mycoplana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1906	267	Daeguia	1729	\N	\N	\N	\N	Daeguia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1907	267	Brucella	1718	\N	\N	\N	\N	Brucella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1908	268	Brevinema	1715	\N	\N	\N	\N	Brevinema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1909	269	Brevibacterium	1691	\N	\N	\N	\N	Brevibacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1910	270	Salinarimonas	1687	\N	\N	\N	\N	Salinarimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1911	270	Rhodopseudomonas	1679	\N	\N	\N	\N	Rhodopseudomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1912	270	Rhodoblastus	1676	\N	\N	\N	\N	Rhodoblastus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1913	270	Oligotropha	1674	\N	\N	\N	\N	Oligotropha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1914	270	Nitrobacter	1669	\N	\N	\N	\N	Nitrobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1915	270	Bradyrhizobium	1656	\N	\N	\N	\N	Bradyrhizobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1916	270	Bosea	1650	\N	\N	\N	\N	Bosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1917	270	Blastobacter	1648	\N	\N	\N	\N	Blastobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1918	270	Afipia	1642	\N	\N	\N	\N	Afipia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1919	271	Brachyspira	1633	\N	\N	\N	\N	Brachyspira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1920	272	Georgenia	1626	\N	\N	\N	\N	Georgenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1921	272	Bogoriella	1624	\N	\N	\N	\N	Bogoriella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1922	273	Scardovia	1620	\N	\N	\N	\N	Scardovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1923	273	Parascardovia	1618	\N	\N	\N	\N	Parascardovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1924	273	Metascardovia	1616	\N	\N	\N	\N	Metascardovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1925	273	Gardnerella	1614	\N	\N	\N	\N	Gardnerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1926	273	Bifidobacterium	1571	\N	\N	\N	\N	Bifidobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1927	273	Alloscardovia	1569	\N	\N	\N	\N	Alloscardovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1928	273	Aeriscardovia	1567	\N	\N	\N	\N	Aeriscardovia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1929	274	Serinibacter	1564	\N	\N	\N	\N	Serinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1930	274	Salana	1562	\N	\N	\N	\N	Salana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1931	274	Miniimonas	1560	\N	\N	\N	\N	Miniimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1932	274	Beutenbergia	1558	\N	\N	\N	\N	Beutenbergia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1933	275	Chitinivorax	1555	\N	\N	\N	\N	Chitinivorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1934	276	Methylovirgula	1552	\N	\N	\N	\N	Methylovirgula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1935	276	Methylorosula	1550	\N	\N	\N	\N	Methylorosula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1936	276	Methyloferula	1548	\N	\N	\N	\N	Methyloferula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1937	276	Methylocella	1544	\N	\N	\N	\N	Methylocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1938	276	Methylocapsa	1541	\N	\N	\N	\N	Methylocapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1939	276	Chelatococcus	1538	\N	\N	\N	\N	Chelatococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1940	276	Camelimonas	1535	\N	\N	\N	\N	Camelimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1941	276	Beijerinckia	1527	\N	\N	\N	\N	Beijerinckia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1942	277	Vampirovibrio	1524	\N	\N	\N	\N	Vampirovibrio	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1943	278	Bartonella	1499	\N	\N	\N	\N	Bartonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1944	279	Prolixibacter	1496	\N	\N	\N	\N	Prolixibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1945	279	Ohtaekwangia	1493	\N	\N	\N	\N	Ohtaekwangia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1946	279	Marinifilum	1491	\N	\N	\N	\N	Marinifilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1947	280	Sunxiuqinia	1488	\N	\N	\N	\N	Sunxiuqinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1948	280	Phocaeicola	1486	\N	\N	\N	\N	Phocaeicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1949	281	Bacteroides	1452	\N	\N	\N	\N	Bacteroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1950	281	Anaerorhabdus	1450	\N	\N	\N	\N	Anaerorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1951	281	Acetomicrobium	1447	\N	\N	\N	\N	Acetomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1952	282	Peredibacter	1444	\N	\N	\N	\N	Peredibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1953	282	Bacteriovorax	1441	\N	\N	\N	\N	Bacteriovorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1954	283	Solibacillus	1438	\N	\N	\N	\N	Solibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1955	283	Rummeliibacillus	1435	\N	\N	\N	\N	Rummeliibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1956	283	Geomicrobium	1433	\N	\N	\N	\N	Geomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1957	283	Gemella	1427	\N	\N	\N	\N	Gemella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1958	283	Exiguobacterium	1415	\N	\N	\N	\N	Exiguobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1959	284	Vulcanibacillus	1412	\N	\N	\N	\N	Vulcanibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1960	284	Viridibacillus	1409	\N	\N	\N	\N	Viridibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1961	284	Virgibacillus	1385	\N	\N	\N	\N	Virgibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1962	284	Thalassobacillus	1380	\N	\N	\N	\N	Thalassobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1963	284	Terribacillus	1375	\N	\N	\N	\N	Terribacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1964	284	Tenuibacillus	1373	\N	\N	\N	\N	Tenuibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1965	284	Streptohalobacillus	1371	\N	\N	\N	\N	Streptohalobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1966	284	Sediminibacillus	1369	\N	\N	\N	\N	Sediminibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1967	284	Salsuginibacillus	1366	\N	\N	\N	\N	Salsuginibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1968	284	Salirhabdus	1364	\N	\N	\N	\N	Salirhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1969	284	Salinibacillus	1361	\N	\N	\N	\N	Salinibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1970	284	Salimicrobium	1355	\N	\N	\N	\N	Salimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1971	284	Saccharococcus	1353	\N	\N	\N	\N	Saccharococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1972	284	Psychrobacillus	1349	\N	\N	\N	\N	Psychrobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1973	284	Pontibacillus	1345	\N	\N	\N	\N	Pontibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1974	284	Piscibacillus	1342	\N	\N	\N	\N	Piscibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1975	284	Paraliobacillus	1339	\N	\N	\N	\N	Paraliobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1976	284	Ornithinibacillus	1335	\N	\N	\N	\N	Ornithinibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1977	284	Oceanobacillus	1323	\N	\N	\N	\N	Oceanobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1978	284	Natribacillus	1321	\N	\N	\N	\N	Natribacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1979	284	Microaerobacter	1319	\N	\N	\N	\N	Microaerobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1980	284	Marinococcus	1315	\N	\N	\N	\N	Marinococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1981	284	Lysinibacillus	1309	\N	\N	\N	\N	Lysinibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1982	284	Lentibacillus	1300	\N	\N	\N	\N	Lentibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1983	284	Halolactibacillus	1296	\N	\N	\N	\N	Halolactibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1984	284	Halobacillus	1278	\N	\N	\N	\N	Halobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1985	284	Halalkalibacillus	1276	\N	\N	\N	\N	Halalkalibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1986	284	Gracilibacillus	1266	\N	\N	\N	\N	Gracilibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1987	284	Geobacillus	1252	\N	\N	\N	\N	Geobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1988	284	Filobacillus	1250	\N	\N	\N	\N	Filobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1989	284	Falsibacillus	1248	\N	\N	\N	\N	Falsibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1990	284	Cerasibacillus	1246	\N	\N	\N	\N	Cerasibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1991	284	Calditerricola	1243	\N	\N	\N	\N	Calditerricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1992	284	Caldibacillus	1241	\N	\N	\N	\N	Caldibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1993	284	Caldalkalibacillus	1238	\N	\N	\N	\N	Caldalkalibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1994	284	Bacillus	1082	\N	\N	\N	\N	Bacillus<Bacillaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
1995	284	Aquisalibacillus	1080	\N	\N	\N	\N	Aquisalibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1996	284	Anoxybacillus	1067	\N	\N	\N	\N	Anoxybacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1997	284	Anaerobacillus	1063	\N	\N	\N	\N	Anaerobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1998	284	Amphibacillus	1059	\N	\N	\N	\N	Amphibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
1999	284	Allobacillus	1057	\N	\N	\N	\N	Allobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2000	284	Alkalibacillus	1051	\N	\N	\N	\N	Alkalibacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2001	284	Aeribacillus	1049	\N	\N	\N	\N	Aeribacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2002	285	Martelella	1046	\N	\N	\N	\N	Martelella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2003	285	Fulvimarina	1044	\N	\N	\N	\N	Fulvimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2004	285	Aureimonas	1040	\N	\N	\N	\N	Aureimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2005	285	Aurantimonas	1037	\N	\N	\N	\N	Aurantimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2006	286	Armatimonas	1034	\N	\N	\N	\N	Armatimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2007	287	Thermocrinis	1029	\N	\N	\N	\N	Thermocrinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2008	287	Hydrogenobacter	1025	\N	\N	\N	\N	Hydrogenobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2009	287	Hydrogenivirga	1022	\N	\N	\N	\N	Hydrogenivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2010	287	Aquifex	1020	\N	\N	\N	\N	Aquifex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2011	288	Wolbachia	1017	\N	\N	\N	\N	Wolbachia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2012	288	Neorickettsia	1014	\N	\N	\N	\N	Neorickettsia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2013	288	Ehrlichia	1009	\N	\N	\N	\N	Ehrlichia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2014	288	Anaplasma	1007	\N	\N	\N	\N	Anaplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2015	289	Asteroleplasma	1004	\N	\N	\N	\N	Asteroleplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2016	289	Anaeroplasma	1000	\N	\N	\N	\N	Anaeroplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2017	290	Longilinea	997	\N	\N	\N	\N	Longilinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2018	290	Levilinea	995	\N	\N	\N	\N	Levilinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2019	290	Leptolinea	993	\N	\N	\N	\N	Leptolinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2020	290	Bellilinea	991	\N	\N	\N	\N	Bellilinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2021	290	Anaerolinea	988	\N	\N	\N	\N	Anaerolinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2022	291	Teredinibacter	985	\N	\N	\N	\N	Teredinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2023	291	Pseudoteredinibacter	983	\N	\N	\N	\N	Pseudoteredinibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2024	291	Maricurvus	981	\N	\N	\N	\N	Maricurvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2025	291	Gilvimarinus	979	\N	\N	\N	\N	Gilvimarinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2026	291	Eionea	977	\N	\N	\N	\N	Eionea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2027	292	Saccharophagus	974	\N	\N	\N	\N	Saccharophagus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2028	292	Microbulbifer	958	\N	\N	\N	\N	Microbulbifer	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2029	292	Marinobacter	928	\N	\N	\N	\N	Marinobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2030	292	Marinobacterium	918	\N	\N	\N	\N	Marinobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2031	292	Marinimicrobium	914	\N	\N	\N	\N	Marinimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2032	292	Haliea	910	\N	\N	\N	\N	Haliea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2033	292	Glaciecola	900	\N	\N	\N	\N	Glaciecola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2034	292	Bowmanella	897	\N	\N	\N	\N	Bowmanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2035	292	Alteromonas	888	\N	\N	\N	\N	Alteromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2036	292	Alishewanella	882	\N	\N	\N	\N	Alishewanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2037	292	Aliagarivorans	879	\N	\N	\N	\N	Aliagarivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2038	292	Agarivorans	876	\N	\N	\N	\N	Agarivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2039	292	Aestuariibacter	872	\N	\N	\N	\N	Aestuariibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2040	293	Rhizomicrobium	868	\N	\N	\N	\N	Rhizomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2041	293	Geminicoccus	866	\N	\N	\N	\N	Geminicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2042	293	Breoghania	864	\N	\N	\N	\N	Breoghania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2043	294	Tumebacillus	860	\N	\N	\N	\N	Tumebacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2044	294	Kyrpidia	858	\N	\N	\N	\N	Kyrpidia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2045	294	Alicyclobacillus	836	\N	\N	\N	\N	Alicyclobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2046	295	Kangiella	829	\N	\N	\N	\N	Kangiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2047	295	Alcanivorax	821	\N	\N	\N	\N	Alcanivorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2048	296	Taylorella	817	\N	\N	\N	\N	Taylorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2049	296	Pusillimonas	813	\N	\N	\N	\N	Pusillimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2050	296	Pigmentiphaga	809	\N	\N	\N	\N	Pigmentiphaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2051	296	Pelistega	807	\N	\N	\N	\N	Pelistega	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2052	296	Parapusillimonas	805	\N	\N	\N	\N	Parapusillimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2053	296	Paralcaligenes	803	\N	\N	\N	\N	Paralcaligenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2054	296	Paenalcaligenes	801	\N	\N	\N	\N	Paenalcaligenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2055	296	Oligella	798	\N	\N	\N	\N	Oligella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2056	296	Kerstersia	796	\N	\N	\N	\N	Kerstersia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2057	296	Derxia	794	\N	\N	\N	\N	Derxia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2058	296	Castellaniella	788	\N	\N	\N	\N	Castellaniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2059	296	Candidimonas	785	\N	\N	\N	\N	Candidimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2060	296	Brackiella	783	\N	\N	\N	\N	Brackiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2061	296	Bordetella	774	\N	\N	\N	\N	Bordetella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2062	296	Azohydromonas	771	\N	\N	\N	\N	Azohydromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2063	296	Alcaligenes	767	\N	\N	\N	\N	Alcaligenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2064	296	Advenella	765	\N	\N	\N	\N	Advenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2065	296	Achromobacter	760	\N	\N	\N	\N	Achromobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2066	297	Akkermansia	757	\N	\N	\N	\N	Akkermansia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2067	298	Zobellella	752	\N	\N	\N	\N	Zobellella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2068	298	Tolumonas	749	\N	\N	\N	\N	Tolumonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2069	298	Oceanisphaera	743	\N	\N	\N	\N	Oceanisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2070	298	Oceanimonas	740	\N	\N	\N	\N	Oceanimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2071	298	Aeromonas	710	\N	\N	\N	\N	Aeromonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2072	299	Globicatella	707	\N	\N	\N	\N	Globicatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2073	299	Facklamia	702	\N	\N	\N	\N	Facklamia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2074	299	Dolosicoccus	700	\N	\N	\N	\N	Dolosicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2075	299	Aerococcus	695	\N	\N	\N	\N	Aerococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2076	300	Actinospica	691	\N	\N	\N	\N	Actinospica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2077	301	Actinopolyspora	684	\N	\N	\N	\N	Actinopolyspora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2078	302	Varibaculum	681	\N	\N	\N	\N	Varibaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2079	302	Trueperella	677	\N	\N	\N	\N	Trueperella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2080	302	Mobiluncus	674	\N	\N	\N	\N	Mobiluncus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2081	302	Arcanobacterium	669	\N	\N	\N	\N	Arcanobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2082	302	Actinomyces	644	\N	\N	\N	\N	Actinomyces	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2083	302	Actinobaculum	639	\N	\N	\N	\N	Actinobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2084	303	Acidothermus	636	\N	\N	\N	\N	Acidothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2085	304	Terriglobus	632	\N	\N	\N	\N	Terriglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2086	304	Telmatobacter	630	\N	\N	\N	\N	Telmatobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2087	304	Granulicella	625	\N	\N	\N	\N	Granulicella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2088	304	Edaphobacter	622	\N	\N	\N	\N	Edaphobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2089	304	Bryocella	620	\N	\N	\N	\N	Bryocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2090	304	Acidobacterium	618	\N	\N	\N	\N	Acidobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2091	304	Acidicapsa	615	\N	\N	\N	\N	Acidicapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2092	305	Bryobacter	612	\N	\N	\N	\N	Bryobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2093	306	Acidithiobacillus	605	\N	\N	\N	\N	Acidithiobacillus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2094	307	Aciditerrimonas	602	\N	\N	\N	\N	Aciditerrimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2095	308	Ilumatobacter	599	\N	\N	\N	\N	Ilumatobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2096	308	Ferrimicrobium	597	\N	\N	\N	\N	Ferrimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2097	308	Acidimicrobium	595	\N	\N	\N	\N	Acidimicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2098	309	Succinispira	592	\N	\N	\N	\N	Succinispira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2099	309	Succiniclasticum	590	\N	\N	\N	\N	Succiniclasticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2100	309	Phascolarctobacterium	587	\N	\N	\N	\N	Phascolarctobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2101	309	Acidaminococcus	584	\N	\N	\N	\N	Acidaminococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2102	310	Acholeplasma	568	\N	\N	\N	\N	Acholeplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2103	311	Tanticharoenia	565	\N	\N	\N	\N	Tanticharoenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2104	311	Swaminathania	563	\N	\N	\N	\N	Swaminathania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2105	311	Stella	560	\N	\N	\N	\N	Stella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2106	311	Saccharibacter	558	\N	\N	\N	\N	Saccharibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2107	311	Rubritepida	556	\N	\N	\N	\N	Rubritepida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2108	311	Roseomonas	540	\N	\N	\N	\N	Roseomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2109	311	Roseococcus	537	\N	\N	\N	\N	Roseococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2110	311	Rhodovarius	535	\N	\N	\N	\N	Rhodovarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2111	311	Rhodopila	533	\N	\N	\N	\N	Rhodopila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2112	311	Paracraurococcus	531	\N	\N	\N	\N	Paracraurococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2113	311	Neokomagataea	528	\N	\N	\N	\N	Neokomagataea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2114	311	Neoasaia	526	\N	\N	\N	\N	Neoasaia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2115	311	Kozakia	524	\N	\N	\N	\N	Kozakia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2116	311	Granulibacter	522	\N	\N	\N	\N	Granulibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2117	311	Gluconobacter	508	\N	\N	\N	\N	Gluconobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2118	311	Gluconacetobacter	487	\N	\N	\N	\N	Gluconacetobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2119	311	Craurococcus	485	\N	\N	\N	\N	Craurococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2120	311	Belnapia	482	\N	\N	\N	\N	Belnapia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2121	311	Asaia	473	\N	\N	\N	\N	Asaia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2122	311	Ameyamaea	471	\N	\N	\N	\N	Ameyamaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2123	311	Acidomonas	469	\N	\N	\N	\N	Acidomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2124	311	Acidocella	465	\N	\N	\N	\N	Acidocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2125	311	Acidisphaera	463	\N	\N	\N	\N	Acidisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2126	311	Acidisoma	460	\N	\N	\N	\N	Acidisoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2127	311	Acidiphilium	453	\N	\N	\N	\N	Acidiphilium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2128	311	Acidicaldus	451	\N	\N	\N	\N	Acidicaldus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2129	311	Acetobacter	429	\N	\N	\N	\N	Acetobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2130	312	Acanthopleuribacter	426	\N	\N	\N	\N	Acanthopleuribacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2131	313	Lokiarchaeum	87180	\N	\N	\N	\N	Lokiarchaeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2132	314	Marine Group II	422	\N	\N	\N	\N	Marine Group II	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2133	315	Vulcanisaeta	418	\N	\N	\N	\N	Vulcanisaeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2134	315	Thermoproteus	415	\N	\N	\N	\N	Thermoproteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2135	315	Thermocladium	413	\N	\N	\N	\N	Thermocladium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2136	315	Pyrobaculum	408	\N	\N	\N	\N	Pyrobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2137	315	Caldivirga	406	\N	\N	\N	\N	Caldivirga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2138	316	Thermoplasma	402	\N	\N	\N	\N	Thermoplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2139	317	Thermofilum	399	\N	\N	\N	\N	Thermofilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2140	318	Thermococcus	374	\N	\N	\N	\N	Thermococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2141	318	Pyrococcus	369	\N	\N	\N	\N	Pyrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2142	318	Palaeococcus	366	\N	\N	\N	\N	Palaeococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2143	319	Sulfurisphaera	363	\N	\N	\N	\N	Sulfurisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2144	319	Sulfolobus	356	\N	\N	\N	\N	Sulfolobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2145	319	Stygiolobus	354	\N	\N	\N	\N	Stygiolobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2146	319	Metallosphaera	349	\N	\N	\N	\N	Metallosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2147	319	Acidianus	344	\N	\N	\N	\N	Acidianus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2148	320	Pyrodictium	341	\N	\N	\N	\N	Pyrodictium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2149	321	Picrophilus	337	\N	\N	\N	\N	Picrophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2150	322	Methanothermus	334	\N	\N	\N	\N	Methanothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2151	323	Methanosarcina	324	\N	\N	\N	\N	Methanosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2152	323	Methanosalsum	322	\N	\N	\N	\N	Methanosalsum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2153	323	Methanomethylovorans	319	\N	\N	\N	\N	Methanomethylovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2154	323	Methanolobus	312	\N	\N	\N	\N	Methanolobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2155	323	Methanohalophilus	309	\N	\N	\N	\N	Methanohalophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2156	323	Methanohalobium	307	\N	\N	\N	\N	Methanohalobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2157	323	Methanococcoides	303	\N	\N	\N	\N	Methanococcoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2158	323	Methanimicrococcus	301	\N	\N	\N	\N	Methanimicrococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2159	324	Methanosaeta	297	\N	\N	\N	\N	Methanosaeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2160	325	Methanosphaerula	294	\N	\N	\N	\N	Methanosphaerula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2161	325	Methanoregula	291	\N	\N	\N	\N	Methanoregula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2162	325	Methanolinea	288	\N	\N	\N	\N	Methanolinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2163	326	Methanopyrus	285	\N	\N	\N	\N	Methanopyrus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2164	327	Methanomassiliicoccus	282	\N	\N	\N	\N	Methanomassiliicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2165	328	Methanocalculus	278	\N	\N	\N	\N	Methanocalculus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2166	329	Methanoplanus	273	\N	\N	\N	\N	Methanoplanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2167	329	Methanomicrobium	271	\N	\N	\N	\N	Methanomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2168	329	Methanogenium	266	\N	\N	\N	\N	Methanogenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2169	329	Methanofollis	261	\N	\N	\N	\N	Methanofollis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2170	329	Methanoculleus	254	\N	\N	\N	\N	Methanoculleus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2171	330	Methanocorpusculum	250	\N	\N	\N	\N	Methanocorpusculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2172	331	Methanothermococcus	246	\N	\N	\N	\N	Methanothermococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2173	331	Methanococcus	244	\N	\N	\N	\N	Methanococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2174	332	Methanocella	239	\N	\N	\N	\N	Methanocella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2175	333	Methanotorris	236	\N	\N	\N	\N	Methanotorris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2176	333	Methanocaldococcus	229	\N	\N	\N	\N	Methanocaldococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2177	334	Methanothermobacter	221	\N	\N	\N	\N	Methanothermobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2178	334	Methanosphaera	219	\N	\N	\N	\N	Methanosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2179	334	Methanobrevibacter	216	\N	\N	\N	\N	Methanobrevibacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2180	334	Methanobacterium	200	\N	\N	\N	\N	Methanobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2181	335	Salarchaeum	197	\N	\N	\N	\N	Salarchaeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2182	335	Natronorubrum	192	\N	\N	\N	\N	Natronorubrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2183	335	Natronomonas	190	\N	\N	\N	\N	Natronomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2184	335	Natronolimnobius	187	\N	\N	\N	\N	Natronolimnobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2185	335	Natronococcus	183	\N	\N	\N	\N	Natronococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2186	335	Natronobacterium	181	\N	\N	\N	\N	Natronobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2187	335	Natronoarchaeum	179	\N	\N	\N	\N	Natronoarchaeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2188	335	Natrinema	172	\N	\N	\N	\N	Natrinema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2189	335	Natrialba	165	\N	\N	\N	\N	Natrialba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2190	335	Halovenus	163	\N	\N	\N	\N	Halovenus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2191	335	Haloterrigena	154	\N	\N	\N	\N	Haloterrigena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2192	335	Halostagnicola	151	\N	\N	\N	\N	Halostagnicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2193	335	Halosimplex	149	\N	\N	\N	\N	Halosimplex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2194	335	Halosarcina	147	\N	\N	\N	\N	Halosarcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2195	335	Halorubrum	124	\N	\N	\N	\N	Halorubrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2196	335	Halorientalis	122	\N	\N	\N	\N	Halorientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2197	335	Halorhabdus	119	\N	\N	\N	\N	Halorhabdus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2198	335	Haloquadratum	117	\N	\N	\N	\N	Haloquadratum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2199	335	Haloplanus	113	\N	\N	\N	\N	Haloplanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2200	335	Halopiger	111	\N	\N	\N	\N	Halopiger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2201	335	Halopenitus	109	\N	\N	\N	\N	Halopenitus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2202	335	Halopelagius	107	\N	\N	\N	\N	Halopelagius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2203	335	Halomicrobium	103	\N	\N	\N	\N	Halomicrobium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2204	335	Halomarina	101	\N	\N	\N	\N	Halomarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2205	335	Halolamina	99	\N	\N	\N	\N	Halolamina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2206	335	Halogranum	94	\N	\N	\N	\N	Halogranum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2207	335	Halogeometricum	91	\N	\N	\N	\N	Halogeometricum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2208	335	Haloferax	82	\N	\N	\N	\N	Haloferax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2209	335	Halococcus	76	\N	\N	\N	\N	Halococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2210	335	Halobiforma	72	\N	\N	\N	\N	Halobiforma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2211	335	Halobellus	68	\N	\N	\N	\N	Halobellus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2212	335	Halobaculum	66	\N	\N	\N	\N	Halobaculum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2213	335	Halobacterium	62	\N	\N	\N	\N	Halobacterium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2214	335	Haloarcula	52	\N	\N	\N	\N	Haloarcula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2215	335	Haloarchaeobius	50	\N	\N	\N	\N	Haloarchaeobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2216	335	Halarchaeum	48	\N	\N	\N	\N	Halarchaeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2217	335	Halalkalicoccus	46	\N	\N	\N	\N	Halalkalicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2218	335	Haladaptatus	43	\N	\N	\N	\N	Haladaptatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2219	336	Ferroplasma	40	\N	\N	\N	\N	Ferroplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2220	336	Acidiplasma	38	\N	\N	\N	\N	Acidiplasma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2221	337	Thermosphaera	35	\N	\N	\N	\N	Thermosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2222	337	Thermodiscus	33	\N	\N	\N	\N	Thermodiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2223	337	Sulfophobococcus	31	\N	\N	\N	\N	Sulfophobococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2224	337	Staphylothermus	29	\N	\N	\N	\N	Staphylothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2225	337	Ignisphaera	27	\N	\N	\N	\N	Ignisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2226	337	Ignicoccus	25	\N	\N	\N	\N	Ignicoccus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2227	337	Desulfurococcus	22	\N	\N	\N	\N	Desulfurococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2228	338	Caldisphaera	19	\N	\N	\N	\N	Caldisphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2229	339	Geoglobus	15	\N	\N	\N	\N	Geoglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2230	339	Ferroglobus	13	\N	\N	\N	\N	Ferroglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2231	339	Archaeoglobus	7	\N	\N	\N	\N	Archaeoglobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2232	340	Acidilobus	3	\N	\N	\N	\N	Acidilobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2233	341	Stramenopiles X	85350	\N	\N	\N	\N	Stramenopiles X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2234	341	Pseudofungi	85078	\N	\N	\N	\N	Pseudofungi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2235	341	Placididea	85064	\N	\N	\N	\N	Placididea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2236	341	Opalinata	85035	\N	\N	\N	\N	Opalinata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2237	341	Ochrophyta	83251	\N	\N	\N	\N	Ochrophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2238	341	MMETSP	83248	\N	\N	\N	\N	MMETSP<Stramenopiles	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2239	341	MAST lineages	83066	\N	\N	\N	\N	MAST lineages	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2240	341	Labyrinthulea	82967	\N	\N	\N	\N	Labyrinthulea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2241	341	environmental samples	82965	\N	\N	\N	\N	environmental samples<Stramenopiles	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2242	341	Bicoecea	82901	\N	\N	\N	\N	Bicoecea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2243	342	Phytorhiza	82731	\N	\N	\N	\N	Phytorhiza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2244	342	Retaria	81757	\N	\N	\N	\N	Retaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2245	342	Eorhiza	81718	\N	\N	\N	\N	Eorhiza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2246	342	Cercozoa	81032	\N	\N	\N	\N	Cercozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2247	342	Zoorhiza	80820	\N	\N	\N	\N	Zoorhiza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2248	343	Myzozoa	13944	\N	\N	\N	\N	Myzozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2249	343	Colponemea	13925	\N	\N	\N	\N	Colponemea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2250	343	Ciliophora	11835	\N	\N	\N	\N	Ciliophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2251	343	Alveolata X	11833	\N	\N	\N	\N	Alveolata X<Alveolata	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2252	344	Eukaryota D3 X1	85360	\N	\N	\N	\N	Eukaryota D3 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2253	345	Eukaryota D2 X1	85357	\N	\N	\N	\N	Eukaryota D2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2254	346	Eukaryota D1 X1	85354	\N	\N	\N	\N	Eukaryota D1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2255	347	S25 1200 X	86687	\N	\N	\N	\N	S25 1200 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2256	348	Rappemonads X	86663	\N	\N	\N	\N	Rappemonads X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2257	349	Katablepharidida X sp.	85456	\N	\N	\N	\N	Katablepharidida X sp.<Katablepharidida X<Orphans	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2258	350	Telo Group 2	80814	\N	\N	\N	\N	Telo Group 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2259	350	Telo Group 1	80808	\N	\N	\N	\N	Telo Group 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2260	351	Rigifilida U1	80804	\N	\N	\N	\N	Rigifilida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2261	351	Rigifilidae	80801	\N	\N	\N	\N	Rigifilidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2262	351	Micronucleariidae	80798	\N	\N	\N	\N	Micronucleariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2263	352	Planomonas lineage	80791	\N	\N	\N	\N	Planomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2264	352	Planomonadida U2	80788	\N	\N	\N	\N	Planomonadida U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2265	352	Planomonadida U1	80781	\N	\N	\N	\N	Planomonadida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2266	352	Nutomonas lineage	80775	\N	\N	\N	\N	Nutomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2267	352	Fabomonas lineage	80771	\N	\N	\N	\N	Fabomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2268	352	Ancyromonas lineage	80764	\N	\N	\N	\N	Ancyromonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2269	353	Picomonadida X	80761	\N	\N	\N	\N	Picomonadida X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2270	353	Picomonadidae	80758	\N	\N	\N	\N	Picomonadidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2271	354	Palpitomonadidae	80754	\N	\N	\N	\N	Palpitomonadidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2272	355	Microheliellidae	80749	\N	\N	\N	\N	Microheliellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2273	355	Microhelida U1	80746	\N	\N	\N	\N	Microhelida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2274	356	Mantamonadidae	80741	\N	\N	\N	\N	Mantamonadidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2275	357	Roombia lineage	80737	\N	\N	\N	\N	Roombia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2276	357	Leucocryptos lineage	80725	\N	\N	\N	\N	Leucocryptos lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2277	357	Katablepharis lineage	80718	\N	\N	\N	\N	Katablepharis lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2278	357	Katablepharidida U3	80715	\N	\N	\N	\N	Katablepharidida U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2279	357	Katablepharidida U2	80710	\N	\N	\N	\N	Katablepharidida U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2280	357	Katablepharidida U1	80703	\N	\N	\N	\N	Katablepharidida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2281	357	Hatena lineage	80698	\N	\N	\N	\N	Hatena lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2282	358	Prymnesiophyceae	80468	\N	\N	\N	\N	Prymnesiophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2283	358	Pavlovophyceae	80436	\N	\N	\N	\N	Pavlovophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2284	358	Haptophyta U3	80433	\N	\N	\N	\N	Haptophyta U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2285	358	Haptophyta U2	80430	\N	\N	\N	\N	Haptophyta U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2286	358	Haptophyta U1	80427	\N	\N	\N	\N	Haptophyta U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2287	359	Eukaryota U9 X3	80424	\N	\N	\N	\N	Eukaryota U9 X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2288	359	Eukaryota U9 X2	80422	\N	\N	\N	\N	Eukaryota U9 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2289	359	Eukaryota U9 X1	80420	\N	\N	\N	\N	Eukaryota U9 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2290	360	Eukaryota U8 X1	80417	\N	\N	\N	\N	Eukaryota U8 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2291	361	Eukaryota U7 X1	80414	\N	\N	\N	\N	Eukaryota U7 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2292	362	Eukaryota U6 X2	80411	\N	\N	\N	\N	Eukaryota U6 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2293	362	Eukaryota U6 X1	80409	\N	\N	\N	\N	Eukaryota U6 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2294	363	Eukaryota U5 X7	80406	\N	\N	\N	\N	Eukaryota U5 X7	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2295	363	Eukaryota U5 X6	80404	\N	\N	\N	\N	Eukaryota U5 X6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2296	363	Eukaryota U5 X5	80402	\N	\N	\N	\N	Eukaryota U5 X5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2297	363	Eukaryota U5 X4	80400	\N	\N	\N	\N	Eukaryota U5 X4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2298	363	Eukaryota U5 X3	80398	\N	\N	\N	\N	Eukaryota U5 X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2299	363	Eukaryota U5 X2	80396	\N	\N	\N	\N	Eukaryota U5 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2300	363	Eukaryota U5 X1	80394	\N	\N	\N	\N	Eukaryota U5 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2301	364	Eukaryota U4 X3	80391	\N	\N	\N	\N	Eukaryota U4 X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2302	364	Eukaryota U4 X2	80389	\N	\N	\N	\N	Eukaryota U4 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2303	364	Eukaryota U4 X1	80387	\N	\N	\N	\N	Eukaryota U4 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2304	365	Eukaryota U3 X1	80384	\N	\N	\N	\N	Eukaryota U3 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2305	366	Eukaryota U2 X2	80381	\N	\N	\N	\N	Eukaryota U2 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2306	366	Eukaryota U2 X1	80379	\N	\N	\N	\N	Eukaryota U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2307	367	Eukaryota U1 X1	80376	\N	\N	\N	\N	Eukaryota U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2308	368	Eukaryota U17 X2	80373	\N	\N	\N	\N	Eukaryota U17 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2309	368	Eukaryota U17 X1	80371	\N	\N	\N	\N	Eukaryota U17 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2310	369	Eukaryota U16 X1	80368	\N	\N	\N	\N	Eukaryota U16 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2311	370	Eukaryota U15 X1	80365	\N	\N	\N	\N	Eukaryota U15 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2312	371	Eukaryota U14 X1	80362	\N	\N	\N	\N	Eukaryota U14 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2313	372	Eukaryota U12 X1	80359	\N	\N	\N	\N	Eukaryota U12 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2314	373	Eukaryota U11 X1	80356	\N	\N	\N	\N	Eukaryota U11 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2315	374	Eukaryota U10 X1	80353	\N	\N	\N	\N	Eukaryota U10 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2316	375	Collodictyonidae	80347	\N	\N	\N	\N	Collodictyonidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2317	376	Cryptophyta X	86682	\N	\N	\N	\N	Cryptophyta X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2318	376	Pyrenomonadales	80343	\N	\N	\N	\N	Pyrenomonadales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2319	376	Goniomonadales	80329	\N	\N	\N	\N	Goniomonadales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2320	376	Cryptophyta U8	80326	\N	\N	\N	\N	Cryptophyta U8	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2321	376	Cryptophyta U7	80323	\N	\N	\N	\N	Cryptophyta U7	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2322	376	Cryptophyta U6	80320	\N	\N	\N	\N	Cryptophyta U6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2323	376	Cryptophyta U5	80317	\N	\N	\N	\N	Cryptophyta U5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2324	376	Cryptophyta U4	80314	\N	\N	\N	\N	Cryptophyta U4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2325	376	Cryptophyta U3	80305	\N	\N	\N	\N	Cryptophyta U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2326	376	Cryptophyta U2	80300	\N	\N	\N	\N	Cryptophyta U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2327	376	Cryptophyta U1	80297	\N	\N	\N	\N	Cryptophyta U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2328	376	Cryptomonadales	80192	\N	\N	\N	\N	Cryptomonadales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2329	377	Raphidiophryidae	80184	\N	\N	\N	\N	Raphidiophryidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2330	377	Pterocystidae	80139	\N	\N	\N	\N	Pterocystidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2331	377	Oxnerellidae	80136	\N	\N	\N	\N	Oxnerellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2332	377	Marophryidae	80133	\N	\N	\N	\N	Marophryidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2333	377	Heterophryidae	80099	\N	\N	\N	\N	Heterophryidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2334	377	Choanocystidae	80058	\N	\N	\N	\N	Choanocystidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2335	377	Centrohelida U2	80055	\N	\N	\N	\N	Centrohelida U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2336	377	Centrohelida U1	80052	\N	\N	\N	\N	Centrohelida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2337	377	Acanthocystidae	80043	\N	\N	\N	\N	Acanthocystidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2338	378	Subulatomonas lineage	80028	\N	\N	\N	\N	Subulatomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2339	378	Pigsuia lineage	80023	\N	\N	\N	\N	Pigsuia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2340	378	Breviatida U6	80020	\N	\N	\N	\N	Breviatida U6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2341	378	Breviatida U5	80017	\N	\N	\N	\N	Breviatida U5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2342	378	Breviatida U4	80014	\N	\N	\N	\N	Breviatida U4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2343	378	Breviatida U3	80011	\N	\N	\N	\N	Breviatida U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2344	378	Breviatida U2	80008	\N	\N	\N	\N	Breviatida U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2345	378	Breviatida U1	80003	\N	\N	\N	\N	Breviatida U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2346	378	Breviata lineage	79995	\N	\N	\N	\N	Breviata lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2347	379	Thecamonas 3 lineage	79991	\N	\N	\N	\N	Thecamonas 3 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2348	379	Thecamonas 2 lineage	79988	\N	\N	\N	\N	Thecamonas 2 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2349	379	Thecamonas 1 lineage	79982	\N	\N	\N	\N	Thecamonas 1 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2350	379	Podomonas lineage	79977	\N	\N	\N	\N	Podomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2351	379	Multimonas lineage	79974	\N	\N	\N	\N	Multimonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2352	379	Manchomonas lineage	79967	\N	\N	\N	\N	Manchomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2353	379	Apusomonas lineage	79961	\N	\N	\N	\N	Apusomonas lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2354	379	Apusomonadida U11	79958	\N	\N	\N	\N	Apusomonadida U11	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2355	379	Apusomonadida U10	79955	\N	\N	\N	\N	Apusomonadida U10	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2356	379	Apusomonadida U09	79950	\N	\N	\N	\N	Apusomonadida U09	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2357	379	Apusomonadida U08	79947	\N	\N	\N	\N	Apusomonadida U08	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2358	379	Apusomonadida U07	79944	\N	\N	\N	\N	Apusomonadida U07	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2359	379	Apusomonadida U06	79939	\N	\N	\N	\N	Apusomonadida U06	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2360	379	Apusomonadida U05	79936	\N	\N	\N	\N	Apusomonadida U05	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2361	379	Apusomonadida U04	79933	\N	\N	\N	\N	Apusomonadida U04	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2362	379	Apusomonadida U03	79930	\N	\N	\N	\N	Apusomonadida U03	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2363	379	Apusomonadida U02	79927	\N	\N	\N	\N	Apusomonadida U02	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2364	379	Apusomonadida U01	79924	\N	\N	\N	\N	Apusomonadida U01	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2365	381	Opisthokonta XX	79917	\N	\N	\N	\N	Opisthokonta XX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2366	381	Opisthokonta X	79915	\N	\N	\N	\N	Opisthokonta X<Opisthokonta X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2368	382	Ichthyosporea	40343	\N	\N	\N	\N	Ichthyosporea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2369	382	Filasterea	40336	\N	\N	\N	\N	Filasterea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2370	382	Choanozoa	40248	\N	\N	\N	\N	Choanozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2371	383	Fungi	29402	\N	\N	\N	\N	Fungi<Holomycota	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2372	383	Cristidiscoidea	29369	\N	\N	\N	\N	Cristidiscoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2373	384	Preaxostyla	29328	\N	\N	\N	\N	Preaxostyla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2374	384	Parabasalia	29077	\N	\N	\N	\N	Parabasalia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2375	384	Fornicata	29019	\N	\N	\N	\N	Fornicata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2376	385	Malawimonas	29015	\N	\N	\N	\N	Malawimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2377	386	Tsukubamonadida	29011	\N	\N	\N	\N	Tsukubamonadida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2378	386	Soginia lineage	29006	\N	\N	\N	\N	Soginia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2379	386	Jakobida	28995	\N	\N	\N	\N	Jakobida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2380	386	Heterolobosea	28897	\N	\N	\N	\N	Heterolobosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2381	386	Euglenozoa	28411	\N	\N	\N	\N	Euglenozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2382	386	Andalucia lineage	28402	\N	\N	\N	\N	Andalucia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2383	390	UE1	86761	\N	\N	\N	\N	UE1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2384	391	Streptophyta	22261	\N	\N	\N	\N	Streptophyta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2385	391	Chlorophyta	20312	\N	\N	\N	\N	Chlorophyta<Viridiplantae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2386	392	Stylonematophyceae	20292	\N	\N	\N	\N	Stylonematophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2387	392	Rhodophyta X	20288	\N	\N	\N	\N	Rhodophyta X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2388	392	Rhodellophyceae	20273	\N	\N	\N	\N	Rhodellophyceae<Rhodophyta	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
2389	392	Porphyridiophyceae	20257	\N	\N	\N	\N	Porphyridiophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2390	392	Florideophyceae	19022	\N	\N	\N	\N	Florideophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2391	392	Compsopogonophyceae	18994	\N	\N	\N	\N	Compsopogonophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2392	392	Bangiophyceae	18861	\N	\N	\N	\N	Bangiophyceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2393	393	Gloeochaete	18858	\N	\N	\N	\N	Gloeochaete	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2394	393	Glaucocystis	18856	\N	\N	\N	\N	Glaucocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2395	393	Cyanoptyche	18854	\N	\N	\N	\N	Cyanoptyche	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2396	393	Cyanophora	18852	\N	\N	\N	\N	Cyanophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2397	394	Trichosphaerium	18847	\N	\N	\N	\N	Trichosphaerium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2398	395	Vermistella-lineage	18841	\N	\N	\N	\N	Vermistella-lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2399	395	Tubulinea	18679	\N	\N	\N	\N	Tubulinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2400	395	Stygamoeba lineage	18676	\N	\N	\N	\N	Stygamoeba lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2401	395	Squamamoeba lineage	18669	\N	\N	\N	\N	Squamamoeba lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2402	395	Pellitida	18657	\N	\N	\N	\N	Pellitida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2403	395	Lobosa U3	18652	\N	\N	\N	\N	Lobosa U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2404	395	Lobosa U2	18649	\N	\N	\N	\N	Lobosa U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2405	395	Lobosa U1	18635	\N	\N	\N	\N	Lobosa U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2406	395	Himatismenida	18615	\N	\N	\N	\N	Himatismenida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2407	395	Discosea	18494	\N	\N	\N	\N	Discosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2408	395	Centramoebida	18397	\N	\N	\N	\N	Centramoebida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2409	396	Variosea	18230	\N	\N	\N	\N	Variosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2410	396	Macromycetozoa	17832	\N	\N	\N	\N	Macromycetozoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2411	396	Archamoebae	17774	\N	\N	\N	\N	Archamoebae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2412	397	UI13E03 lineage	17770	\N	\N	\N	\N	UI13E03 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2413	397	PRS2 lineage	17767	\N	\N	\N	\N	PRS2 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2414	398	Xylella fastidiosa subsp. multiplex	11830	\N	\N	\N	\N	Xylella fastidiosa subsp. multiplex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2415	398	Xylella fastidiosa subsp. fastidiosa	11829	\N	\N	\N	\N	Xylella fastidiosa subsp. fastidiosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2416	399	Xanthomonas vesicatoria	11827	\N	\N	\N	\N	Xanthomonas vesicatoria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2417	399	Xanthomonas vasicola	11826	\N	\N	\N	\N	Xanthomonas vasicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2418	399	Xanthomonas translucens	11825	\N	\N	\N	\N	Xanthomonas translucens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2419	399	Xanthomonas theicola	11824	\N	\N	\N	\N	Xanthomonas theicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2420	399	Xanthomonas sacchari	11823	\N	\N	\N	\N	Xanthomonas sacchari	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2421	399	Xanthomonas populi	11822	\N	\N	\N	\N	Xanthomonas populi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2422	399	Xanthomonas pisi	11821	\N	\N	\N	\N	Xanthomonas pisi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2423	399	Xanthomonas phaseoli	11820	\N	\N	\N	\N	Xanthomonas phaseoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2424	399	Xanthomonas perforans	11819	\N	\N	\N	\N	Xanthomonas perforans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2425	399	Xanthomonas oryzae	11818	\N	\N	\N	\N	Xanthomonas oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2426	399	Xanthomonas melonis	11817	\N	\N	\N	\N	Xanthomonas melonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2427	399	Xanthomonas hyacinthi	11816	\N	\N	\N	\N	Xanthomonas hyacinthi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2428	399	Xanthomonas hortorum	11815	\N	\N	\N	\N	Xanthomonas hortorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2429	399	Xanthomonas gardneri	11814	\N	\N	\N	\N	Xanthomonas gardneri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2430	399	Xanthomonas fragariae	11813	\N	\N	\N	\N	Xanthomonas fragariae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2431	399	Xanthomonas euvesicatoria	11812	\N	\N	\N	\N	Xanthomonas euvesicatoria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2432	399	Xanthomonas dyei	11811	\N	\N	\N	\N	Xanthomonas dyei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2433	399	Xanthomonas cynarae	11810	\N	\N	\N	\N	Xanthomonas cynarae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2434	399	Xanthomonas cucurbitae	11809	\N	\N	\N	\N	Xanthomonas cucurbitae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2435	399	Xanthomonas codiaei	11808	\N	\N	\N	\N	Xanthomonas codiaei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2436	399	Xanthomonas citri subsp. malvacearum	11807	\N	\N	\N	\N	Xanthomonas citri subsp. malvacearum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2437	399	Xanthomonas cassavae	11806	\N	\N	\N	\N	Xanthomonas cassavae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2438	399	Xanthomonas campestris	11805	\N	\N	\N	\N	Xanthomonas campestris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2439	399	Xanthomonas bromi	11804	\N	\N	\N	\N	Xanthomonas bromi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2440	399	Xanthomonas axonopodis	11803	\N	\N	\N	\N	Xanthomonas axonopodis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2441	399	Xanthomonas arboricola	11802	\N	\N	\N	\N	Xanthomonas arboricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2442	399	Xanthomonas albilineans	11801	\N	\N	\N	\N	Xanthomonas albilineans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2443	400	Wohlfahrtiimonas chitiniclastica	11799	\N	\N	\N	\N	Wohlfahrtiimonas chitiniclastica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2444	401	Thermomonas koreensis	11797	\N	\N	\N	\N	Thermomonas koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2445	401	Thermomonas hydrothermalis	11796	\N	\N	\N	\N	Thermomonas hydrothermalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2446	401	Thermomonas haemolytica	11795	\N	\N	\N	\N	Thermomonas haemolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2447	401	Thermomonas fusca	11794	\N	\N	\N	\N	Thermomonas fusca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2448	401	Thermomonas brevis	11793	\N	\N	\N	\N	Thermomonas brevis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2449	402	Stenotrophomonas terrae	11791	\N	\N	\N	\N	Stenotrophomonas terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2450	402	Stenotrophomonas rhizophila	11790	\N	\N	\N	\N	Stenotrophomonas rhizophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2451	402	Stenotrophomonas pavanii	11789	\N	\N	\N	\N	Stenotrophomonas pavanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2452	402	Stenotrophomonas nitritireducens	11788	\N	\N	\N	\N	Stenotrophomonas nitritireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2453	402	Stenotrophomonas maltophilia	11787	\N	\N	\N	\N	Stenotrophomonas maltophilia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2454	402	Stenotrophomonas koreensis	11786	\N	\N	\N	\N	Stenotrophomonas koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2455	402	Stenotrophomonas humi	11785	\N	\N	\N	\N	Stenotrophomonas humi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2456	402	Stenotrophomonas ginsengisoli	11784	\N	\N	\N	\N	Stenotrophomonas ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2457	402	Stenotrophomonas daejeonensis	11783	\N	\N	\N	\N	Stenotrophomonas daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2458	402	Stenotrophomonas chelatiphaga	11782	\N	\N	\N	\N	Stenotrophomonas chelatiphaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2459	402	Stenotrophomonas acidaminiphila	11781	\N	\N	\N	\N	Stenotrophomonas acidaminiphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2460	403	Rhodanobacter thiooxydans	11779	\N	\N	\N	\N	Rhodanobacter thiooxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2461	403	Rhodanobacter terrae	11778	\N	\N	\N	\N	Rhodanobacter terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2462	403	Rhodanobacter spathiphylli	11777	\N	\N	\N	\N	Rhodanobacter spathiphylli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2463	403	Rhodanobacter soli	11776	\N	\N	\N	\N	Rhodanobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2464	403	Rhodanobacter panaciterrae	11775	\N	\N	\N	\N	Rhodanobacter panaciterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2465	403	Rhodanobacter lindaniclasticus	11774	\N	\N	\N	\N	Rhodanobacter lindaniclasticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2466	403	Rhodanobacter ginsenosidimutans	11773	\N	\N	\N	\N	Rhodanobacter ginsenosidimutans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2467	403	Rhodanobacter ginsengisoli	11772	\N	\N	\N	\N	Rhodanobacter ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2468	403	Rhodanobacter fulvus	11771	\N	\N	\N	\N	Rhodanobacter fulvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2469	404	Pseudoxanthomonas yeongjuensis	11769	\N	\N	\N	\N	Pseudoxanthomonas yeongjuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2470	404	Pseudoxanthomonas taiwanensis	11768	\N	\N	\N	\N	Pseudoxanthomonas taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2471	404	Pseudoxanthomonas suwonensis	11767	\N	\N	\N	\N	Pseudoxanthomonas suwonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2472	404	Pseudoxanthomonas spadix	11766	\N	\N	\N	\N	Pseudoxanthomonas spadix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2473	404	Pseudoxanthomonas sacheonensis	11765	\N	\N	\N	\N	Pseudoxanthomonas sacheonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2474	404	Pseudoxanthomonas mexicana	11764	\N	\N	\N	\N	Pseudoxanthomonas mexicana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2475	404	Pseudoxanthomonas kaohsiungensis	11763	\N	\N	\N	\N	Pseudoxanthomonas kaohsiungensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2476	404	Pseudoxanthomonas kalamensis	11762	\N	\N	\N	\N	Pseudoxanthomonas kalamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2477	404	Pseudoxanthomonas japonensis	11761	\N	\N	\N	\N	Pseudoxanthomonas japonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2478	404	Pseudoxanthomonas dokdonensis	11760	\N	\N	\N	\N	Pseudoxanthomonas dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2479	404	Pseudoxanthomonas daejeonensis	11759	\N	\N	\N	\N	Pseudoxanthomonas daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2480	404	Pseudoxanthomonas broegbernensis	11758	\N	\N	\N	\N	Pseudoxanthomonas broegbernensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2481	405	Panacagrimonas perspica	11756	\N	\N	\N	\N	Panacagrimonas perspica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2482	406	Lysobacter yangpyeongensis	11754	\N	\N	\N	\N	Lysobacter yangpyeongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2483	406	Lysobacter xinjiangensis	11753	\N	\N	\N	\N	Lysobacter xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2484	406	Lysobacter ximonensis	11752	\N	\N	\N	\N	Lysobacter ximonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2485	406	Lysobacter spongiicola	11751	\N	\N	\N	\N	Lysobacter spongiicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2486	406	Lysobacter soli	11750	\N	\N	\N	\N	Lysobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2487	406	Lysobacter ruishenii	11749	\N	\N	\N	\N	Lysobacter ruishenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2488	406	Lysobacter panaciterrae	11748	\N	\N	\N	\N	Lysobacter panaciterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2489	406	Lysobacter oryzae	11747	\N	\N	\N	\N	Lysobacter oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2490	406	Lysobacter niastensis	11746	\N	\N	\N	\N	Lysobacter niastensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2491	406	Lysobacter niabensis	11745	\N	\N	\N	\N	Lysobacter niabensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2492	406	Lysobacter korlensis	11744	\N	\N	\N	\N	Lysobacter korlensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2493	406	Lysobacter koreensis	11743	\N	\N	\N	\N	Lysobacter koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2494	406	Lysobacter gummosus	11742	\N	\N	\N	\N	Lysobacter gummosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2495	406	Lysobacter ginsengisoli	11741	\N	\N	\N	\N	Lysobacter ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2496	406	Lysobacter enzymogenes	11740	\N	\N	\N	\N	Lysobacter enzymogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2497	406	Lysobacter dokdonensis	11739	\N	\N	\N	\N	Lysobacter dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2498	406	Lysobacter defluvii	11738	\N	\N	\N	\N	Lysobacter defluvii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2499	406	Lysobacter daejeonensis	11737	\N	\N	\N	\N	Lysobacter daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2500	406	Lysobacter concretionis	11736	\N	\N	\N	\N	Lysobacter concretionis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2501	406	Lysobacter capsici	11735	\N	\N	\N	\N	Lysobacter capsici	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2502	406	Lysobacter bugurensis	11734	\N	\N	\N	\N	Lysobacter bugurensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2503	406	Lysobacter brunescens	11733	\N	\N	\N	\N	Lysobacter brunescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2504	406	Lysobacter arseniciresistens	11732	\N	\N	\N	\N	Lysobacter arseniciresistens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2505	406	Lysobacter antibioticus	11731	\N	\N	\N	\N	Lysobacter antibioticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2506	407	Luteimonas terricola	11729	\N	\N	\N	\N	Luteimonas terricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2507	407	Luteimonas mephitis	11728	\N	\N	\N	\N	Luteimonas mephitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2508	407	Luteimonas marina	11727	\N	\N	\N	\N	Luteimonas marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2509	407	Luteimonas lutimaris	11726	\N	\N	\N	\N	Luteimonas lutimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2510	407	Luteimonas composti	11725	\N	\N	\N	\N	Luteimonas composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2511	407	Luteimonas aquatica	11724	\N	\N	\N	\N	Luteimonas aquatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2512	407	Luteimonas aestuarii	11723	\N	\N	\N	\N	Luteimonas aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2513	408	Luteibacter yeojuensis	11721	\N	\N	\N	\N	Luteibacter yeojuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2514	408	Luteibacter rhizovicinus	11720	\N	\N	\N	\N	Luteibacter rhizovicinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2515	408	Luteibacter anthropi	11719	\N	\N	\N	\N	Luteibacter anthropi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2516	409	Ignatzschineria ureiclastica	11717	\N	\N	\N	\N	Ignatzschineria ureiclastica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2517	409	Ignatzschineria larvae	11716	\N	\N	\N	\N	Ignatzschineria larvae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2518	409	Ignatzschineria indica	11715	\N	\N	\N	\N	Ignatzschineria indica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2519	410	Fulvimonas soli	11713	\N	\N	\N	\N	Fulvimonas soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2520	411	Frateuria terrea	11711	\N	\N	\N	\N	Frateuria terrea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2521	411	Frateuria aurantia	11710	\N	\N	\N	\N	Frateuria aurantia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2522	412	Dyella thiooxydans	11708	\N	\N	\N	\N	Dyella thiooxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2523	412	Dyella terrae	11707	\N	\N	\N	\N	Dyella terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2524	412	Dyella soli	11706	\N	\N	\N	\N	Dyella soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2525	412	Dyella marensis	11705	\N	\N	\N	\N	Dyella marensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2526	412	Dyella koreensis	11704	\N	\N	\N	\N	Dyella koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2527	412	Dyella japonica	11703	\N	\N	\N	\N	Dyella japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2528	412	Dyella ginsengisoli	11702	\N	\N	\N	\N	Dyella ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2529	413	Dokdonella soli	11700	\N	\N	\N	\N	Dokdonella soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2530	413	Dokdonella koreensis	11699	\N	\N	\N	\N	Dokdonella koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2531	413	Dokdonella ginsengisoli	11698	\N	\N	\N	\N	Dokdonella ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2532	413	Dokdonella fugitiva	11697	\N	\N	\N	\N	Dokdonella fugitiva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2533	414	Arenimonas oryziterrae	11695	\N	\N	\N	\N	Arenimonas oryziterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2534	414	Arenimonas metalli	11694	\N	\N	\N	\N	Arenimonas metalli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2535	414	Arenimonas malthae	11693	\N	\N	\N	\N	Arenimonas malthae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2536	414	Arenimonas donghaensis	11692	\N	\N	\N	\N	Arenimonas donghaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2537	414	Arenimonas daejeonensis	11691	\N	\N	\N	\N	Arenimonas daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2538	414	Arenimonas composti	11690	\N	\N	\N	\N	Arenimonas composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2539	415	Aquimonas voraii	11688	\N	\N	\N	\N	Aquimonas voraii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2540	416	Xanthobacter viscosus	11685	\N	\N	\N	\N	Xanthobacter viscosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2541	416	Xanthobacter tagetidis	11684	\N	\N	\N	\N	Xanthobacter tagetidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2542	416	Xanthobacter flavus	11683	\N	\N	\N	\N	Xanthobacter flavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2543	416	Xanthobacter autotrophicus	11682	\N	\N	\N	\N	Xanthobacter autotrophicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2544	416	Xanthobacter aminoxidans	11681	\N	\N	\N	\N	Xanthobacter aminoxidans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2545	416	Xanthobacter agilis	11680	\N	\N	\N	\N	Xanthobacter agilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2546	417	Starkeya novella	11678	\N	\N	\N	\N	Starkeya novella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2547	417	Starkeya koreensis	11677	\N	\N	\N	\N	Starkeya koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2548	418	Pseudoxanthobacter soli	11675	\N	\N	\N	\N	Pseudoxanthobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2549	419	Pseudolabrys taiwanensis	11673	\N	\N	\N	\N	Pseudolabrys taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2550	420	Labrys wisconsinensis	11671	\N	\N	\N	\N	Labrys wisconsinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2551	420	Labrys portucalensis	11670	\N	\N	\N	\N	Labrys portucalensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2552	420	Labrys okinawensis	11669	\N	\N	\N	\N	Labrys okinawensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2553	420	Labrys neptuniae	11668	\N	\N	\N	\N	Labrys neptuniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2554	420	Labrys monachus	11667	\N	\N	\N	\N	Labrys monachus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2555	420	Labrys miyagiensis	11666	\N	\N	\N	\N	Labrys miyagiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2556	420	Labrys methylaminiphilus	11665	\N	\N	\N	\N	Labrys methylaminiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2557	421	Azorhizobium doebereinerae	11663	\N	\N	\N	\N	Azorhizobium doebereinerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2558	421	Azorhizobium caulinodans	11662	\N	\N	\N	\N	Azorhizobium caulinodans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2559	422	Ancylobacter vacuolatus	11660	\N	\N	\N	\N	Ancylobacter vacuolatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2560	422	Ancylobacter rudongensis	11659	\N	\N	\N	\N	Ancylobacter rudongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2561	422	Ancylobacter polymorphus	11658	\N	\N	\N	\N	Ancylobacter polymorphus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2562	422	Ancylobacter oerskovii	11657	\N	\N	\N	\N	Ancylobacter oerskovii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2563	422	Ancylobacter dichloromethanicus	11656	\N	\N	\N	\N	Ancylobacter dichloromethanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2564	422	Ancylobacter aquaticus	11655	\N	\N	\N	\N	Ancylobacter aquaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2565	423	Waddlia chondrophila	11652	\N	\N	\N	\N	Waddlia chondrophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2566	424	Victivallis vadensis	11649	\N	\N	\N	\N	Victivallis vadensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2567	425	Vibrio xiamenensis	11646	\N	\N	\N	\N	Vibrio xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2568	425	Vibrio vulnificus	11645	\N	\N	\N	\N	Vibrio vulnificus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2569	425	Vibrio variabilis	11644	\N	\N	\N	\N	Vibrio variabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2570	425	Vibrio tasmaniensis	11643	\N	\N	\N	\N	Vibrio tasmaniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2571	425	Vibrio tapetis	11642	\N	\N	\N	\N	Vibrio tapetis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2572	425	Vibrio superstes	11641	\N	\N	\N	\N	Vibrio superstes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2573	425	Vibrio stylophorae	11640	\N	\N	\N	\N	Vibrio stylophorae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2574	425	Vibrio sinaloensis	11639	\N	\N	\N	\N	Vibrio sinaloensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2575	425	Vibrio scophthalmi	11638	\N	\N	\N	\N	Vibrio scophthalmi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2576	425	Vibrio rumoiensis	11637	\N	\N	\N	\N	Vibrio rumoiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2577	425	Vibrio ruber	11636	\N	\N	\N	\N	Vibrio ruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2578	425	Vibrio rotiferianus	11635	\N	\N	\N	\N	Vibrio rotiferianus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2579	425	Vibrio rhizosphaerae	11634	\N	\N	\N	\N	Vibrio rhizosphaerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2580	425	Vibrio proteolyticus	11633	\N	\N	\N	\N	Vibrio proteolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2581	425	Vibrio ponticus	11632	\N	\N	\N	\N	Vibrio ponticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2582	425	Vibrio pomeroyi	11631	\N	\N	\N	\N	Vibrio pomeroyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2583	425	Vibrio penaeicida	11630	\N	\N	\N	\N	Vibrio penaeicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2584	425	Vibrio pelagius	11629	\N	\N	\N	\N	Vibrio pelagius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2585	425	Vibrio pectenicida	11628	\N	\N	\N	\N	Vibrio pectenicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2586	425	Vibrio parahaemolyticus	11627	\N	\N	\N	\N	Vibrio parahaemolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2587	425	Vibrio pacinii	11626	\N	\N	\N	\N	Vibrio pacinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2588	425	Vibrio owensii	11625	\N	\N	\N	\N	Vibrio owensii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2589	425	Vibrio orientalis	11624	\N	\N	\N	\N	Vibrio orientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2590	425	Vibrio neptunius	11623	\N	\N	\N	\N	Vibrio neptunius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2591	425	Vibrio natriegens	11622	\N	\N	\N	\N	Vibrio natriegens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2592	425	Vibrio mytili	11621	\N	\N	\N	\N	Vibrio mytili	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2593	425	Vibrio mimicus	11620	\N	\N	\N	\N	Vibrio mimicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2594	425	Vibrio mediterranei	11619	\N	\N	\N	\N	Vibrio mediterranei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2595	425	Vibrio maritimus	11618	\N	\N	\N	\N	Vibrio maritimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2596	425	Vibrio mangrovi	11617	\N	\N	\N	\N	Vibrio mangrovi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2597	425	Vibrio litoralis	11616	\N	\N	\N	\N	Vibrio litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2598	425	Vibrio lentus	11615	\N	\N	\N	\N	Vibrio lentus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2599	425	Vibrio kanaloae	11614	\N	\N	\N	\N	Vibrio kanaloae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2600	425	Vibrio inusitatus	11613	\N	\N	\N	\N	Vibrio inusitatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2601	425	Vibrio hispanicus	11612	\N	\N	\N	\N	Vibrio hispanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2602	425	Vibrio hepatarius	11611	\N	\N	\N	\N	Vibrio hepatarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2603	425	Vibrio harveyi	11610	\N	\N	\N	\N	Vibrio harveyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2604	425	Vibrio hangzhouensis	11609	\N	\N	\N	\N	Vibrio hangzhouensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2605	425	Vibrio halioticoli	11608	\N	\N	\N	\N	Vibrio halioticoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2606	425	Vibrio gigantis	11607	\N	\N	\N	\N	Vibrio gigantis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2607	425	Vibrio gallicus	11606	\N	\N	\N	\N	Vibrio gallicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2608	425	Vibrio gallaecicus	11605	\N	\N	\N	\N	Vibrio gallaecicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2609	425	Vibrio furnissii	11604	\N	\N	\N	\N	Vibrio furnissii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2610	425	Vibrio fortis	11603	\N	\N	\N	\N	Vibrio fortis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2611	425	Vibrio fluvialis	11602	\N	\N	\N	\N	Vibrio fluvialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2612	425	Vibrio ezurae	11601	\N	\N	\N	\N	Vibrio ezurae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2613	425	Vibrio diazotrophicus	11600	\N	\N	\N	\N	Vibrio diazotrophicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2614	425	Vibrio crassostreae	11599	\N	\N	\N	\N	Vibrio crassostreae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2615	425	Vibrio coralliilyticus	11598	\N	\N	\N	\N	Vibrio coralliilyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2616	425	Vibrio communis	11597	\N	\N	\N	\N	Vibrio communis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2617	425	Vibrio comitans	11596	\N	\N	\N	\N	Vibrio comitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2618	425	Vibrio cincinnatiensis	11595	\N	\N	\N	\N	Vibrio cincinnatiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2619	425	Vibrio cholerae	11594	\N	\N	\N	\N	Vibrio cholerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2620	425	Vibrio celticus	11593	\N	\N	\N	\N	Vibrio celticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2621	425	Vibrio casei	11592	\N	\N	\N	\N	Vibrio casei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2622	425	Vibrio caribbeanicus	11591	\N	\N	\N	\N	Vibrio caribbeanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2623	425	Vibrio campbellii	11590	\N	\N	\N	\N	Vibrio campbellii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2624	425	Vibrio brasiliensis	11589	\N	\N	\N	\N	Vibrio brasiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2625	425	Vibrio atypicus	11588	\N	\N	\N	\N	Vibrio atypicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2626	425	Vibrio atlanticus	11587	\N	\N	\N	\N	Vibrio atlanticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2627	425	Vibrio artabrorum	11586	\N	\N	\N	\N	Vibrio artabrorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2628	425	Vibrio areninigrae	11585	\N	\N	\N	\N	Vibrio areninigrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2629	425	Vibrio anguillarum	11584	\N	\N	\N	\N	Vibrio anguillarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2630	425	Vibrio alginolyticus	11583	\N	\N	\N	\N	Vibrio alginolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2631	425	Vibrio albensis	11582	\N	\N	\N	\N	Vibrio albensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2632	425	Vibrio agarivorans	11581	\N	\N	\N	\N	Vibrio agarivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2633	426	Salinivibrio siamensis	11579	\N	\N	\N	\N	Salinivibrio siamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2634	426	Salinivibrio sharmensis	11578	\N	\N	\N	\N	Salinivibrio sharmensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2635	426	Salinivibrio proteolyticus	11577	\N	\N	\N	\N	Salinivibrio proteolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2636	426	Salinivibrio costicola subsp. vallismortis	11576	\N	\N	\N	\N	Salinivibrio costicola subsp. vallismortis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2637	426	Salinivibrio costicola subsp. costicola	11575	\N	\N	\N	\N	Salinivibrio costicola subsp. costicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2638	426	Salinivibrio costicola subsp. alcaliphilus	11574	\N	\N	\N	\N	Salinivibrio costicola subsp. alcaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2639	427	Photobacterium swingsii	11572	\N	\N	\N	\N	Photobacterium swingsii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2640	427	Photobacterium rosenbergii	11571	\N	\N	\N	\N	Photobacterium rosenbergii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2641	427	Photobacterium profundum	11570	\N	\N	\N	\N	Photobacterium profundum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2642	427	Photobacterium phosphoreum	11569	\N	\N	\N	\N	Photobacterium phosphoreum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2643	427	Photobacterium lutimaris	11568	\N	\N	\N	\N	Photobacterium lutimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2644	427	Photobacterium lipolyticum	11567	\N	\N	\N	\N	Photobacterium lipolyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2645	427	Photobacterium leiognathi	11566	\N	\N	\N	\N	Photobacterium leiognathi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2646	427	Photobacterium kishitanii	11565	\N	\N	\N	\N	Photobacterium kishitanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2647	427	Photobacterium jeanii	11564	\N	\N	\N	\N	Photobacterium jeanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2648	427	Photobacterium indicum	11563	\N	\N	\N	\N	Photobacterium indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2649	427	Photobacterium iliopiscarium	11562	\N	\N	\N	\N	Photobacterium iliopiscarium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2650	427	Photobacterium halotolerans	11561	\N	\N	\N	\N	Photobacterium halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2651	427	Photobacterium ganghwense	11560	\N	\N	\N	\N	Photobacterium ganghwense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2652	427	Photobacterium gaetbulicola	11559	\N	\N	\N	\N	Photobacterium gaetbulicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2653	427	Photobacterium frigidiphilum	11558	\N	\N	\N	\N	Photobacterium frigidiphilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2654	427	Photobacterium damselae subsp. piscicida	11557	\N	\N	\N	\N	Photobacterium damselae subsp. piscicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2655	427	Photobacterium damselae subsp. damselae	11556	\N	\N	\N	\N	Photobacterium damselae subsp. damselae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2656	427	Photobacterium aplysiae	11555	\N	\N	\N	\N	Photobacterium aplysiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2657	427	Photobacterium aphoticum	11554	\N	\N	\N	\N	Photobacterium aphoticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2658	427	Photobacterium angustum	11553	\N	\N	\N	\N	Photobacterium angustum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2659	428	Grimontia hollisae	11551	\N	\N	\N	\N	Grimontia hollisae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2660	429	Enterovibrio norvegicus	11549	\N	\N	\N	\N	Enterovibrio norvegicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2661	429	Enterovibrio nigricans	11548	\N	\N	\N	\N	Enterovibrio nigricans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2662	429	Enterovibrio coralii	11547	\N	\N	\N	\N	Enterovibrio coralii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2663	429	Enterovibrio calviensis	11546	\N	\N	\N	\N	Enterovibrio calviensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2664	430	Aliivibrio wodanis	11544	\N	\N	\N	\N	Aliivibrio wodanis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2665	430	Aliivibrio sifiae	11543	\N	\N	\N	\N	Aliivibrio sifiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2666	430	Aliivibrio salmonicida	11542	\N	\N	\N	\N	Aliivibrio salmonicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2667	430	Aliivibrio fischeri	11541	\N	\N	\N	\N	Aliivibrio fischeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2668	430	Aliivibrio finisterrensis	11540	\N	\N	\N	\N	Aliivibrio finisterrensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2669	431	Verrucomicrobium spinosum	11537	\N	\N	\N	\N	Verrucomicrobium spinosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2670	432	Roseibacillus ponti	11535	\N	\N	\N	\N	Roseibacillus ponti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2671	432	Roseibacillus persicicus	11534	\N	\N	\N	\N	Roseibacillus persicicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2672	432	Roseibacillus ishigakijimensis	11533	\N	\N	\N	\N	Roseibacillus ishigakijimensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2673	433	Prosthecobacter vanneervenii	11531	\N	\N	\N	\N	Prosthecobacter vanneervenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2674	433	Prosthecobacter fusiformis	11530	\N	\N	\N	\N	Prosthecobacter fusiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2675	433	Prosthecobacter fluviatilis	11529	\N	\N	\N	\N	Prosthecobacter fluviatilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2676	433	Prosthecobacter dejongeii	11528	\N	\N	\N	\N	Prosthecobacter dejongeii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2677	433	Prosthecobacter debontii	11527	\N	\N	\N	\N	Prosthecobacter debontii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2678	434	Persicirhabdus sediminis	11525	\N	\N	\N	\N	Persicirhabdus sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2679	435	Luteolibacter pohnpeiensis	11523	\N	\N	\N	\N	Luteolibacter pohnpeiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2680	435	Luteolibacter algae	11522	\N	\N	\N	\N	Luteolibacter algae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2681	436	Haloferula sargassicola	11520	\N	\N	\N	\N	Haloferula sargassicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2682	436	Haloferula rosea	11519	\N	\N	\N	\N	Haloferula rosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2683	436	Haloferula phyci	11518	\N	\N	\N	\N	Haloferula phyci	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2684	436	Haloferula helveola	11517	\N	\N	\N	\N	Haloferula helveola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2685	436	Haloferula harenae	11516	\N	\N	\N	\N	Haloferula harenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2686	437	Zymophilus raffinosivorans	11513	\N	\N	\N	\N	Zymophilus raffinosivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2687	438	Veillonella parvula	11511	\N	\N	\N	\N	Veillonella parvula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2688	438	Veillonella montpellierensis	11510	\N	\N	\N	\N	Veillonella montpellierensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2689	438	Veillonella magna	11509	\N	\N	\N	\N	Veillonella magna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2690	438	Veillonella denticariosi	11508	\N	\N	\N	\N	Veillonella denticariosi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2691	438	Veillonella criceti	11507	\N	\N	\N	\N	Veillonella criceti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2692	438	Veillonella atypica	11506	\N	\N	\N	\N	Veillonella atypica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2693	439	Thermosinus carboxydivorans	11504	\N	\N	\N	\N	Thermosinus carboxydivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2694	440	Sporomusa sphaeroides	11502	\N	\N	\N	\N	Sporomusa sphaeroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2695	440	Sporomusa silvacetica	11501	\N	\N	\N	\N	Sporomusa silvacetica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2696	440	Sporomusa rhizae	11500	\N	\N	\N	\N	Sporomusa rhizae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2697	440	Sporomusa paucivorans	11499	\N	\N	\N	\N	Sporomusa paucivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2698	440	Sporomusa ovata	11498	\N	\N	\N	\N	Sporomusa ovata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2699	440	Sporomusa malonica	11497	\N	\N	\N	\N	Sporomusa malonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2700	440	Sporomusa aerivorans	11496	\N	\N	\N	\N	Sporomusa aerivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2701	440	Sporomusa acidovorans	11495	\N	\N	\N	\N	Sporomusa acidovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2702	441	Sporolituus thermophilus	11493	\N	\N	\N	\N	Sporolituus thermophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2703	442	Selenomonas sputigena	11491	\N	\N	\N	\N	Selenomonas sputigena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2704	442	Selenomonas ruminantium subsp. ruminantium	11490	\N	\N	\N	\N	Selenomonas ruminantium subsp. ruminantium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2705	442	Selenomonas ruminantium subsp. lactilytica	11489	\N	\N	\N	\N	Selenomonas ruminantium subsp. lactilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2706	442	Selenomonas noxia	11488	\N	\N	\N	\N	Selenomonas noxia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2707	442	Selenomonas lipolytica	11487	\N	\N	\N	\N	Selenomonas lipolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2708	442	Selenomonas infelix	11486	\N	\N	\N	\N	Selenomonas infelix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2709	442	Selenomonas flueggei	11485	\N	\N	\N	\N	Selenomonas flueggei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2710	442	Selenomonas dianae	11484	\N	\N	\N	\N	Selenomonas dianae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2711	442	Selenomonas bovis	11483	\N	\N	\N	\N	Selenomonas bovis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2712	442	Selenomonas artemidis	11482	\N	\N	\N	\N	Selenomonas artemidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2713	443	Schwartzia succinivorans	11480	\N	\N	\N	\N	Schwartzia succinivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2714	444	Propionispora vibrioides	11478	\N	\N	\N	\N	Propionispora vibrioides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2715	444	Propionispora hippei	11477	\N	\N	\N	\N	Propionispora hippei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2716	445	Propionispira arboris	11475	\N	\N	\N	\N	Propionispira arboris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2717	446	Pelosinus propionicus	11473	\N	\N	\N	\N	Pelosinus propionicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2718	446	Pelosinus fermentans	11472	\N	\N	\N	\N	Pelosinus fermentans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2719	446	Pelosinus defluvii	11471	\N	\N	\N	\N	Pelosinus defluvii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2720	447	Pectinatus portalensis	11469	\N	\N	\N	\N	Pectinatus portalensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2721	447	Pectinatus haikarae	11468	\N	\N	\N	\N	Pectinatus haikarae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2722	447	Pectinatus cerevisiiphilus	11467	\N	\N	\N	\N	Pectinatus cerevisiiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2723	448	Mitsuokella multacida	11465	\N	\N	\N	\N	Mitsuokella multacida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2724	448	Mitsuokella jalaludinii	11464	\N	\N	\N	\N	Mitsuokella jalaludinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2725	449	Megasphaera sueciensis	11462	\N	\N	\N	\N	Megasphaera sueciensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2726	449	Megasphaera paucivorans	11461	\N	\N	\N	\N	Megasphaera paucivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2727	449	Megasphaera micronuciformis	11460	\N	\N	\N	\N	Megasphaera micronuciformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2728	450	Megamonas hypermegale	11458	\N	\N	\N	\N	Megamonas hypermegale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2729	450	Megamonas funiformis	11457	\N	\N	\N	\N	Megamonas funiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2730	451	Dialister succinatiphilus	11455	\N	\N	\N	\N	Dialister succinatiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2731	451	Dialister pneumosintes	11454	\N	\N	\N	\N	Dialister pneumosintes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2732	451	Dialister micraerophilus	11453	\N	\N	\N	\N	Dialister micraerophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2733	451	Dialister invisus	11452	\N	\N	\N	\N	Dialister invisus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2734	452	Dendrosporobacter quercicolus	11450	\N	\N	\N	\N	Dendrosporobacter quercicolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2735	453	Centipeda periodontii	11448	\N	\N	\N	\N	Centipeda periodontii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2736	454	Anaerovibrio lipolyticus	11446	\N	\N	\N	\N	Anaerovibrio lipolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2737	455	Anaerosinus glycerini	11444	\N	\N	\N	\N	Anaerosinus glycerini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2738	456	Anaeromusa acidaminophila	11442	\N	\N	\N	\N	Anaeromusa acidaminophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2739	457	Anaeroglobus geminatus	11440	\N	\N	\N	\N	Anaeroglobus geminatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2740	458	Anaeroarcus burkinensis	11438	\N	\N	\N	\N	Anaeroarcus burkinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2741	459	Allisonella histaminiformans	11436	\N	\N	\N	\N	Allisonella histaminiformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2742	460	Acetonema longum	11434	\N	\N	\N	\N	Acetonema longum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2743	461	Tsukamurella tyrosinosolvens	11431	\N	\N	\N	\N	Tsukamurella tyrosinosolvens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2744	461	Tsukamurella sunchonensis	11430	\N	\N	\N	\N	Tsukamurella sunchonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2745	461	Tsukamurella strandjordii	11429	\N	\N	\N	\N	Tsukamurella strandjordii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2746	461	Tsukamurella spumae	11428	\N	\N	\N	\N	Tsukamurella spumae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2747	461	Tsukamurella spongiae	11427	\N	\N	\N	\N	Tsukamurella spongiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2748	461	Tsukamurella soli	11426	\N	\N	\N	\N	Tsukamurella soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2749	461	Tsukamurella pulmonis	11425	\N	\N	\N	\N	Tsukamurella pulmonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2750	461	Tsukamurella pseudospumae	11424	\N	\N	\N	\N	Tsukamurella pseudospumae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2751	461	Tsukamurella paurometabola	11423	\N	\N	\N	\N	Tsukamurella paurometabola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2752	461	Tsukamurella inchonensis	11422	\N	\N	\N	\N	Tsukamurella inchonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2753	461	Tsukamurella carboxydivorans	11421	\N	\N	\N	\N	Tsukamurella carboxydivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2754	462	Truepera radiovictrix	11418	\N	\N	\N	\N	Truepera radiovictrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2755	463	Fangia hongkongensis	11415	\N	\N	\N	\N	Fangia hongkongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2756	464	Caedibacter taeniospiralis	11413	\N	\N	\N	\N	Caedibacter taeniospiralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2757	464	Caedibacter caryophilus	11412	\N	\N	\N	\N	Caedibacter caryophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2758	465	Thiothrix nivea	11409	\N	\N	\N	\N	Thiothrix nivea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2759	465	Thiothrix lacustris	11408	\N	\N	\N	\N	Thiothrix lacustris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2760	465	Thiothrix fructosivorans	11407	\N	\N	\N	\N	Thiothrix fructosivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2761	465	Thiothrix flexilis	11406	\N	\N	\N	\N	Thiothrix flexilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2762	465	Thiothrix eikelboomii	11405	\N	\N	\N	\N	Thiothrix eikelboomii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2763	465	Thiothrix disciformis	11404	\N	\N	\N	\N	Thiothrix disciformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2764	465	Thiothrix defluvii	11403	\N	\N	\N	\N	Thiothrix defluvii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2765	465	Thiothrix caldifontis	11402	\N	\N	\N	\N	Thiothrix caldifontis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2766	466	Leucothrix mucor	11400	\N	\N	\N	\N	Leucothrix mucor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2767	467	Cocleimonas flava	11398	\N	\N	\N	\N	Cocleimonas flava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2768	468	Beggiatoa alba	11396	\N	\N	\N	\N	Beggiatoa alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2769	469	Thioprofundum lithotrophicum	11393	\N	\N	\N	\N	Thioprofundum lithotrophicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2770	469	Thioprofundum hispidum	11392	\N	\N	\N	\N	Thioprofundum hispidum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2771	470	Thioalkalispira microaerophila	11390	\N	\N	\N	\N	Thioalkalispira microaerophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2772	471	Thermotoga thermarum	11387	\N	\N	\N	\N	Thermotoga thermarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2773	471	Thermotoga subterranea	11386	\N	\N	\N	\N	Thermotoga subterranea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2774	471	Thermotoga petrophila	11385	\N	\N	\N	\N	Thermotoga petrophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2775	471	Thermotoga neapolitana	11384	\N	\N	\N	\N	Thermotoga neapolitana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2776	471	Thermotoga naphthophila	11383	\N	\N	\N	\N	Thermotoga naphthophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2777	471	Thermotoga maritima	11382	\N	\N	\N	\N	Thermotoga maritima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2778	471	Thermotoga lettingae	11381	\N	\N	\N	\N	Thermotoga lettingae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2779	471	Thermotoga hypogea	11380	\N	\N	\N	\N	Thermotoga hypogea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2780	471	Thermotoga elfii	11379	\N	\N	\N	\N	Thermotoga elfii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2781	472	Thermosipho melanesiensis	11377	\N	\N	\N	\N	Thermosipho melanesiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2782	472	Thermosipho japonicus	11376	\N	\N	\N	\N	Thermosipho japonicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2783	472	Thermosipho geolei	11375	\N	\N	\N	\N	Thermosipho geolei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2784	472	Thermosipho atlanticus	11374	\N	\N	\N	\N	Thermosipho atlanticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2785	472	Thermosipho affectus	11373	\N	\N	\N	\N	Thermosipho affectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2786	473	Thermococcoides shengliensis	11371	\N	\N	\N	\N	Thermococcoides shengliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2787	474	Petrotoga sibirica	11369	\N	\N	\N	\N	Petrotoga sibirica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2788	474	Petrotoga olearia	11368	\N	\N	\N	\N	Petrotoga olearia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2789	474	Petrotoga mobilis	11367	\N	\N	\N	\N	Petrotoga mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2790	474	Petrotoga miotherma	11366	\N	\N	\N	\N	Petrotoga miotherma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2791	474	Petrotoga mexicana	11365	\N	\N	\N	\N	Petrotoga mexicana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2792	474	Petrotoga halophila	11364	\N	\N	\N	\N	Petrotoga halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2793	475	Oceanotoga teriensis	11362	\N	\N	\N	\N	Oceanotoga teriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2794	476	Marinitoga okinawensis	11360	\N	\N	\N	\N	Marinitoga okinawensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2795	476	Marinitoga hydrogenitolerans	11359	\N	\N	\N	\N	Marinitoga hydrogenitolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2796	476	Marinitoga camini	11358	\N	\N	\N	\N	Marinitoga camini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2797	477	Kosmotoga olearia	11356	\N	\N	\N	\N	Kosmotoga olearia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2798	477	Kosmotoga arenicorallina	11355	\N	\N	\N	\N	Kosmotoga arenicorallina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2799	478	Geotoga subterranea	11353	\N	\N	\N	\N	Geotoga subterranea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2800	478	Geotoga petraea	11352	\N	\N	\N	\N	Geotoga petraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2801	479	Fervidobacterium riparium	11350	\N	\N	\N	\N	Fervidobacterium riparium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2802	479	Fervidobacterium islandicum	11349	\N	\N	\N	\N	Fervidobacterium islandicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2803	479	Fervidobacterium gondwanense	11348	\N	\N	\N	\N	Fervidobacterium gondwanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2804	479	Fervidobacterium changbaicum	11347	\N	\N	\N	\N	Fervidobacterium changbaicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2805	480	Defluviitoga tunisiensis	11345	\N	\N	\N	\N	Defluviitoga tunisiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2806	481	Thermosporothrix hazakensis	11342	\N	\N	\N	\N	Thermosporothrix hazakensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2807	482	Thermomonospora curvata	11339	\N	\N	\N	\N	Thermomonospora curvata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2808	482	Thermomonospora chromogena	11338	\N	\N	\N	\N	Thermomonospora chromogena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2809	483	Spirillospora rubra	11336	\N	\N	\N	\N	Spirillospora rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2810	483	Spirillospora albida	11335	\N	\N	\N	\N	Spirillospora albida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2811	484	Actinomadura yumaensis	11333	\N	\N	\N	\N	Actinomadura yumaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2812	484	Actinomadura viridilutea	11331	\N	\N	\N	\N	Actinomadura viridilutea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2813	484	Actinomadura vinacea	11330	\N	\N	\N	\N	Actinomadura vinacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2814	484	Actinomadura verrucosospora	11329	\N	\N	\N	\N	Actinomadura verrucosospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2815	484	Actinomadura umbrina	11328	\N	\N	\N	\N	Actinomadura umbrina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2816	484	Actinomadura sputi	11327	\N	\N	\N	\N	Actinomadura sputi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2817	484	Actinomadura sediminis	11326	\N	\N	\N	\N	Actinomadura sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2818	484	Actinomadura scrupuli	11325	\N	\N	\N	\N	Actinomadura scrupuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2819	484	Actinomadura rupiterrae	11324	\N	\N	\N	\N	Actinomadura rupiterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2820	484	Actinomadura rugatobispora	11323	\N	\N	\N	\N	Actinomadura rugatobispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2821	484	Actinomadura rudentiformis	11322	\N	\N	\N	\N	Actinomadura rudentiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2822	484	Actinomadura rubrobrunea	11321	\N	\N	\N	\N	Actinomadura rubrobrunea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2823	484	Actinomadura rifamycini	11320	\N	\N	\N	\N	Actinomadura rifamycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2824	484	Actinomadura pelletieri	11319	\N	\N	\N	\N	Actinomadura pelletieri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2825	484	Actinomadura oligospora	11318	\N	\N	\N	\N	Actinomadura oligospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2826	484	Actinomadura nitritigenes	11317	\N	\N	\N	\N	Actinomadura nitritigenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2827	484	Actinomadura napierensis	11316	\N	\N	\N	\N	Actinomadura napierensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2828	484	Actinomadura namibiensis	11315	\N	\N	\N	\N	Actinomadura namibiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2829	484	Actinomadura miaoliensis	11314	\N	\N	\N	\N	Actinomadura miaoliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2830	484	Actinomadura meyerae	11313	\N	\N	\N	\N	Actinomadura meyerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2831	484	Actinomadura mexicana	11312	\N	\N	\N	\N	Actinomadura mexicana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2832	484	Actinomadura meridiana	11311	\N	\N	\N	\N	Actinomadura meridiana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2833	484	Actinomadura madurae	11310	\N	\N	\N	\N	Actinomadura madurae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2834	484	Actinomadura macra	11309	\N	\N	\N	\N	Actinomadura macra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2835	484	Actinomadura luteofluorescens	11308	\N	\N	\N	\N	Actinomadura luteofluorescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2836	484	Actinomadura livida	11307	\N	\N	\N	\N	Actinomadura livida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2837	484	Actinomadura latina	11306	\N	\N	\N	\N	Actinomadura latina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2838	484	Actinomadura kijaniata	11305	\N	\N	\N	\N	Actinomadura kijaniata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2839	484	Actinomadura keratinilytica	11304	\N	\N	\N	\N	Actinomadura keratinilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2840	484	Actinomadura hibisca	11303	\N	\N	\N	\N	Actinomadura hibisca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2841	484	Actinomadura hallensis	11302	\N	\N	\N	\N	Actinomadura hallensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2842	484	Actinomadura glauciflava	11301	\N	\N	\N	\N	Actinomadura glauciflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2843	484	Actinomadura geliboluensis	11300	\N	\N	\N	\N	Actinomadura geliboluensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2844	484	Actinomadura fulvescens	11299	\N	\N	\N	\N	Actinomadura fulvescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2845	484	Actinomadura formosensis	11298	\N	\N	\N	\N	Actinomadura formosensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2846	484	Actinomadura flavalba	11297	\N	\N	\N	\N	Actinomadura flavalba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2847	484	Actinomadura fibrosa	11296	\N	\N	\N	\N	Actinomadura fibrosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2848	484	Actinomadura echinospora	11295	\N	\N	\N	\N	Actinomadura echinospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2849	484	Actinomadura cremea subsp. cremea	11294	\N	\N	\N	\N	Actinomadura cremea subsp. cremea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2850	484	Actinomadura coerulea	11293	\N	\N	\N	\N	Actinomadura coerulea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2851	484	Actinomadura citrea	11292	\N	\N	\N	\N	Actinomadura citrea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2852	484	Actinomadura chokoriensis	11291	\N	\N	\N	\N	Actinomadura chokoriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2853	484	Actinomadura chibensis	11290	\N	\N	\N	\N	Actinomadura chibensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2854	484	Actinomadura catellatispora	11289	\N	\N	\N	\N	Actinomadura catellatispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2855	484	Actinomadura bangladeshensis	11288	\N	\N	\N	\N	Actinomadura bangladeshensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2856	484	Actinomadura atramentaria	11287	\N	\N	\N	\N	Actinomadura atramentaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2857	484	Actinomadura apis	11286	\N	\N	\N	\N	Actinomadura apis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2858	484	Actinomadura alba	11285	\N	\N	\N	\N	Actinomadura alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2859	484	Actinomadura viridis	11332	\N	\N	\N	\N	Actinomadura viridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2860	485	Actinocorallia longicatena	11283	\N	\N	\N	\N	Actinocorallia longicatena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2861	485	Actinocorallia libanotica	11282	\N	\N	\N	\N	Actinocorallia libanotica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2862	485	Actinocorallia herbida	11281	\N	\N	\N	\N	Actinocorallia herbida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2863	485	Actinocorallia glomerata	11280	\N	\N	\N	\N	Actinocorallia glomerata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2864	485	Actinocorallia cavernae	11279	\N	\N	\N	\N	Actinocorallia cavernae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2865	485	Actinocorallia aurea	11278	\N	\N	\N	\N	Actinocorallia aurea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2866	485	Actinocorallia aurantiaca	11277	\N	\N	\N	\N	Actinocorallia aurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2867	486	Actinoallomurus yoronensis	11275	\N	\N	\N	\N	Actinoallomurus yoronensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2868	486	Actinoallomurus spadix	11274	\N	\N	\N	\N	Actinoallomurus spadix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2869	486	Actinoallomurus radicium	11273	\N	\N	\N	\N	Actinoallomurus radicium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2870	486	Actinoallomurus purpureus	11272	\N	\N	\N	\N	Actinoallomurus purpureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2871	486	Actinoallomurus oryzae	11271	\N	\N	\N	\N	Actinoallomurus oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2872	486	Actinoallomurus luridus	11270	\N	\N	\N	\N	Actinoallomurus luridus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2873	486	Actinoallomurus iriomotensis	11269	\N	\N	\N	\N	Actinoallomurus iriomotensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2874	486	Actinoallomurus fulvus	11268	\N	\N	\N	\N	Actinoallomurus fulvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2875	486	Actinoallomurus coprocola	11267	\N	\N	\N	\N	Actinoallomurus coprocola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2876	486	Actinoallomurus caesius	11266	\N	\N	\N	\N	Actinoallomurus caesius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2877	486	Actinoallomurus amamiensis	11265	\N	\N	\N	\N	Actinoallomurus amamiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2878	486	Actinoallomurus acaciae	11264	\N	\N	\N	\N	Actinoallomurus acaciae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2879	487	Thermomicrobium roseum	11261	\N	\N	\N	\N	Thermomicrobium roseum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2880	488	Thermolithobacter ferrireducens	11258	\N	\N	\N	\N	Thermolithobacter ferrireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2881	488	Thermolithobacter carboxydivorans	11257	\N	\N	\N	\N	Thermolithobacter carboxydivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2882	489	Thermoleophilum minutum	11254	\N	\N	\N	\N	Thermoleophilum minutum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2883	489	Thermoleophilum album	11253	\N	\N	\N	\N	Thermoleophilum album	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2884	490	Thermogemmatispora onikobensis	11250	\N	\N	\N	\N	Thermogemmatispora onikobensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2885	490	Thermogemmatispora foliorum	11249	\N	\N	\N	\N	Thermogemmatispora foliorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2886	491	Coprothermobacter proteolyticus	11246	\N	\N	\N	\N	Coprothermobacter proteolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2887	491	Coprothermobacter platensis	11245	\N	\N	\N	\N	Coprothermobacter platensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2888	492	Thermodesulfobacterium thermophilum	11242	\N	\N	\N	\N	Thermodesulfobacterium thermophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2889	492	Thermodesulfobacterium hydrogeniphilum	11241	\N	\N	\N	\N	Thermodesulfobacterium hydrogeniphilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2890	492	Thermodesulfobacterium hveragerdense	11240	\N	\N	\N	\N	Thermodesulfobacterium hveragerdense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2891	492	Thermodesulfobacterium commune	11239	\N	\N	\N	\N	Thermodesulfobacterium commune	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2892	493	Thermodesulfatator indicus	11237	\N	\N	\N	\N	Thermodesulfatator indicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2893	493	Thermodesulfatator atlanticus	11236	\N	\N	\N	\N	Thermodesulfatator atlanticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2894	494	Thermovorax subterraneus	11233	\N	\N	\N	\N	Thermovorax subterraneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2895	495	Thermovenabulum ferriorganovorum	11231	\N	\N	\N	\N	Thermovenabulum ferriorganovorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2896	496	Thermosediminibacter litoriperuensis	11229	\N	\N	\N	\N	Thermosediminibacter litoriperuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2897	497	Thermoanaerobacterium xylanolyticum	11227	\N	\N	\N	\N	Thermoanaerobacterium xylanolyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2898	497	Thermoanaerobacterium thermosulfurigenes	11226	\N	\N	\N	\N	Thermoanaerobacterium thermosulfurigenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2899	497	Thermoanaerobacterium thermostercoris	11225	\N	\N	\N	\N	Thermoanaerobacterium thermostercoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2900	497	Thermoanaerobacterium thermosaccharolyticum	11224	\N	\N	\N	\N	Thermoanaerobacterium thermosaccharolyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2901	497	Thermoanaerobacterium saccharolyticum	11223	\N	\N	\N	\N	Thermoanaerobacterium saccharolyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2902	497	Thermoanaerobacterium aotearoense	11222	\N	\N	\N	\N	Thermoanaerobacterium aotearoense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2903	497	Thermoanaerobacterium aciditolerans	11221	\N	\N	\N	\N	Thermoanaerobacterium aciditolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2904	498	Mahella australiensis	11219	\N	\N	\N	\N	Mahella australiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2905	499	Caldicellulosiruptor saccharolyticus	11217	\N	\N	\N	\N	Caldicellulosiruptor saccharolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2906	499	Caldicellulosiruptor owensensis	11216	\N	\N	\N	\N	Caldicellulosiruptor owensensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2907	499	Caldicellulosiruptor lactoaceticus	11215	\N	\N	\N	\N	Caldicellulosiruptor lactoaceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2908	499	Caldicellulosiruptor kronotskyensis	11214	\N	\N	\N	\N	Caldicellulosiruptor kronotskyensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2909	499	Caldicellulosiruptor kristjanssonii	11213	\N	\N	\N	\N	Caldicellulosiruptor kristjanssonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2910	499	Caldicellulosiruptor hydrothermalis	11212	\N	\N	\N	\N	Caldicellulosiruptor hydrothermalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2911	499	Caldicellulosiruptor bescii	11211	\N	\N	\N	\N	Caldicellulosiruptor bescii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2912	499	Caldicellulosiruptor acetigenus	11210	\N	\N	\N	\N	Caldicellulosiruptor acetigenus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2913	500	Caldanaerovirga acetigignens	11208	\N	\N	\N	\N	Caldanaerovirga acetigignens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2914	501	Thermoanaerobacter wiegelii	11205	\N	\N	\N	\N	Thermoanaerobacter wiegelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2915	501	Thermoanaerobacter uzonensis	11204	\N	\N	\N	\N	Thermoanaerobacter uzonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2916	501	Thermoanaerobacter thermohydrosulfuricus	11203	\N	\N	\N	\N	Thermoanaerobacter thermohydrosulfuricus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2917	501	Thermoanaerobacter thermocopriae	11202	\N	\N	\N	\N	Thermoanaerobacter thermocopriae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2918	501	Thermoanaerobacter sulfurophilus	11201	\N	\N	\N	\N	Thermoanaerobacter sulfurophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2919	501	Thermoanaerobacter sulfurigignens	11200	\N	\N	\N	\N	Thermoanaerobacter sulfurigignens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2920	501	Thermoanaerobacter siderophilus	11199	\N	\N	\N	\N	Thermoanaerobacter siderophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2921	501	Thermoanaerobacter pseudethanolicus	11198	\N	\N	\N	\N	Thermoanaerobacter pseudethanolicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2922	501	Thermoanaerobacter mathranii subsp. mathranii	11197	\N	\N	\N	\N	Thermoanaerobacter mathranii subsp. mathranii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2923	501	Thermoanaerobacter mathranii subsp. alimentarius	11196	\N	\N	\N	\N	Thermoanaerobacter mathranii subsp. alimentarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2924	501	Thermoanaerobacter kivui	11195	\N	\N	\N	\N	Thermoanaerobacter kivui	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2925	501	Thermoanaerobacter italicus	11194	\N	\N	\N	\N	Thermoanaerobacter italicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2926	501	Thermoanaerobacter ethanolicus	11193	\N	\N	\N	\N	Thermoanaerobacter ethanolicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2927	501	Thermoanaerobacter brockii subsp. lactiethylicus	11192	\N	\N	\N	\N	Thermoanaerobacter brockii subsp. lactiethylicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2928	501	Thermoanaerobacter brockii subsp. finnii	11191	\N	\N	\N	\N	Thermoanaerobacter brockii subsp. finnii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2929	501	Thermoanaerobacter brockii subsp. brockii	11190	\N	\N	\N	\N	Thermoanaerobacter brockii subsp. brockii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2930	501	Thermoanaerobacter acetoethylicus	11189	\N	\N	\N	\N	Thermoanaerobacter acetoethylicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2931	502	Thermanaeromonas toyohensis	11187	\N	\N	\N	\N	Thermanaeromonas toyohensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2932	503	Thermacetogenium phaeum	11185	\N	\N	\N	\N	Thermacetogenium phaeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2933	504	Tepidanaerobacter syntrophicus	11183	\N	\N	\N	\N	Tepidanaerobacter syntrophicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2934	505	Moorella thermoautotrophica	11181	\N	\N	\N	\N	Moorella thermoautotrophica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2935	505	Moorella thermoacetica	11180	\N	\N	\N	\N	Moorella thermoacetica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2936	505	Moorella mulderi	11179	\N	\N	\N	\N	Moorella mulderi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2937	505	Moorella humiferrea	11178	\N	\N	\N	\N	Moorella humiferrea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2938	505	Moorella glycerini	11177	\N	\N	\N	\N	Moorella glycerini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2939	506	Gelria glutamica	11175	\N	\N	\N	\N	Gelria glutamica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2940	507	Desulfovirgula thermocuniculi	11173	\N	\N	\N	\N	Desulfovirgula thermocuniculi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2941	508	Carboxydothermus siderophilus	11171	\N	\N	\N	\N	Carboxydothermus siderophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2942	508	Carboxydothermus pertinax	11170	\N	\N	\N	\N	Carboxydothermus pertinax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2943	508	Carboxydothermus hydrogenoformans	11169	\N	\N	\N	\N	Carboxydothermus hydrogenoformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2944	508	Carboxydothermus ferrireducens	11168	\N	\N	\N	\N	Carboxydothermus ferrireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2945	509	Caloribacterium cisternae	11166	\N	\N	\N	\N	Caloribacterium cisternae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2946	510	Caldanaerobius zeae	11164	\N	\N	\N	\N	Caldanaerobius zeae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2947	510	Caldanaerobius polysaccharolyticus	11163	\N	\N	\N	\N	Caldanaerobius polysaccharolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2948	510	Caldanaerobius fijiensis	11162	\N	\N	\N	\N	Caldanaerobius fijiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2949	511	Caldanaerobacter uzonensis	11160	\N	\N	\N	\N	Caldanaerobacter uzonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2950	511	Caldanaerobacter subterraneus subsp. yonseiensis	11159	\N	\N	\N	\N	Caldanaerobacter subterraneus subsp. yonseiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2951	511	Caldanaerobacter subterraneus subsp. tengcongensis	11158	\N	\N	\N	\N	Caldanaerobacter subterraneus subsp. tengcongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2952	511	Caldanaerobacter subterraneus subsp. pacificus	11157	\N	\N	\N	\N	Caldanaerobacter subterraneus subsp. pacificus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2953	512	Ammonifex thiophilus	11155	\N	\N	\N	\N	Ammonifex thiophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2954	512	Ammonifex degensii	11154	\N	\N	\N	\N	Ammonifex degensii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2955	513	Thermoflavimicrobium dichotomicum	11151	\N	\N	\N	\N	Thermoflavimicrobium dichotomicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2956	514	Thermoactinomyces vulgaris	11149	\N	\N	\N	\N	Thermoactinomyces vulgaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2957	514	Thermoactinomyces intermedius	11148	\N	\N	\N	\N	Thermoactinomyces intermedius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2958	515	Shimazuella kribbensis	11146	\N	\N	\N	\N	Shimazuella kribbensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2959	516	Seinonella peptonophila	11144	\N	\N	\N	\N	Seinonella peptonophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2960	517	Planifilum yunnanense	11142	\N	\N	\N	\N	Planifilum yunnanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2961	517	Planifilum fulgidum	11141	\N	\N	\N	\N	Planifilum fulgidum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2962	517	Planifilum fimeticola	11140	\N	\N	\N	\N	Planifilum fimeticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2963	518	Melghirimyces algeriensis	11138	\N	\N	\N	\N	Melghirimyces algeriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2964	519	Mechercharimyces mesophilus	11136	\N	\N	\N	\N	Mechercharimyces mesophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2965	520	Marininema mesophilum	11134	\N	\N	\N	\N	Marininema mesophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2966	521	Laceyella tengchongensis	11132	\N	\N	\N	\N	Laceyella tengchongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2967	521	Laceyella sediminis	11131	\N	\N	\N	\N	Laceyella sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2968	521	Laceyella putida	11130	\N	\N	\N	\N	Laceyella putida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2969	522	Kroppenstedtia eburnea	11128	\N	\N	\N	\N	Kroppenstedtia eburnea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2970	523	Desmospora activa	11126	\N	\N	\N	\N	Desmospora activa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2971	524	Thermithiobacillus tepidarius	11123	\N	\N	\N	\N	Thermithiobacillus tepidarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2972	525	Vulcanithermus mediatlanticus	11120	\N	\N	\N	\N	Vulcanithermus mediatlanticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2973	526	Thermus thermophilus	11118	\N	\N	\N	\N	Thermus thermophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2974	526	Thermus scotoductus	11117	\N	\N	\N	\N	Thermus scotoductus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2975	526	Thermus oshimai	11116	\N	\N	\N	\N	Thermus oshimai	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2976	526	Thermus islandicus	11115	\N	\N	\N	\N	Thermus islandicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2977	526	Thermus igniterrae	11114	\N	\N	\N	\N	Thermus igniterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2978	526	Thermus filiformis	11113	\N	\N	\N	\N	Thermus filiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2979	526	Thermus composti	11112	\N	\N	\N	\N	Thermus composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2980	526	Thermus brockianus	11111	\N	\N	\N	\N	Thermus brockianus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2981	526	Thermus arciformis	11110	\N	\N	\N	\N	Thermus arciformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2982	526	Thermus aquaticus	11109	\N	\N	\N	\N	Thermus aquaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2983	526	Thermus antranikianii	11108	\N	\N	\N	\N	Thermus antranikianii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2984	527	Rhabdothermus arcticus	11106	\N	\N	\N	\N	Rhabdothermus arcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2985	528	Oceanithermus profundus	11104	\N	\N	\N	\N	Oceanithermus profundus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2986	529	Meiothermus timidus	11102	\N	\N	\N	\N	Meiothermus timidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2987	529	Meiothermus taiwanensis	11101	\N	\N	\N	\N	Meiothermus taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2988	529	Meiothermus silvanus	11100	\N	\N	\N	\N	Meiothermus silvanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2989	529	Meiothermus rufus	11099	\N	\N	\N	\N	Meiothermus rufus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2990	529	Meiothermus ruber	11098	\N	\N	\N	\N	Meiothermus ruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2991	529	Meiothermus hypogaeus	11097	\N	\N	\N	\N	Meiothermus hypogaeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2992	529	Meiothermus granaticius	11096	\N	\N	\N	\N	Meiothermus granaticius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2993	529	Meiothermus chliarophilus	11095	\N	\N	\N	\N	Meiothermus chliarophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2994	529	Meiothermus cerbereus	11094	\N	\N	\N	\N	Meiothermus cerbereus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2995	529	Meiothermus cateniformans	11093	\N	\N	\N	\N	Meiothermus cateniformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2996	530	Marinithermus hydrothermalis	11091	\N	\N	\N	\N	Marinithermus hydrothermalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2997	531	Syntrophorhabdus aromaticivorans	11088	\N	\N	\N	\N	Syntrophorhabdus aromaticivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2998	532	Thermosyntropha tengcongensis	11085	\N	\N	\N	\N	Thermosyntropha tengcongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
2999	532	Thermosyntropha lipolytica	11084	\N	\N	\N	\N	Thermosyntropha lipolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3000	533	Thermohydrogenium kirishiense	11082	\N	\N	\N	\N	Thermohydrogenium kirishiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3001	534	Syntrophothermus lipocalidus	11080	\N	\N	\N	\N	Syntrophothermus lipocalidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3002	535	Syntrophomonas wolfei subsp. wolfei	11078	\N	\N	\N	\N	Syntrophomonas wolfei subsp. wolfei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3003	535	Syntrophomonas wolfei subsp. saponavida	11077	\N	\N	\N	\N	Syntrophomonas wolfei subsp. saponavida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3004	535	Syntrophomonas sapovorans	11076	\N	\N	\N	\N	Syntrophomonas sapovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3005	535	Syntrophomonas palmitatica	11075	\N	\N	\N	\N	Syntrophomonas palmitatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3006	535	Syntrophomonas erecta	11074	\N	\N	\N	\N	Syntrophomonas erecta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3007	535	Syntrophomonas curvata	11073	\N	\N	\N	\N	Syntrophomonas curvata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3008	535	Syntrophomonas cellicola	11072	\N	\N	\N	\N	Syntrophomonas cellicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3009	536	Pelospora glutarica	11070	\N	\N	\N	\N	Pelospora glutarica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3010	537	Fervidicola ferrireducens	11068	\N	\N	\N	\N	Fervidicola ferrireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3011	538	Dethiobacter alkaliphilus	11066	\N	\N	\N	\N	Dethiobacter alkaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3012	539	Thermodesulforhabdus norvegica	11063	\N	\N	\N	\N	Thermodesulforhabdus norvegica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3013	540	Syntrophobacter wolinii	11061	\N	\N	\N	\N	Syntrophobacter wolinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3014	540	Syntrophobacter sulfatireducens	11060	\N	\N	\N	\N	Syntrophobacter sulfatireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3015	540	Syntrophobacter pfennigii	11059	\N	\N	\N	\N	Syntrophobacter pfennigii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3016	540	Syntrophobacter fumaroxidans	11058	\N	\N	\N	\N	Syntrophobacter fumaroxidans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3017	541	Desulfovirga adipica	11056	\N	\N	\N	\N	Desulfovirga adipica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3018	542	Desulfosoma caldarium	11054	\N	\N	\N	\N	Desulfosoma caldarium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3019	543	Desulforhabdus amnigena	11052	\N	\N	\N	\N	Desulforhabdus amnigena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3020	544	Desulfoglaeba alkanexedens	11050	\N	\N	\N	\N	Desulfoglaeba alkanexedens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3021	545	Desulfacinum infernum	11048	\N	\N	\N	\N	Desulfacinum infernum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3022	545	Desulfacinum hydrothermale	11047	\N	\N	\N	\N	Desulfacinum hydrothermale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3023	546	Syntrophus gentianae	11044	\N	\N	\N	\N	Syntrophus gentianae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3024	546	Syntrophus buswellii	11043	\N	\N	\N	\N	Syntrophus buswellii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3025	546	Syntrophus aciditrophicus	11042	\N	\N	\N	\N	Syntrophus aciditrophicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3026	547	Desulfomonile limimaris	11040	\N	\N	\N	\N	Desulfomonile limimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3027	548	Desulfobacca acetoxidans	11038	\N	\N	\N	\N	Desulfobacca acetoxidans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3028	549	Thermovirga lienii	11035	\N	\N	\N	\N	Thermovirga lienii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3029	550	Thermanaerovibrio velox	11033	\N	\N	\N	\N	Thermanaerovibrio velox	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3030	550	Thermanaerovibrio acidaminovorans	11032	\N	\N	\N	\N	Thermanaerovibrio acidaminovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3031	551	Pyramidobacter piscolens	11030	\N	\N	\N	\N	Pyramidobacter piscolens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3032	552	Jonquetella anthropi	11028	\N	\N	\N	\N	Jonquetella anthropi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3033	553	Dethiosulfovibrio salsuginis	11026	\N	\N	\N	\N	Dethiosulfovibrio salsuginis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3034	553	Dethiosulfovibrio russensis	11025	\N	\N	\N	\N	Dethiosulfovibrio russensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3035	553	Dethiosulfovibrio peptidovorans	11024	\N	\N	\N	\N	Dethiosulfovibrio peptidovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3036	553	Dethiosulfovibrio marinus	11023	\N	\N	\N	\N	Dethiosulfovibrio marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3037	553	Dethiosulfovibrio acidaminovorans	11022	\N	\N	\N	\N	Dethiosulfovibrio acidaminovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3038	554	Anaerobaculum thermoterrenum	11020	\N	\N	\N	\N	Anaerobaculum thermoterrenum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3039	554	Anaerobaculum hydrogeniformans	11019	\N	\N	\N	\N	Anaerobaculum hydrogeniformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3040	555	Aminobacterium mobile	11017	\N	\N	\N	\N	Aminobacterium mobile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3041	555	Aminobacterium colombiense	11016	\N	\N	\N	\N	Aminobacterium colombiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3042	556	Sutterella wadsworthensis	11013	\N	\N	\N	\N	Sutterella wadsworthensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3043	556	Sutterella stercoricanis	11012	\N	\N	\N	\N	Sutterella stercoricanis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3044	556	Sutterella parvirubra	11011	\N	\N	\N	\N	Sutterella parvirubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3045	557	Parasutterella secunda	11009	\N	\N	\N	\N	Parasutterella secunda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3046	557	Parasutterella excrementihominis	11008	\N	\N	\N	\N	Parasutterella excrementihominis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3047	558	Succinivibrio dextrinosolvens	11005	\N	\N	\N	\N	Succinivibrio dextrinosolvens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3048	559	Succinimonas amylolytica	11003	\N	\N	\N	\N	Succinimonas amylolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3049	560	Succinatimonas hippei	11001	\N	\N	\N	\N	Succinatimonas hippei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3050	561	Ruminobacter amylophilus	10999	\N	\N	\N	\N	Ruminobacter amylophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3051	562	Anaerobiospirillum thomasii	10997	\N	\N	\N	\N	Anaerobiospirillum thomasii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3052	562	Anaerobiospirillum succiniciproducens	10996	\N	\N	\N	\N	Anaerobiospirillum succiniciproducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3053	563	Sinosporangium album	10993	\N	\N	\N	\N	Sinosporangium album	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3054	564	Thermopolyspora flexuosa	10990	\N	\N	\N	\N	Thermopolyspora flexuosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3055	565	Streptosporangium yunnanense	10988	\N	\N	\N	\N	Streptosporangium yunnanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3056	565	Streptosporangium vulgare	10987	\N	\N	\N	\N	Streptosporangium vulgare	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3057	565	Streptosporangium violaceochromogenes	10986	\N	\N	\N	\N	Streptosporangium violaceochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3058	565	Streptosporangium subroseum	10985	\N	\N	\N	\N	Streptosporangium subroseum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3059	565	Streptosporangium roseum	10984	\N	\N	\N	\N	Streptosporangium roseum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3060	565	Streptosporangium purpuratum	10983	\N	\N	\N	\N	Streptosporangium purpuratum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3061	565	Streptosporangium pseudovulgare	10982	\N	\N	\N	\N	Streptosporangium pseudovulgare	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3062	565	Streptosporangium oxazolinicum	10981	\N	\N	\N	\N	Streptosporangium oxazolinicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3063	565	Streptosporangium nondiastaticum	10980	\N	\N	\N	\N	Streptosporangium nondiastaticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3064	565	Streptosporangium longisporum	10979	\N	\N	\N	\N	Streptosporangium longisporum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3065	565	Streptosporangium fragile	10978	\N	\N	\N	\N	Streptosporangium fragile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3066	565	Streptosporangium carneum	10977	\N	\N	\N	\N	Streptosporangium carneum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3067	565	Streptosporangium canum	10976	\N	\N	\N	\N	Streptosporangium canum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3068	565	Streptosporangium amethystogenes subsp. fukuiense	10975	\N	\N	\N	\N	Streptosporangium amethystogenes subsp. fukuiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3069	565	Streptosporangium amethystogenes subsp. amethystogenes	10974	\N	\N	\N	\N	Streptosporangium amethystogenes subsp. amethystogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3070	565	Streptosporangium album	10973	\N	\N	\N	\N	Streptosporangium album	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3071	566	Sphaerisporangium viridialbum	10971	\N	\N	\N	\N	Sphaerisporangium viridialbum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3072	566	Sphaerisporangium siamense	10970	\N	\N	\N	\N	Sphaerisporangium siamense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3073	566	Sphaerisporangium rubeum	10969	\N	\N	\N	\N	Sphaerisporangium rubeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3074	566	Sphaerisporangium melleum	10968	\N	\N	\N	\N	Sphaerisporangium melleum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3075	566	Sphaerisporangium krabiense	10967	\N	\N	\N	\N	Sphaerisporangium krabiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3076	566	Sphaerisporangium flaviroseum	10966	\N	\N	\N	\N	Sphaerisporangium flaviroseum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3077	566	Sphaerisporangium cinnabarinum	10965	\N	\N	\N	\N	Sphaerisporangium cinnabarinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3078	567	Planotetraspora thailandica	10963	\N	\N	\N	\N	Planotetraspora thailandica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3079	567	Planotetraspora silvatica	10962	\N	\N	\N	\N	Planotetraspora silvatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3080	567	Planotetraspora mira	10961	\N	\N	\N	\N	Planotetraspora mira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3081	567	Planotetraspora kaengkrachanensis	10960	\N	\N	\N	\N	Planotetraspora kaengkrachanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3082	568	Planomonospora venezuelensis	10958	\N	\N	\N	\N	Planomonospora venezuelensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3083	568	Planomonospora sphaerica	10957	\N	\N	\N	\N	Planomonospora sphaerica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3084	568	Planomonospora parontospora subsp. parontospora	10956	\N	\N	\N	\N	Planomonospora parontospora subsp. parontospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3085	568	Planomonospora parontospora subsp. antibiotica	10955	\N	\N	\N	\N	Planomonospora parontospora subsp. antibiotica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3086	568	Planomonospora alba	10954	\N	\N	\N	\N	Planomonospora alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3087	569	Planobispora rosea	10952	\N	\N	\N	\N	Planobispora rosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3088	569	Planobispora longispora	10951	\N	\N	\N	\N	Planobispora longispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3089	570	Nonomuraea wenchangensis	10949	\N	\N	\N	\N	Nonomuraea wenchangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3090	570	Nonomuraea turkmeniaca	10948	\N	\N	\N	\N	Nonomuraea turkmeniaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3091	570	Nonomuraea spiralis	10947	\N	\N	\N	\N	Nonomuraea spiralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3092	570	Nonomuraea soli	10946	\N	\N	\N	\N	Nonomuraea soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3093	570	Nonomuraea salmonea	10945	\N	\N	\N	\N	Nonomuraea salmonea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3094	570	Nonomuraea rubra	10944	\N	\N	\N	\N	Nonomuraea rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3095	570	Nonomuraea roseoviolacea subsp. roseoviolacea	10943	\N	\N	\N	\N	Nonomuraea roseoviolacea subsp. roseoviolacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3096	570	Nonomuraea roseoviolacea subsp. carminata	10942	\N	\N	\N	\N	Nonomuraea roseoviolacea subsp. carminata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3097	570	Nonomuraea roseola	10941	\N	\N	\N	\N	Nonomuraea roseola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3098	570	Nonomuraea rhizophila	10940	\N	\N	\N	\N	Nonomuraea rhizophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3099	570	Nonomuraea recticatena	10939	\N	\N	\N	\N	Nonomuraea recticatena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3100	570	Nonomuraea pusilla	10938	\N	\N	\N	\N	Nonomuraea pusilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3101	570	Nonomuraea polychroma	10937	\N	\N	\N	\N	Nonomuraea polychroma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3102	570	Nonomuraea maritima	10936	\N	\N	\N	\N	Nonomuraea maritima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3103	570	Nonomuraea maheshkhaliensis	10935	\N	\N	\N	\N	Nonomuraea maheshkhaliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3104	570	Nonomuraea longicatena	10934	\N	\N	\N	\N	Nonomuraea longicatena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3105	570	Nonomuraea kuesteri	10933	\N	\N	\N	\N	Nonomuraea kuesteri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3106	570	Nonomuraea jiangxiensis	10932	\N	\N	\N	\N	Nonomuraea jiangxiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3107	570	Nonomuraea helvata	10931	\N	\N	\N	\N	Nonomuraea helvata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3108	570	Nonomuraea ferruginea	10930	\N	\N	\N	\N	Nonomuraea ferruginea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3109	570	Nonomuraea fastidiosa	10929	\N	\N	\N	\N	Nonomuraea fastidiosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3110	570	Nonomuraea endophytica	10928	\N	\N	\N	\N	Nonomuraea endophytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3111	570	Nonomuraea dietziae	10927	\N	\N	\N	\N	Nonomuraea dietziae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3112	570	Nonomuraea coxensis	10926	\N	\N	\N	\N	Nonomuraea coxensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3113	570	Nonomuraea bangladeshensis	10925	\N	\N	\N	\N	Nonomuraea bangladeshensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3114	570	Nonomuraea antimicrobica	10924	\N	\N	\N	\N	Nonomuraea antimicrobica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3115	570	Nonomuraea angiospora	10923	\N	\N	\N	\N	Nonomuraea angiospora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3116	570	Nonomuraea africana	10922	\N	\N	\N	\N	Nonomuraea africana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3117	571	Microtetraspora niveoalba	10920	\N	\N	\N	\N	Microtetraspora niveoalba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3118	571	Microtetraspora malaysiensis	10919	\N	\N	\N	\N	Microtetraspora malaysiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3119	571	Microtetraspora glauca	10918	\N	\N	\N	\N	Microtetraspora glauca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3120	571	Microtetraspora fusca	10917	\N	\N	\N	\N	Microtetraspora fusca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3121	572	Microbispora siamensis	10915	\N	\N	\N	\N	Microbispora siamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3122	572	Microbispora rosea subsp. rosea	10914	\N	\N	\N	\N	Microbispora rosea subsp. rosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3123	572	Microbispora rosea subsp. aerata	10913	\N	\N	\N	\N	Microbispora rosea subsp. aerata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3124	572	Microbispora mesophila	10912	\N	\N	\N	\N	Microbispora mesophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3125	572	Microbispora corallina	10911	\N	\N	\N	\N	Microbispora corallina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3126	573	Herbidospora yilanensis	10909	\N	\N	\N	\N	Herbidospora yilanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3127	573	Herbidospora sakaeratensis	10908	\N	\N	\N	\N	Herbidospora sakaeratensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3128	573	Herbidospora osyris	10907	\N	\N	\N	\N	Herbidospora osyris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3129	573	Herbidospora daliensis	10906	\N	\N	\N	\N	Herbidospora daliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3130	573	Herbidospora cretacea	10905	\N	\N	\N	\N	Herbidospora cretacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3131	574	Acrocarpospora pleiomorpha	10903	\N	\N	\N	\N	Acrocarpospora pleiomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3132	574	Acrocarpospora macrocephala	10902	\N	\N	\N	\N	Acrocarpospora macrocephala	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3133	574	Acrocarpospora corrugata	10901	\N	\N	\N	\N	Acrocarpospora corrugata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3134	575	Streptomyces zinciresistens	10898	\N	\N	\N	\N	Streptomyces zinciresistens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3135	575	Streptomyces zaomyceticus	10897	\N	\N	\N	\N	Streptomyces zaomyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3136	575	Streptomyces yunnanensis	10896	\N	\N	\N	\N	Streptomyces yunnanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3137	575	Streptomyces youssoufiensis	10895	\N	\N	\N	\N	Streptomyces youssoufiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3138	575	Streptomyces yokosukanensis	10894	\N	\N	\N	\N	Streptomyces yokosukanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3139	575	Streptomyces yogyakartensis	10893	\N	\N	\N	\N	Streptomyces yogyakartensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3140	575	Streptomyces yerevanensis	10892	\N	\N	\N	\N	Streptomyces yerevanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3141	575	Streptomyces yeochonensis	10891	\N	\N	\N	\N	Streptomyces yeochonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3142	575	Streptomyces yatensis	10890	\N	\N	\N	\N	Streptomyces yatensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3143	575	Streptomyces yanii	10889	\N	\N	\N	\N	Streptomyces yanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3144	575	Streptomyces yanglinensis	10888	\N	\N	\N	\N	Streptomyces yanglinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3145	575	Streptomyces xinghaiensis	10887	\N	\N	\N	\N	Streptomyces xinghaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3146	575	Streptomyces xiamenensis	10886	\N	\N	\N	\N	Streptomyces xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3147	575	Streptomyces xanthophaeus	10885	\N	\N	\N	\N	Streptomyces xanthophaeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3148	575	Streptomyces xantholiticus	10884	\N	\N	\N	\N	Streptomyces xantholiticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3149	575	Streptomyces xanthocidicus	10883	\N	\N	\N	\N	Streptomyces xanthocidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3150	575	Streptomyces xanthochromogenes	10882	\N	\N	\N	\N	Streptomyces xanthochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3151	575	Streptomyces werraensis	10881	\N	\N	\N	\N	Streptomyces werraensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3152	575	Streptomyces wellingtoniae	10880	\N	\N	\N	\N	Streptomyces wellingtoniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3153	575	Streptomyces wedmorensis	10879	\N	\N	\N	\N	Streptomyces wedmorensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3154	575	Streptomyces vitaminophilus	10878	\N	\N	\N	\N	Streptomyces vitaminophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3155	575	Streptomyces viridosporus	10877	\N	\N	\N	\N	Streptomyces viridosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3156	575	Streptomyces viridodiastaticus	10876	\N	\N	\N	\N	Streptomyces viridodiastaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3157	575	Streptomyces viridochromogenes	10875	\N	\N	\N	\N	Streptomyces viridochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3158	575	Streptomyces viridobrunneus	10874	\N	\N	\N	\N	Streptomyces viridobrunneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3159	575	Streptomyces viridiviolaceus	10873	\N	\N	\N	\N	Streptomyces viridiviolaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3160	575	Streptomyces virginiae	10872	\N	\N	\N	\N	Streptomyces virginiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3161	575	Streptomyces virens	10871	\N	\N	\N	\N	Streptomyces virens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3162	575	Streptomyces violens	10870	\N	\N	\N	\N	Streptomyces violens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3163	575	Streptomyces violascens	10869	\N	\N	\N	\N	Streptomyces violascens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3164	575	Streptomyces violarus	10868	\N	\N	\N	\N	Streptomyces violarus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3165	575	Streptomyces violaceusniger	10867	\N	\N	\N	\N	Streptomyces violaceusniger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3166	575	Streptomyces violaceus	10866	\N	\N	\N	\N	Streptomyces violaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3167	575	Streptomyces violaceorubidus	10865	\N	\N	\N	\N	Streptomyces violaceorubidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3168	575	Streptomyces violaceoruber	10864	\N	\N	\N	\N	Streptomyces violaceoruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3169	575	Streptomyces violaceorectus	10863	\N	\N	\N	\N	Streptomyces violaceorectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3170	575	Streptomyces violaceolatus	10862	\N	\N	\N	\N	Streptomyces violaceolatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3171	575	Streptomyces violaceochromogenes	10861	\N	\N	\N	\N	Streptomyces violaceochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3172	575	Streptomyces vinaceusdrappus	10860	\N	\N	\N	\N	Streptomyces vinaceusdrappus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3173	575	Streptomyces vinaceus	10859	\N	\N	\N	\N	Streptomyces vinaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3174	575	Streptomyces vietnamensis	10858	\N	\N	\N	\N	Streptomyces vietnamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3175	575	Streptomyces venezuelae	10857	\N	\N	\N	\N	Streptomyces venezuelae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3176	575	Streptomyces vastus	10856	\N	\N	\N	\N	Streptomyces vastus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3177	575	Streptomyces varsoviensis	10855	\N	\N	\N	\N	Streptomyces varsoviensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3178	575	Streptomyces variegatus	10854	\N	\N	\N	\N	Streptomyces variegatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3179	575	Streptomyces variabilis	10853	\N	\N	\N	\N	Streptomyces variabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3180	575	Streptomyces umbrinus	10852	\N	\N	\N	\N	Streptomyces umbrinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3181	575	Streptomyces turgidiscabies	10851	\N	\N	\N	\N	Streptomyces turgidiscabies	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3182	575	Streptomyces tuirus	10850	\N	\N	\N	\N	Streptomyces tuirus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3183	575	Streptomyces tubercidicus	10849	\N	\N	\N	\N	Streptomyces tubercidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3184	575	Streptomyces tritolerans	10848	\N	\N	\N	\N	Streptomyces tritolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3185	575	Streptomyces tricolor	10847	\N	\N	\N	\N	Streptomyces tricolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3186	575	Streptomyces toxytricini	10846	\N	\N	\N	\N	Streptomyces toxytricini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3187	575	Streptomyces torulosus	10845	\N	\N	\N	\N	Streptomyces torulosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3188	575	Streptomyces thioluteus	10844	\N	\N	\N	\N	Streptomyces thioluteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3189	575	Streptomyces thinghirensis	10843	\N	\N	\N	\N	Streptomyces thinghirensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3190	575	Streptomyces thermovulgaris	10842	\N	\N	\N	\N	Streptomyces thermovulgaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3191	575	Streptomyces thermoviolaceus subsp. thermoviolaceus	10841	\N	\N	\N	\N	Streptomyces thermoviolaceus subsp. thermoviolaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3192	575	Streptomyces thermoviolaceus subsp. apingens	10840	\N	\N	\N	\N	Streptomyces thermoviolaceus subsp. apingens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3193	575	Streptomyces thermospinosisporus	10839	\N	\N	\N	\N	Streptomyces thermospinosisporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3194	575	Streptomyces thermolineatus	10838	\N	\N	\N	\N	Streptomyces thermolineatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3195	575	Streptomyces thermogriseus	10837	\N	\N	\N	\N	Streptomyces thermogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3196	575	Streptomyces thermodiastaticus	10836	\N	\N	\N	\N	Streptomyces thermodiastaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3197	575	Streptomyces thermocoprophilus	10835	\N	\N	\N	\N	Streptomyces thermocoprophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3198	575	Streptomyces thermocarboxydus	10834	\N	\N	\N	\N	Streptomyces thermocarboxydus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3199	575	Streptomyces thermocarboxydovorans	10833	\N	\N	\N	\N	Streptomyces thermocarboxydovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3200	575	Streptomyces thermoalcalitolerans	10832	\N	\N	\N	\N	Streptomyces thermoalcalitolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3201	575	Streptomyces termitum	10831	\N	\N	\N	\N	Streptomyces termitum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3202	575	Streptomyces tendae	10830	\N	\N	\N	\N	Streptomyces tendae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3203	575	Streptomyces tauricus	10829	\N	\N	\N	\N	Streptomyces tauricus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3204	575	Streptomyces tateyamensis	10828	\N	\N	\N	\N	Streptomyces tateyamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3205	575	Streptomyces tanashiensis	10827	\N	\N	\N	\N	Streptomyces tanashiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3206	575	Streptomyces tacrolimicus	10826	\N	\N	\N	\N	Streptomyces tacrolimicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3207	575	Streptomyces synnematoformans	10825	\N	\N	\N	\N	Streptomyces synnematoformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3208	575	Streptomyces sulphureus	10824	\N	\N	\N	\N	Streptomyces sulphureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3209	575	Streptomyces sulfonofaciens	10823	\N	\N	\N	\N	Streptomyces sulfonofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3210	575	Streptomyces subrutilus	10822	\N	\N	\N	\N	Streptomyces subrutilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3211	575	Streptomyces stramineus	10821	\N	\N	\N	\N	Streptomyces stramineus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3212	575	Streptomyces stelliscabiei	10820	\N	\N	\N	\N	Streptomyces stelliscabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3213	575	Streptomyces staurosporininus	10819	\N	\N	\N	\N	Streptomyces staurosporininus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3214	575	Streptomyces sporoverrucosus	10818	\N	\N	\N	\N	Streptomyces sporoverrucosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3215	575	Streptomyces spororaveus	10817	\N	\N	\N	\N	Streptomyces spororaveus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3216	575	Streptomyces sporoclivatus	10816	\N	\N	\N	\N	Streptomyces sporoclivatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3217	575	Streptomyces sporocinereus	10815	\N	\N	\N	\N	Streptomyces sporocinereus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3218	575	Streptomyces spongiae	10814	\N	\N	\N	\N	Streptomyces spongiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3219	575	Streptomyces spiroverticillatus	10813	\N	\N	\N	\N	Streptomyces spiroverticillatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3220	575	Streptomyces spiralis	10812	\N	\N	\N	\N	Streptomyces spiralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3221	575	Streptomyces spinoverrucosus	10811	\N	\N	\N	\N	Streptomyces spinoverrucosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3222	575	Streptomyces speibonae	10810	\N	\N	\N	\N	Streptomyces speibonae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3223	575	Streptomyces spectabilis	10809	\N	\N	\N	\N	Streptomyces spectabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3224	575	Streptomyces specialis	10808	\N	\N	\N	\N	Streptomyces specialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3225	575	Streptomyces sparsus	10807	\N	\N	\N	\N	Streptomyces sparsus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3226	575	Streptomyces sparsogenes	10806	\N	\N	\N	\N	Streptomyces sparsogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3227	575	Streptomyces somaliensis	10805	\N	\N	\N	\N	Streptomyces somaliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3228	575	Streptomyces sodiiphilus	10804	\N	\N	\N	\N	Streptomyces sodiiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3229	575	Streptomyces sioyaensis	10803	\N	\N	\N	\N	Streptomyces sioyaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3230	575	Streptomyces sindenensis	10802	\N	\N	\N	\N	Streptomyces sindenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3231	575	Streptomyces silaceus	10801	\N	\N	\N	\N	Streptomyces silaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3232	575	Streptomyces showdoensis	10800	\N	\N	\N	\N	Streptomyces showdoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3233	575	Streptomyces shaanxiensis	10799	\N	\N	\N	\N	Streptomyces shaanxiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3234	575	Streptomyces seoulensis	10798	\N	\N	\N	\N	Streptomyces seoulensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3235	575	Streptomyces sedi	10797	\N	\N	\N	\N	Streptomyces sedi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3236	575	Streptomyces scopiformis	10796	\N	\N	\N	\N	Streptomyces scopiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3237	575	Streptomyces sclerotialus	10795	\N	\N	\N	\N	Streptomyces sclerotialus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3238	575	Streptomyces scabrisporus	10794	\N	\N	\N	\N	Streptomyces scabrisporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3239	575	Streptomyces scabiei	10793	\N	\N	\N	\N	Streptomyces scabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3240	575	Streptomyces sanyensis	10792	\N	\N	\N	\N	Streptomyces sanyensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3241	575	Streptomyces sannanensis	10791	\N	\N	\N	\N	Streptomyces sannanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3242	575	Streptomyces sanglieri	10790	\N	\N	\N	\N	Streptomyces sanglieri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3243	575	Streptomyces samsunensis	10789	\N	\N	\N	\N	Streptomyces samsunensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3244	575	Streptomyces rutgersensis	10788	\N	\N	\N	\N	Streptomyces rutgersensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3245	575	Streptomyces rubrus	10787	\N	\N	\N	\N	Streptomyces rubrus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3246	575	Streptomyces rubrogriseus	10786	\N	\N	\N	\N	Streptomyces rubrogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3247	575	Streptomyces rubiginosus	10785	\N	\N	\N	\N	Streptomyces rubiginosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3248	575	Streptomyces rubiginosohelvolus	10784	\N	\N	\N	\N	Streptomyces rubiginosohelvolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3249	575	Streptomyces rubidus	10783	\N	\N	\N	\N	Streptomyces rubidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3250	575	Streptomyces ruber	10782	\N	\N	\N	\N	Streptomyces ruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3251	575	Streptomyces roseoviridis	10781	\N	\N	\N	\N	Streptomyces roseoviridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3252	575	Streptomyces roseoviolaceus	10780	\N	\N	\N	\N	Streptomyces roseoviolaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3253	575	Streptomyces roseolus	10779	\N	\N	\N	\N	Streptomyces roseolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3254	575	Streptomyces roseolilacinus	10778	\N	\N	\N	\N	Streptomyces roseolilacinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3255	575	Streptomyces roseofulvus	10777	\N	\N	\N	\N	Streptomyces roseofulvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3256	575	Streptomyces roseiscleroticus	10776	\N	\N	\N	\N	Streptomyces roseiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3257	575	Streptomyces rochei	10775	\N	\N	\N	\N	Streptomyces rochei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3258	575	Streptomyces rishiriensis	10774	\N	\N	\N	\N	Streptomyces rishiriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3259	575	Streptomyces rimosus subsp. rimosus	10773	\N	\N	\N	\N	Streptomyces rimosus subsp. rimosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3260	575	Streptomyces rimosus subsp. paromomycinus	10772	\N	\N	\N	\N	Streptomyces rimosus subsp. paromomycinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3261	575	Streptomyces rhizosphaericus	10771	\N	\N	\N	\N	Streptomyces rhizosphaericus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3262	575	Streptomyces reticuliscabiei	10770	\N	\N	\N	\N	Streptomyces reticuliscabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3263	575	Streptomyces resistomycificus	10769	\N	\N	\N	\N	Streptomyces resistomycificus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3264	575	Streptomyces regensis	10768	\N	\N	\N	\N	Streptomyces regensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3265	575	Streptomyces rectiviolaceus	10767	\N	\N	\N	\N	Streptomyces rectiviolaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3266	575	Streptomyces recifensis	10766	\N	\N	\N	\N	Streptomyces recifensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3267	575	Streptomyces rapamycinicus	10765	\N	\N	\N	\N	Streptomyces rapamycinicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3268	575	Streptomyces rangoonensis	10764	\N	\N	\N	\N	Streptomyces rangoonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3269	575	Streptomyces ramulosus	10763	\N	\N	\N	\N	Streptomyces ramulosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3270	575	Streptomyces rameus	10762	\N	\N	\N	\N	Streptomyces rameus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3271	575	Streptomyces radiopugnans	10761	\N	\N	\N	\N	Streptomyces radiopugnans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3272	575	Streptomyces racemochromogenes	10760	\N	\N	\N	\N	Streptomyces racemochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3273	575	Streptomyces qinglanensis	10759	\N	\N	\N	\N	Streptomyces qinglanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3274	575	Streptomyces purpurogeneiscleroticus	10758	\N	\N	\N	\N	Streptomyces purpurogeneiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3275	575	Streptomyces purpureus	10757	\N	\N	\N	\N	Streptomyces purpureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3276	575	Streptomyces purpurascens	10756	\N	\N	\N	\N	Streptomyces purpurascens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3277	575	Streptomyces purpeofuscus	10755	\N	\N	\N	\N	Streptomyces purpeofuscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3278	575	Streptomyces puniciscabiei	10754	\N	\N	\N	\N	Streptomyces puniciscabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3279	575	Streptomyces puniceus	10753	\N	\N	\N	\N	Streptomyces puniceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3280	575	Streptomyces pulveraceus	10752	\N	\N	\N	\N	Streptomyces pulveraceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3281	575	Streptomyces pseudovenezuelae	10751	\N	\N	\N	\N	Streptomyces pseudovenezuelae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3282	575	Streptomyces pseudogriseolus	10750	\N	\N	\N	\N	Streptomyces pseudogriseolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3283	575	Streptomyces pseudoechinosporeus	10749	\N	\N	\N	\N	Streptomyces pseudoechinosporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3284	575	Streptomyces psammoticus	10748	\N	\N	\N	\N	Streptomyces psammoticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3285	575	Streptomyces prunicolor	10747	\N	\N	\N	\N	Streptomyces prunicolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3286	575	Streptomyces pratens	10746	\N	\N	\N	\N	Streptomyces pratens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3287	575	Streptomyces prasinus	10745	\N	\N	\N	\N	Streptomyces prasinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3288	575	Streptomyces prasinosporus	10744	\N	\N	\N	\N	Streptomyces prasinosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3289	575	Streptomyces prasinopilosus	10743	\N	\N	\N	\N	Streptomyces prasinopilosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3290	575	Streptomyces poonensis	10742	\N	\N	\N	\N	Streptomyces poonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3291	575	Streptomyces polychromogenes	10741	\N	\N	\N	\N	Streptomyces polychromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3292	575	Streptomyces polyantibioticus	10740	\N	\N	\N	\N	Streptomyces polyantibioticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3293	575	Streptomyces pluricolorescens	10739	\N	\N	\N	\N	Streptomyces pluricolorescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3294	575	Streptomyces plumbiresistens	10738	\N	\N	\N	\N	Streptomyces plumbiresistens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3295	575	Streptomyces platensis	10737	\N	\N	\N	\N	Streptomyces platensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3296	575	Streptomyces pilosus	10736	\N	\N	\N	\N	Streptomyces pilosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3297	575	Streptomyces pharmamarensis	10735	\N	\N	\N	\N	Streptomyces pharmamarensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3298	575	Streptomyces pharetrae	10734	\N	\N	\N	\N	Streptomyces pharetrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3299	575	Streptomyces phaeopurpureus	10733	\N	\N	\N	\N	Streptomyces phaeopurpureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3300	575	Streptomyces phaeoluteigriseus	10732	\N	\N	\N	\N	Streptomyces phaeoluteigriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3301	575	Streptomyces phaeoluteichromatogenes	10731	\N	\N	\N	\N	Streptomyces phaeoluteichromatogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3302	575	Streptomyces phaeofaciens	10730	\N	\N	\N	\N	Streptomyces phaeofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3303	575	Streptomyces phaeochromogenes	10729	\N	\N	\N	\N	Streptomyces phaeochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3304	575	Streptomyces peucetius	10728	\N	\N	\N	\N	Streptomyces peucetius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3305	575	Streptomyces paucisporeus	10727	\N	\N	\N	\N	Streptomyces paucisporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3306	575	Streptomyces parvus	10726	\N	\N	\N	\N	Streptomyces parvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3307	575	Streptomyces parvulus	10725	\N	\N	\N	\N	Streptomyces parvulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3308	575	Streptomyces paradoxus	10724	\N	\N	\N	\N	Streptomyces paradoxus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3309	575	Streptomyces panacagri	10723	\N	\N	\N	\N	Streptomyces panacagri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3310	575	Streptomyces pactum	10722	\N	\N	\N	\N	Streptomyces pactum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3311	575	Streptomyces osmaniensis	10721	\N	\N	\N	\N	Streptomyces osmaniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3312	575	Streptomyces orinoci	10720	\N	\N	\N	\N	Streptomyces orinoci	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3313	575	Streptomyces omiyaensis	10719	\N	\N	\N	\N	Streptomyces omiyaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3314	575	Streptomyces olivoverticillatus	10718	\N	\N	\N	\N	Streptomyces olivoverticillatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3315	575	Streptomyces olivochromogenes	10717	\N	\N	\N	\N	Streptomyces olivochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3316	575	Streptomyces olivaceus	10716	\N	\N	\N	\N	Streptomyces olivaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3317	575	Streptomyces olivaceoviridis	10715	\N	\N	\N	\N	Streptomyces olivaceoviridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3318	575	Streptomyces olivaceiscleroticus	10714	\N	\N	\N	\N	Streptomyces olivaceiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3319	575	Streptomyces ochraceiscleroticus	10713	\N	\N	\N	\N	Streptomyces ochraceiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3320	575	Streptomyces novaecaesareae	10712	\N	\N	\N	\N	Streptomyces novaecaesareae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3321	575	Streptomyces noursei	10711	\N	\N	\N	\N	Streptomyces noursei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3322	575	Streptomyces nojiriensis	10710	\N	\N	\N	\N	Streptomyces nojiriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3323	575	Streptomyces nogalater	10709	\N	\N	\N	\N	Streptomyces nogalater	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3324	575	Streptomyces nodosus	10708	\N	\N	\N	\N	Streptomyces nodosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3325	575	Streptomyces noboritoensis	10707	\N	\N	\N	\N	Streptomyces noboritoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3326	575	Streptomyces niveoruber	10706	\N	\N	\N	\N	Streptomyces niveoruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3327	575	Streptomyces niveiscabiei	10705	\N	\N	\N	\N	Streptomyces niveiscabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3328	575	Streptomyces nitrosporeus	10704	\N	\N	\N	\N	Streptomyces nitrosporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3329	575	Streptomyces nigrescens	10703	\N	\N	\N	\N	Streptomyces nigrescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3330	575	Streptomyces niger	10702	\N	\N	\N	\N	Streptomyces niger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3331	575	Streptomyces neyagawaensis	10701	\N	\N	\N	\N	Streptomyces neyagawaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3332	575	Streptomyces netropsis	10700	\N	\N	\N	\N	Streptomyces netropsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3333	575	Streptomyces nashvillensis	10699	\N	\N	\N	\N	Streptomyces nashvillensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3334	575	Streptomyces narbonensis	10698	\N	\N	\N	\N	Streptomyces narbonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3335	575	Streptomyces nanshensis	10697	\N	\N	\N	\N	Streptomyces nanshensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3336	575	Streptomyces nanhaiensis	10696	\N	\N	\N	\N	Streptomyces nanhaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3337	575	Streptomyces naganishii	10695	\N	\N	\N	\N	Streptomyces naganishii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3338	575	Streptomyces mutomycini	10694	\N	\N	\N	\N	Streptomyces mutomycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3339	575	Streptomyces mutabilis	10693	\N	\N	\N	\N	Streptomyces mutabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3340	575	Streptomyces murinus	10692	\N	\N	\N	\N	Streptomyces murinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3341	575	Streptomyces morookaense	10691	\N	\N	\N	\N	Streptomyces morookaense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3342	575	Streptomyces mordarskii	10690	\N	\N	\N	\N	Streptomyces mordarskii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3343	575	Streptomyces monomycini	10689	\N	\N	\N	\N	Streptomyces monomycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3344	575	Streptomyces mobaraensis	10688	\N	\N	\N	\N	Streptomyces mobaraensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3345	575	Streptomyces misionensis	10687	\N	\N	\N	\N	Streptomyces misionensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3346	575	Streptomyces misakiensis	10686	\N	\N	\N	\N	Streptomyces misakiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3347	575	Streptomyces mirabilis	10685	\N	\N	\N	\N	Streptomyces mirabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3348	575	Streptomyces minutiscleroticus	10684	\N	\N	\N	\N	Streptomyces minutiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3349	575	Streptomyces milbemycinicus	10683	\N	\N	\N	\N	Streptomyces milbemycinicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3350	575	Streptomyces microflavus	10682	\N	\N	\N	\N	Streptomyces microflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3351	575	Streptomyces michiganensis	10681	\N	\N	\N	\N	Streptomyces michiganensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3352	575	Streptomyces mexicanus	10680	\N	\N	\N	\N	Streptomyces mexicanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3353	575	Streptomyces melanosporofaciens	10679	\N	\N	\N	\N	Streptomyces melanosporofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3354	575	Streptomyces melanogenes	10678	\N	\N	\N	\N	Streptomyces melanogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3355	575	Streptomyces megasporus	10677	\N	\N	\N	\N	Streptomyces megasporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3356	575	Streptomyces mauvecolor	10676	\N	\N	\N	\N	Streptomyces mauvecolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3357	575	Streptomyces matensis	10675	\N	\N	\N	\N	Streptomyces matensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3358	575	Streptomyces massasporeus	10674	\N	\N	\N	\N	Streptomyces massasporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3359	575	Streptomyces mashuensis	10673	\N	\N	\N	\N	Streptomyces mashuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3360	575	Streptomyces marokkonensis	10672	\N	\N	\N	\N	Streptomyces marokkonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3361	575	Streptomyces marinus	10671	\N	\N	\N	\N	Streptomyces marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3362	575	Streptomyces malaysiensis	10670	\N	\N	\N	\N	Streptomyces malaysiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3363	575	Streptomyces malachitospinus	10669	\N	\N	\N	\N	Streptomyces malachitospinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3364	575	Streptomyces malachitofuscus	10668	\N	\N	\N	\N	Streptomyces malachitofuscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3365	575	Streptomyces macrosporus	10667	\N	\N	\N	\N	Streptomyces macrosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3366	575	Streptomyces lydicus	10666	\N	\N	\N	\N	Streptomyces lydicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3367	575	Streptomyces luteosporeus	10665	\N	\N	\N	\N	Streptomyces luteosporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3368	575	Streptomyces luteogriseus	10664	\N	\N	\N	\N	Streptomyces luteogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3369	575	Streptomyces luteireticuli	10663	\N	\N	\N	\N	Streptomyces luteireticuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3370	575	Streptomyces lusitanus	10662	\N	\N	\N	\N	Streptomyces lusitanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3371	575	Streptomyces luridus	10661	\N	\N	\N	\N	Streptomyces luridus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3372	575	Streptomyces lunalinharesii	10660	\N	\N	\N	\N	Streptomyces lunalinharesii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3373	575	Streptomyces lucensis	10659	\N	\N	\N	\N	Streptomyces lucensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3374	575	Streptomyces longwoodensis	10658	\N	\N	\N	\N	Streptomyces longwoodensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3375	575	Streptomyces longisporus	10657	\N	\N	\N	\N	Streptomyces longisporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3376	575	Streptomyces longispororuber	10656	\N	\N	\N	\N	Streptomyces longispororuber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3377	575	Streptomyces longisporoflavus	10655	\N	\N	\N	\N	Streptomyces longisporoflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3378	575	Streptomyces lomondensis	10654	\N	\N	\N	\N	Streptomyces lomondensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3379	575	Streptomyces litmocidini	10653	\N	\N	\N	\N	Streptomyces litmocidini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3380	575	Streptomyces lincolnensis	10652	\N	\N	\N	\N	Streptomyces lincolnensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3381	575	Streptomyces lilacinus	10651	\N	\N	\N	\N	Streptomyces lilacinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3382	575	Streptomyces lienomycini	10650	\N	\N	\N	\N	Streptomyces lienomycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3383	575	Streptomyces libani subsp. rufus	10649	\N	\N	\N	\N	Streptomyces libani subsp. rufus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3384	575	Streptomyces libani subsp. libani	10648	\N	\N	\N	\N	Streptomyces libani subsp. libani	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3385	575	Streptomyces levis	10647	\N	\N	\N	\N	Streptomyces levis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3386	575	Streptomyces lavendulocolor	10646	\N	\N	\N	\N	Streptomyces lavendulocolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3387	575	Streptomyces lavenduligriseus	10645	\N	\N	\N	\N	Streptomyces lavenduligriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3388	575	Streptomyces lavendulae subsp. lavendulae	10644	\N	\N	\N	\N	Streptomyces lavendulae subsp. lavendulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3389	575	Streptomyces lavendulae subsp. grasserius	10643	\N	\N	\N	\N	Streptomyces lavendulae subsp. grasserius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3390	575	Streptomyces lavendofoliae	10642	\N	\N	\N	\N	Streptomyces lavendofoliae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3391	575	Streptomyces laurentii	10641	\N	\N	\N	\N	Streptomyces laurentii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3392	575	Streptomyces lateritius	10640	\N	\N	\N	\N	Streptomyces lateritius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3393	575	Streptomyces lanatus	10639	\N	\N	\N	\N	Streptomyces lanatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3394	575	Streptomyces laculatispora	10638	\N	\N	\N	\N	Streptomyces laculatispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3395	575	Streptomyces lacticiproducens	10637	\N	\N	\N	\N	Streptomyces lacticiproducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3396	575	Streptomyces labedae	10636	\N	\N	\N	\N	Streptomyces labedae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3397	575	Streptomyces kurssanovii	10635	\N	\N	\N	\N	Streptomyces kurssanovii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3398	575	Streptomyces kunmingensis	10634	\N	\N	\N	\N	Streptomyces kunmingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3399	575	Streptomyces koyangensis	10633	\N	\N	\N	\N	Streptomyces koyangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3400	575	Streptomyces katrae	10632	\N	\N	\N	\N	Streptomyces katrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3401	575	Streptomyces kasugaensis	10631	\N	\N	\N	\N	Streptomyces kasugaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3402	575	Streptomyces kanamyceticus	10630	\N	\N	\N	\N	Streptomyces kanamyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3403	575	Streptomyces jietaisiensis	10629	\N	\N	\N	\N	Streptomyces jietaisiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3404	575	Streptomyces javensis	10628	\N	\N	\N	\N	Streptomyces javensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3405	575	Streptomyces janthinus	10627	\N	\N	\N	\N	Streptomyces janthinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3406	575	Streptomyces iranensis	10626	\N	\N	\N	\N	Streptomyces iranensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3407	575	Streptomyces ipomoeae	10625	\N	\N	\N	\N	Streptomyces ipomoeae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3408	575	Streptomyces inusitatus	10624	\N	\N	\N	\N	Streptomyces inusitatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3409	575	Streptomyces intermedius	10623	\N	\N	\N	\N	Streptomyces intermedius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3410	575	Streptomyces indonesiensis	10622	\N	\N	\N	\N	Streptomyces indonesiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3411	575	Streptomyces indigoferus	10621	\N	\N	\N	\N	Streptomyces indigoferus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3412	575	Streptomyces indicus	10620	\N	\N	\N	\N	Streptomyces indicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3413	575	Streptomyces indiaensis	10619	\N	\N	\N	\N	Streptomyces indiaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3414	575	Streptomyces incanus	10618	\N	\N	\N	\N	Streptomyces incanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3415	575	Streptomyces iakyrus	10617	\N	\N	\N	\N	Streptomyces iakyrus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3416	575	Streptomyces hypolithicus	10616	\N	\N	\N	\N	Streptomyces hypolithicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3417	575	Streptomyces hygroscopicus subsp. ossamyceticus	10615	\N	\N	\N	\N	Streptomyces hygroscopicus subsp. ossamyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3418	575	Streptomyces hygroscopicus subsp. hygroscopicus	10614	\N	\N	\N	\N	Streptomyces hygroscopicus subsp. hygroscopicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3419	575	Streptomyces hygroscopicus subsp. glebosus	10613	\N	\N	\N	\N	Streptomyces hygroscopicus subsp. glebosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3420	575	Streptomyces hygroscopicus subsp. decoyicus	10612	\N	\N	\N	\N	Streptomyces hygroscopicus subsp. decoyicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3421	575	Streptomyces hydrogenans	10611	\N	\N	\N	\N	Streptomyces hydrogenans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3422	575	Streptomyces hyderabadensis	10610	\N	\N	\N	\N	Streptomyces hyderabadensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3423	575	Streptomyces humiferus	10609	\N	\N	\N	\N	Streptomyces humiferus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3424	575	Streptomyces humidus	10608	\N	\N	\N	\N	Streptomyces humidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3425	575	Streptomyces hirsutus	10607	\N	\N	\N	\N	Streptomyces hirsutus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3426	575	Streptomyces hiroshimensis	10606	\N	\N	\N	\N	Streptomyces hiroshimensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3427	575	Streptomyces himastatinicus	10605	\N	\N	\N	\N	Streptomyces himastatinicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3428	575	Streptomyces herbaricolor	10604	\N	\N	\N	\N	Streptomyces herbaricolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3429	575	Streptomyces herbaceus	10603	\N	\N	\N	\N	Streptomyces herbaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3430	575	Streptomyces helvaticus	10602	\N	\N	\N	\N	Streptomyces helvaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3431	575	Streptomyces heliomycini	10601	\N	\N	\N	\N	Streptomyces heliomycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3432	575	Streptomyces hebeiensis	10600	\N	\N	\N	\N	Streptomyces hebeiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3433	575	Streptomyces hawaiiensis	10599	\N	\N	\N	\N	Streptomyces hawaiiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3434	575	Streptomyces halstedii	10598	\N	\N	\N	\N	Streptomyces halstedii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3435	575	Streptomyces haliclonae	10597	\N	\N	\N	\N	Streptomyces haliclonae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3436	575	Streptomyces hainanensis	10596	\N	\N	\N	\N	Streptomyces hainanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3437	575	Streptomyces gulbargensis	10595	\N	\N	\N	\N	Streptomyces gulbargensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3438	575	Streptomyces guanduensis	10594	\N	\N	\N	\N	Streptomyces guanduensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3439	575	Streptomyces griseus	10593	\N	\N	\N	\N	Streptomyces griseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3440	575	Streptomyces griseoviridis	10592	\N	\N	\N	\N	Streptomyces griseoviridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3441	575	Streptomyces griseostramineus	10591	\N	\N	\N	\N	Streptomyces griseostramineus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3442	575	Streptomyces griseosporeus	10590	\N	\N	\N	\N	Streptomyces griseosporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3443	575	Streptomyces griseorubiginosus	10589	\N	\N	\N	\N	Streptomyces griseorubiginosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3444	575	Streptomyces griseoruber	10588	\N	\N	\N	\N	Streptomyces griseoruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3445	575	Streptomyces griseorubens	10587	\N	\N	\N	\N	Streptomyces griseorubens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3446	575	Streptomyces griseoplanus	10586	\N	\N	\N	\N	Streptomyces griseoplanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3447	575	Streptomyces griseomycini	10585	\N	\N	\N	\N	Streptomyces griseomycini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3448	575	Streptomyces griseoluteus	10584	\N	\N	\N	\N	Streptomyces griseoluteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3449	575	Streptomyces griseolus	10583	\N	\N	\N	\N	Streptomyces griseolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3450	575	Streptomyces griseoloalbus	10582	\N	\N	\N	\N	Streptomyces griseoloalbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3451	575	Streptomyces griseoincarnatus	10581	\N	\N	\N	\N	Streptomyces griseoincarnatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3452	575	Streptomyces griseofuscus	10580	\N	\N	\N	\N	Streptomyces griseofuscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3453	575	Streptomyces griseoflavus	10579	\N	\N	\N	\N	Streptomyces griseoflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3454	575	Streptomyces griseochromogenes	10578	\N	\N	\N	\N	Streptomyces griseochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3455	575	Streptomyces griseocarneus	10577	\N	\N	\N	\N	Streptomyces griseocarneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3456	575	Streptomyces griseoaurantiacus	10576	\N	\N	\N	\N	Streptomyces griseoaurantiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3457	575	Streptomyces griseiniger	10575	\N	\N	\N	\N	Streptomyces griseiniger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3458	575	Streptomyces graminearus	10574	\N	\N	\N	\N	Streptomyces graminearus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3459	575	Streptomyces gougerotii	10573	\N	\N	\N	\N	Streptomyces gougerotii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3460	575	Streptomyces goshikiensis	10572	\N	\N	\N	\N	Streptomyces goshikiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3461	575	Streptomyces gobitricini	10571	\N	\N	\N	\N	Streptomyces gobitricini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3462	575	Streptomyces glomeroaurantiacus	10570	\N	\N	\N	\N	Streptomyces glomeroaurantiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3463	575	Streptomyces glomeratus	10569	\N	\N	\N	\N	Streptomyces glomeratus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3464	575	Streptomyces globosus	10568	\N	\N	\N	\N	Streptomyces globosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3465	575	Streptomyces globisporus	10567	\N	\N	\N	\N	Streptomyces globisporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3466	575	Streptomyces glaucus	10566	\N	\N	\N	\N	Streptomyces glaucus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3467	575	Streptomyces glaucosporus	10565	\N	\N	\N	\N	Streptomyces glaucosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3468	575	Streptomyces glauciniger	10564	\N	\N	\N	\N	Streptomyces glauciniger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3469	575	Streptomyces glaucescens	10563	\N	\N	\N	\N	Streptomyces glaucescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3470	575	Streptomyces gibsonii	10562	\N	\N	\N	\N	Streptomyces gibsonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3471	575	Streptomyces ghanaensis	10561	\N	\N	\N	\N	Streptomyces ghanaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3472	575	Streptomyces geysiriensis	10560	\N	\N	\N	\N	Streptomyces geysiriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3473	575	Streptomyces geldanamycininus	10559	\N	\N	\N	\N	Streptomyces geldanamycininus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3474	575	Streptomyces gelaticus	10558	\N	\N	\N	\N	Streptomyces gelaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3475	575	Streptomyces gardneri	10557	\N	\N	\N	\N	Streptomyces gardneri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3476	575	Streptomyces gancidicus	10556	\N	\N	\N	\N	Streptomyces gancidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3477	575	Streptomyces galilaeus	10555	\N	\N	\N	\N	Streptomyces galilaeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3478	575	Streptomyces galbus	10554	\N	\N	\N	\N	Streptomyces galbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3479	575	Streptomyces fumigatiscleroticus	10553	\N	\N	\N	\N	Streptomyces fumigatiscleroticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3480	575	Streptomyces fumanus	10552	\N	\N	\N	\N	Streptomyces fumanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3481	575	Streptomyces fulvorobeus	10551	\N	\N	\N	\N	Streptomyces fulvorobeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3482	575	Streptomyces fulvissimus	10550	\N	\N	\N	\N	Streptomyces fulvissimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3483	575	Streptomyces fragilis	10549	\N	\N	\N	\N	Streptomyces fragilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3484	575	Streptomyces fradiae	10548	\N	\N	\N	\N	Streptomyces fradiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3485	575	Streptomyces flocculus	10547	\N	\N	\N	\N	Streptomyces flocculus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3486	575	Streptomyces flavoviridis	10546	\N	\N	\N	\N	Streptomyces flavoviridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3487	575	Streptomyces flavovirens	10545	\N	\N	\N	\N	Streptomyces flavovirens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3488	575	Streptomyces flavovariabilis	10544	\N	\N	\N	\N	Streptomyces flavovariabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3489	575	Streptomyces flavogriseus	10543	\N	\N	\N	\N	Streptomyces flavogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3490	575	Streptomyces flavofungini	10542	\N	\N	\N	\N	Streptomyces flavofungini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3491	575	Streptomyces flavidovirens	10541	\N	\N	\N	\N	Streptomyces flavidovirens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3492	575	Streptomyces flaveus	10540	\N	\N	\N	\N	Streptomyces flaveus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3493	575	Streptomyces flaveolus	10539	\N	\N	\N	\N	Streptomyces flaveolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3494	575	Streptomyces finlayi	10538	\N	\N	\N	\N	Streptomyces finlayi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3495	575	Streptomyces fimicarius	10537	\N	\N	\N	\N	Streptomyces fimicarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3496	575	Streptomyces fimbriatus	10536	\N	\N	\N	\N	Streptomyces fimbriatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3497	575	Streptomyces filipinensis	10535	\N	\N	\N	\N	Streptomyces filipinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3498	575	Streptomyces filamentosus	10534	\N	\N	\N	\N	Streptomyces filamentosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3499	575	Streptomyces ferralitis	10533	\N	\N	\N	\N	Streptomyces ferralitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3500	575	Streptomyces fenghuangensis	10532	\N	\N	\N	\N	Streptomyces fenghuangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3501	575	Streptomyces exfoliatus	10531	\N	\N	\N	\N	Streptomyces exfoliatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3502	575	Streptomyces eurythermus	10530	\N	\N	\N	\N	Streptomyces eurythermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3503	575	Streptomyces europaeiscabiei	10529	\N	\N	\N	\N	Streptomyces europaeiscabiei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3504	575	Streptomyces eurocidicus	10528	\N	\N	\N	\N	Streptomyces eurocidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3505	575	Streptomyces erythrogriseus	10527	\N	\N	\N	\N	Streptomyces erythrogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3506	575	Streptomyces enissocaesilis	10526	\N	\N	\N	\N	Streptomyces enissocaesilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3507	575	Streptomyces endus	10525	\N	\N	\N	\N	Streptomyces endus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3508	575	Streptomyces emeiensis	10524	\N	\N	\N	\N	Streptomyces emeiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3509	575	Streptomyces ederensis	10523	\N	\N	\N	\N	Streptomyces ederensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3510	575	Streptomyces echinatus	10522	\N	\N	\N	\N	Streptomyces echinatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3511	575	Streptomyces durmitorensis	10521	\N	\N	\N	\N	Streptomyces durmitorensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3512	575	Streptomyces durhamensis	10520	\N	\N	\N	\N	Streptomyces durhamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3513	575	Streptomyces drozdowiczii	10519	\N	\N	\N	\N	Streptomyces drozdowiczii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3514	575	Streptomyces djakartensis	10518	\N	\N	\N	\N	Streptomyces djakartensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3515	575	Streptomyces diastatochromogenes	10517	\N	\N	\N	\N	Streptomyces diastatochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3516	575	Streptomyces diastaticus subsp. diastaticus	10516	\N	\N	\N	\N	Streptomyces diastaticus subsp. diastaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3517	575	Streptomyces diastaticus subsp. ardesiacus	10515	\N	\N	\N	\N	Streptomyces diastaticus subsp. ardesiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3518	575	Streptomyces demainii	10514	\N	\N	\N	\N	Streptomyces demainii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3519	575	Streptomyces decoyicus	10513	\N	\N	\N	\N	Streptomyces decoyicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3520	575	Streptomyces deccanensis	10512	\N	\N	\N	\N	Streptomyces deccanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3521	575	Streptomyces daghestanicus	10511	\N	\N	\N	\N	Streptomyces daghestanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3522	575	Streptomyces cyanoalbus	10510	\N	\N	\N	\N	Streptomyces cyanoalbus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3523	575	Streptomyces cyaneus	10509	\N	\N	\N	\N	Streptomyces cyaneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3524	575	Streptomyces cyaneofuscatus	10508	\N	\N	\N	\N	Streptomyces cyaneofuscatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3525	575	Streptomyces cuspidosporus	10507	\N	\N	\N	\N	Streptomyces cuspidosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3526	575	Streptomyces curacoi	10506	\N	\N	\N	\N	Streptomyces curacoi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3527	575	Streptomyces crystallinus	10505	\N	\N	\N	\N	Streptomyces crystallinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3528	575	Streptomyces cremeus	10504	\N	\N	\N	\N	Streptomyces cremeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3529	575	Streptomyces costaricanus	10503	\N	\N	\N	\N	Streptomyces costaricanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3530	575	Streptomyces corchorusii	10502	\N	\N	\N	\N	Streptomyces corchorusii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3531	575	Streptomyces colombiensis	10501	\N	\N	\N	\N	Streptomyces colombiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3532	575	Streptomyces collinus	10500	\N	\N	\N	\N	Streptomyces collinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3533	575	Streptomyces coerulescens	10499	\N	\N	\N	\N	Streptomyces coerulescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3534	575	Streptomyces coeruleorubidus	10498	\N	\N	\N	\N	Streptomyces coeruleorubidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3535	575	Streptomyces coeruleoprunus	10497	\N	\N	\N	\N	Streptomyces coeruleoprunus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3536	575	Streptomyces coeruleofuscus	10496	\N	\N	\N	\N	Streptomyces coeruleofuscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3537	575	Streptomyces coelicoflavus	10495	\N	\N	\N	\N	Streptomyces coelicoflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3538	575	Streptomyces coelescens	10494	\N	\N	\N	\N	Streptomyces coelescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3539	575	Streptomyces cocklensis	10493	\N	\N	\N	\N	Streptomyces cocklensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3540	575	Streptomyces coacervatus	10492	\N	\N	\N	\N	Streptomyces coacervatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3541	575	Streptomyces clavuligerus	10491	\N	\N	\N	\N	Streptomyces clavuligerus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3542	575	Streptomyces clavifer	10490	\N	\N	\N	\N	Streptomyces clavifer	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3543	575	Streptomyces ciscaucasicus	10489	\N	\N	\N	\N	Streptomyces ciscaucasicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3544	575	Streptomyces cirratus	10488	\N	\N	\N	\N	Streptomyces cirratus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3545	575	Streptomyces cinnamoneus	10487	\N	\N	\N	\N	Streptomyces cinnamoneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3546	575	Streptomyces cinnamonensis	10486	\N	\N	\N	\N	Streptomyces cinnamonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3547	575	Streptomyces cinnabarinus	10485	\N	\N	\N	\N	Streptomyces cinnabarinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3548	575	Streptomyces cinerochromogenes	10484	\N	\N	\N	\N	Streptomyces cinerochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3549	575	Streptomyces cinereus	10483	\N	\N	\N	\N	Streptomyces cinereus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3550	575	Streptomyces cinereospinus	10482	\N	\N	\N	\N	Streptomyces cinereospinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3551	575	Streptomyces cinereoruber subsp. fructofermentans	10481	\N	\N	\N	\N	Streptomyces cinereoruber subsp. fructofermentans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3552	575	Streptomyces cinereoruber subsp. cinereoruber	10480	\N	\N	\N	\N	Streptomyces cinereoruber subsp. cinereoruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3553	575	Streptomyces cinereorectus	10479	\N	\N	\N	\N	Streptomyces cinereorectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3554	575	Streptomyces chrysomallus subsp. fumigatus	10478	\N	\N	\N	\N	Streptomyces chrysomallus subsp. fumigatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3555	575	Streptomyces chrysomallus subsp. chrysomallus	10477	\N	\N	\N	\N	Streptomyces chrysomallus subsp. chrysomallus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3556	575	Streptomyces chryseus	10476	\N	\N	\N	\N	Streptomyces chryseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3557	575	Streptomyces chromofuscus	10475	\N	\N	\N	\N	Streptomyces chromofuscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3558	575	Streptomyces chrestomyceticus	10474	\N	\N	\N	\N	Streptomyces chrestomyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3559	575	Streptomyces cheonanensis	10473	\N	\N	\N	\N	Streptomyces cheonanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3560	575	Streptomyces chattanoogensis	10472	\N	\N	\N	\N	Streptomyces chattanoogensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3561	575	Streptomyces chartreusis	10471	\N	\N	\N	\N	Streptomyces chartreusis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3562	575	Streptomyces cellulosae	10470	\N	\N	\N	\N	Streptomyces cellulosae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3563	575	Streptomyces celluloflavus	10469	\N	\N	\N	\N	Streptomyces celluloflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3564	575	Streptomyces cellostaticus	10468	\N	\N	\N	\N	Streptomyces cellostaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3565	575	Streptomyces cavourensis	10467	\N	\N	\N	\N	Streptomyces cavourensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3566	575	Streptomyces catenulae	10466	\N	\N	\N	\N	Streptomyces catenulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3567	575	Streptomyces castelarensis	10465	\N	\N	\N	\N	Streptomyces castelarensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3568	575	Streptomyces carpinensis	10464	\N	\N	\N	\N	Streptomyces carpinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3569	575	Streptomyces carpaticus	10463	\N	\N	\N	\N	Streptomyces carpaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3570	575	Streptomyces capoamus	10462	\N	\N	\N	\N	Streptomyces capoamus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3571	575	Streptomyces capillispiralis	10461	\N	\N	\N	\N	Streptomyces capillispiralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3572	575	Streptomyces canus	10460	\N	\N	\N	\N	Streptomyces canus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3573	575	Streptomyces caniferus	10459	\N	\N	\N	\N	Streptomyces caniferus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3574	575	Streptomyces cangkringensis	10458	\N	\N	\N	\N	Streptomyces cangkringensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3575	575	Streptomyces candidus	10457	\N	\N	\N	\N	Streptomyces candidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3576	575	Streptomyces canarius	10456	\N	\N	\N	\N	Streptomyces canarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3577	575	Streptomyces calvus	10455	\N	\N	\N	\N	Streptomyces calvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3578	575	Streptomyces caeruleus	10454	\N	\N	\N	\N	Streptomyces caeruleus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3579	575	Streptomyces caeruleatus	10453	\N	\N	\N	\N	Streptomyces caeruleatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3580	575	Streptomyces caelestis	10452	\N	\N	\N	\N	Streptomyces caelestis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3581	575	Streptomyces cacaoi subsp. cacaoi	10451	\N	\N	\N	\N	Streptomyces cacaoi subsp. cacaoi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3582	575	Streptomyces cacaoi subsp. asoensis	10450	\N	\N	\N	\N	Streptomyces cacaoi subsp. asoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3583	575	Streptomyces bungoensis	10449	\N	\N	\N	\N	Streptomyces bungoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3584	575	Streptomyces brevispora	10448	\N	\N	\N	\N	Streptomyces brevispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3585	575	Streptomyces brasiliensis	10447	\N	\N	\N	\N	Streptomyces brasiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3586	575	Streptomyces bottropensis	10446	\N	\N	\N	\N	Streptomyces bottropensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3587	575	Streptomyces bobili	10445	\N	\N	\N	\N	Streptomyces bobili	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3588	575	Streptomyces bluensis	10444	\N	\N	\N	\N	Streptomyces bluensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3589	575	Streptomyces blastmyceticus	10443	\N	\N	\N	\N	Streptomyces blastmyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3590	575	Streptomyces bikiniensis	10442	\N	\N	\N	\N	Streptomyces bikiniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3591	575	Streptomyces bellus	10441	\N	\N	\N	\N	Streptomyces bellus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3592	575	Streptomyces beijiangensis	10440	\N	\N	\N	\N	Streptomyces beijiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3593	575	Streptomyces bangladeshensis	10439	\N	\N	\N	\N	Streptomyces bangladeshensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3594	575	Streptomyces bambergiensis	10438	\N	\N	\N	\N	Streptomyces bambergiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3595	575	Streptomyces baliensis	10437	\N	\N	\N	\N	Streptomyces baliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3596	575	Streptomyces badius	10436	\N	\N	\N	\N	Streptomyces badius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3597	575	Streptomyces bacillaris	10435	\N	\N	\N	\N	Streptomyces bacillaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3598	575	Streptomyces azureus	10434	\N	\N	\N	\N	Streptomyces azureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3599	575	Streptomyces axinellae	10433	\N	\N	\N	\N	Streptomyces axinellae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3600	575	Streptomyces avidinii	10432	\N	\N	\N	\N	Streptomyces avidinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3601	575	Streptomyces avicenniae	10431	\N	\N	\N	\N	Streptomyces avicenniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3602	575	Streptomyces avermitilis	10430	\N	\N	\N	\N	Streptomyces avermitilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3603	575	Streptomyces avellaneus	10429	\N	\N	\N	\N	Streptomyces avellaneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3604	575	Streptomyces aureus	10428	\N	\N	\N	\N	Streptomyces aureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3605	575	Streptomyces aureoverticillatus	10427	\N	\N	\N	\N	Streptomyces aureoverticillatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3606	575	Streptomyces aureorectus	10426	\N	\N	\N	\N	Streptomyces aureorectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3607	575	Streptomyces aureofaciens	10425	\N	\N	\N	\N	Streptomyces aureofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3608	575	Streptomyces aureocirculatus	10424	\N	\N	\N	\N	Streptomyces aureocirculatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3609	575	Streptomyces auratus	10423	\N	\N	\N	\N	Streptomyces auratus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3610	575	Streptomyces aurantiogriseus	10422	\N	\N	\N	\N	Streptomyces aurantiogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3611	575	Streptomyces aurantiacus	10421	\N	\N	\N	\N	Streptomyces aurantiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3612	575	Streptomyces atrovirens	10420	\N	\N	\N	\N	Streptomyces atrovirens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3613	575	Streptomyces atroolivaceus	10419	\N	\N	\N	\N	Streptomyces atroolivaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3614	575	Streptomyces atriruber	10418	\N	\N	\N	\N	Streptomyces atriruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3615	575	Streptomyces atratus	10417	\N	\N	\N	\N	Streptomyces atratus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3616	575	Streptomyces asterosporus	10416	\N	\N	\N	\N	Streptomyces asterosporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3617	575	Streptomyces asiaticus	10415	\N	\N	\N	\N	Streptomyces asiaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3618	575	Streptomyces ascomycinicus	10414	\N	\N	\N	\N	Streptomyces ascomycinicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3619	575	Streptomyces artemisiae	10413	\N	\N	\N	\N	Streptomyces artemisiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3620	575	Streptomyces armeniacus	10412	\N	\N	\N	\N	Streptomyces armeniacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3621	575	Streptomyces arenae	10411	\N	\N	\N	\N	Streptomyces arenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3622	575	Streptomyces ardus	10410	\N	\N	\N	\N	Streptomyces ardus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3623	575	Streptomyces aomiensis	10409	\N	\N	\N	\N	Streptomyces aomiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3624	575	Streptomyces anulatus	10408	\N	\N	\N	\N	Streptomyces anulatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3625	575	Streptomyces antimycoticus	10407	\N	\N	\N	\N	Streptomyces antimycoticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3626	575	Streptomyces antibioticus	10406	\N	\N	\N	\N	Streptomyces antibioticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3627	575	Streptomyces anthocyanicus	10405	\N	\N	\N	\N	Streptomyces anthocyanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3628	575	Streptomyces angustmyceticus	10404	\N	\N	\N	\N	Streptomyces angustmyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3629	575	Streptomyces anandii	10403	\N	\N	\N	\N	Streptomyces anandii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3630	575	Streptomyces ambofaciens	10402	\N	\N	\N	\N	Streptomyces ambofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3631	575	Streptomyces amakusaensis	10401	\N	\N	\N	\N	Streptomyces amakusaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3632	575	Streptomyces althioticus	10400	\N	\N	\N	\N	Streptomyces althioticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3633	575	Streptomyces alni	10399	\N	\N	\N	\N	Streptomyces alni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3634	575	Streptomyces almquistii	10398	\N	\N	\N	\N	Streptomyces almquistii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3635	575	Streptomyces aldersoniae	10397	\N	\N	\N	\N	Streptomyces aldersoniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3636	575	Streptomyces albus subsp. pathocidicus	10396	\N	\N	\N	\N	Streptomyces albus subsp. pathocidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3637	575	Streptomyces albus subsp. albus	10395	\N	\N	\N	\N	Streptomyces albus subsp. albus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3638	575	Streptomyces albulus	10394	\N	\N	\N	\N	Streptomyces albulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3639	575	Streptomyces albovinaceus	10393	\N	\N	\N	\N	Streptomyces albovinaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3640	575	Streptomyces albosporeus subsp. labilomyceticus	10392	\N	\N	\N	\N	Streptomyces albosporeus subsp. labilomyceticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3641	575	Streptomyces albosporeus subsp. albosporeus	10391	\N	\N	\N	\N	Streptomyces albosporeus subsp. albosporeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3642	575	Streptomyces albospinus	10390	\N	\N	\N	\N	Streptomyces albospinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3643	575	Streptomyces alboniger	10389	\N	\N	\N	\N	Streptomyces alboniger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3644	575	Streptomyces albolongus	10388	\N	\N	\N	\N	Streptomyces albolongus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3645	575	Streptomyces albogriseolus	10387	\N	\N	\N	\N	Streptomyces albogriseolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3646	575	Streptomyces alboflavus	10386	\N	\N	\N	\N	Streptomyces alboflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3647	575	Streptomyces albofaciens	10385	\N	\N	\N	\N	Streptomyces albofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3648	575	Streptomyces albiflaviniger	10384	\N	\N	\N	\N	Streptomyces albiflaviniger	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3649	575	Streptomyces albidoflavus	10383	\N	\N	\N	\N	Streptomyces albidoflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3650	575	Streptomyces albidochromogenes	10382	\N	\N	\N	\N	Streptomyces albidochromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3651	575	Streptomyces albiaxialis	10381	\N	\N	\N	\N	Streptomyces albiaxialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3652	575	Streptomyces albaduncus	10380	\N	\N	\N	\N	Streptomyces albaduncus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3653	575	Streptomyces alanosinicus	10379	\N	\N	\N	\N	Streptomyces alanosinicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3654	575	Streptomyces africanus	10378	\N	\N	\N	\N	Streptomyces africanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3655	575	Streptomyces afghaniensis	10377	\N	\N	\N	\N	Streptomyces afghaniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3656	575	Streptomyces aculeolatus	10376	\N	\N	\N	\N	Streptomyces aculeolatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3657	575	Streptomyces acidiscabies	10375	\N	\N	\N	\N	Streptomyces acidiscabies	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3658	575	Streptomyces achromogenes subsp. rubradiris	10374	\N	\N	\N	\N	Streptomyces achromogenes subsp. rubradiris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3659	575	Streptomyces achromogenes subsp. achromogenes	10373	\N	\N	\N	\N	Streptomyces achromogenes subsp. achromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3660	575	Streptomyces aburaviensis	10372	\N	\N	\N	\N	Streptomyces aburaviensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3661	575	Streptomyces abikoensis	10371	\N	\N	\N	\N	Streptomyces abikoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3662	576	Streptacidiphilus rugosus	10369	\N	\N	\N	\N	Streptacidiphilus rugosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3663	576	Streptacidiphilus oryzae	10368	\N	\N	\N	\N	Streptacidiphilus oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3664	576	Streptacidiphilus neutrinimicus	10367	\N	\N	\N	\N	Streptacidiphilus neutrinimicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3665	576	Streptacidiphilus melanogenes	10366	\N	\N	\N	\N	Streptacidiphilus melanogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3666	576	Streptacidiphilus jiangxiensis	10365	\N	\N	\N	\N	Streptacidiphilus jiangxiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3667	576	Streptacidiphilus carbonis	10364	\N	\N	\N	\N	Streptacidiphilus carbonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3668	576	Streptacidiphilus anmyonensis	10363	\N	\N	\N	\N	Streptacidiphilus anmyonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3669	576	Streptacidiphilus albus	10362	\N	\N	\N	\N	Streptacidiphilus albus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3670	577	Kitasatospora viridis	10360	\N	\N	\N	\N	Kitasatospora viridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3671	577	Kitasatospora terrestris	10359	\N	\N	\N	\N	Kitasatospora terrestris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3672	577	Kitasatospora setae	10358	\N	\N	\N	\N	Kitasatospora setae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3673	577	Kitasatospora sampliensis	10357	\N	\N	\N	\N	Kitasatospora sampliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3674	577	Kitasatospora saccharophila	10356	\N	\N	\N	\N	Kitasatospora saccharophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3675	577	Kitasatospora putterlickiae	10355	\N	\N	\N	\N	Kitasatospora putterlickiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3676	577	Kitasatospora phosalacinea	10354	\N	\N	\N	\N	Kitasatospora phosalacinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3677	577	Kitasatospora paranensis	10353	\N	\N	\N	\N	Kitasatospora paranensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3678	577	Kitasatospora paracochleata	10352	\N	\N	\N	\N	Kitasatospora paracochleata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3679	577	Kitasatospora nipponensis	10351	\N	\N	\N	\N	Kitasatospora nipponensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3680	577	Kitasatospora niigatensis	10350	\N	\N	\N	\N	Kitasatospora niigatensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3681	577	Kitasatospora mediocidica	10349	\N	\N	\N	\N	Kitasatospora mediocidica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3682	577	Kitasatospora kifunensis	10348	\N	\N	\N	\N	Kitasatospora kifunensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3683	577	Kitasatospora kazusensis	10347	\N	\N	\N	\N	Kitasatospora kazusensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3684	577	Kitasatospora griseola	10346	\N	\N	\N	\N	Kitasatospora griseola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3685	577	Kitasatospora gansuensis	10345	\N	\N	\N	\N	Kitasatospora gansuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3686	577	Kitasatospora cystarginea	10344	\N	\N	\N	\N	Kitasatospora cystarginea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3687	577	Kitasatospora cochleata	10343	\N	\N	\N	\N	Kitasatospora cochleata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3688	577	Kitasatospora cineracea	10342	\N	\N	\N	\N	Kitasatospora cineracea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3689	577	Kitasatospora cheerisanensis	10341	\N	\N	\N	\N	Kitasatospora cheerisanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3690	577	Kitasatospora azatica	10340	\N	\N	\N	\N	Kitasatospora azatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3691	577	Kitasatospora atroaurantiaca	10339	\N	\N	\N	\N	Kitasatospora atroaurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3692	577	Kitasatospora arboriphila	10338	\N	\N	\N	\N	Kitasatospora arboriphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3693	578	Streptococcus vestibularis	10335	\N	\N	\N	\N	Streptococcus vestibularis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3694	578	Streptococcus ursoris	10334	\N	\N	\N	\N	Streptococcus ursoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3695	578	Streptococcus urinalis	10333	\N	\N	\N	\N	Streptococcus urinalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3696	578	Streptococcus uberis	10332	\N	\N	\N	\N	Streptococcus uberis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3697	578	Streptococcus thoraltensis	10331	\N	\N	\N	\N	Streptococcus thoraltensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3698	578	Streptococcus suis	10330	\N	\N	\N	\N	Streptococcus suis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3699	578	Streptococcus sobrinus	10329	\N	\N	\N	\N	Streptococcus sobrinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3700	578	Streptococcus sinensis	10328	\N	\N	\N	\N	Streptococcus sinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3701	578	Streptococcus sanguinis	10327	\N	\N	\N	\N	Streptococcus sanguinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3702	578	Streptococcus salivarius subsp. thermophilus	10326	\N	\N	\N	\N	Streptococcus salivarius subsp. thermophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3703	578	Streptococcus salivarius subsp. salivarius	10325	\N	\N	\N	\N	Streptococcus salivarius subsp. salivarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3704	578	Streptococcus rupicaprae	10324	\N	\N	\N	\N	Streptococcus rupicaprae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3705	578	Streptococcus ratti	10323	\N	\N	\N	\N	Streptococcus ratti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3706	578	Streptococcus pseudoporcinus	10322	\N	\N	\N	\N	Streptococcus pseudoporcinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3707	578	Streptococcus pseudopneumoniae	10321	\N	\N	\N	\N	Streptococcus pseudopneumoniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3708	578	Streptococcus porcorum	10320	\N	\N	\N	\N	Streptococcus porcorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3709	578	Streptococcus porcinus	10319	\N	\N	\N	\N	Streptococcus porcinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3710	578	Streptococcus porci	10318	\N	\N	\N	\N	Streptococcus porci	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3711	578	Streptococcus pneumoniae	10317	\N	\N	\N	\N	Streptococcus pneumoniae<Streptococcus<Streptococcaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
3712	578	Streptococcus plurextorum	10316	\N	\N	\N	\N	Streptococcus plurextorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3713	578	Streptococcus phocae	10315	\N	\N	\N	\N	Streptococcus phocae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3714	578	Streptococcus parauberis	10314	\N	\N	\N	\N	Streptococcus parauberis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3715	578	Streptococcus parasanguinis	10313	\N	\N	\N	\N	Streptococcus parasanguinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3716	578	Streptococcus orisuis	10312	\N	\N	\N	\N	Streptococcus orisuis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3717	578	Streptococcus oralis	10311	\N	\N	\N	\N	Streptococcus oralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3718	578	Streptococcus oligofermentans	10310	\N	\N	\N	\N	Streptococcus oligofermentans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3719	578	Streptococcus mutans	10309	\N	\N	\N	\N	Streptococcus mutans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3720	578	Streptococcus mitis	10308	\N	\N	\N	\N	Streptococcus mitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3721	578	Streptococcus minor	10307	\N	\N	\N	\N	Streptococcus minor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3722	578	Streptococcus massiliensis	10306	\N	\N	\N	\N	Streptococcus massiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3723	578	Streptococcus marimammalium	10305	\N	\N	\N	\N	Streptococcus marimammalium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3724	578	Streptococcus macacae	10304	\N	\N	\N	\N	Streptococcus macacae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3725	578	Streptococcus lutetiensis	10303	\N	\N	\N	\N	Streptococcus lutetiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3726	578	Streptococcus lactarius	10302	\N	\N	\N	\N	Streptococcus lactarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3727	578	Streptococcus intermedius	10301	\N	\N	\N	\N	Streptococcus intermedius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3728	578	Streptococcus iniae	10300	\N	\N	\N	\N	Streptococcus iniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3729	578	Streptococcus infantis	10299	\N	\N	\N	\N	Streptococcus infantis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3730	578	Streptococcus infantarius subsp. infantarius	10298	\N	\N	\N	\N	Streptococcus infantarius subsp. infantarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3731	578	Streptococcus infantarius subsp. coli	10297	\N	\N	\N	\N	Streptococcus infantarius subsp. coli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3732	578	Streptococcus ictaluri	10296	\N	\N	\N	\N	Streptococcus ictaluri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3733	578	Streptococcus hyovaginalis	10295	\N	\N	\N	\N	Streptococcus hyovaginalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3734	578	Streptococcus henryi	10294	\N	\N	\N	\N	Streptococcus henryi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3735	578	Streptococcus halichoeri	10293	\N	\N	\N	\N	Streptococcus halichoeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3736	578	Streptococcus gordonii	10292	\N	\N	\N	\N	Streptococcus gordonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3737	578	Streptococcus gallolyticus subsp. pasteurianus	10291	\N	\N	\N	\N	Streptococcus gallolyticus subsp. pasteurianus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3738	578	Streptococcus gallolyticus subsp. macedonicus	10290	\N	\N	\N	\N	Streptococcus gallolyticus subsp. macedonicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3739	578	Streptococcus gallolyticus subsp. gallolyticus	10289	\N	\N	\N	\N	Streptococcus gallolyticus subsp. gallolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3740	578	Streptococcus gallinaceus	10288	\N	\N	\N	\N	Streptococcus gallinaceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3741	578	Streptococcus ferus	10287	\N	\N	\N	\N	Streptococcus ferus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3742	578	Streptococcus equi subsp. zooepidemicus	10286	\N	\N	\N	\N	Streptococcus equi subsp. zooepidemicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3743	578	Streptococcus equi subsp. ruminatorum	10285	\N	\N	\N	\N	Streptococcus equi subsp. ruminatorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3744	578	Streptococcus equi subsp. equi	10284	\N	\N	\N	\N	Streptococcus equi subsp. equi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3745	578	Streptococcus equinus	10283	\N	\N	\N	\N	Streptococcus equinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3746	578	Streptococcus dysgalactiae subsp. equisimilis	10282	\N	\N	\N	\N	Streptococcus dysgalactiae subsp. equisimilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3747	578	Streptococcus dysgalactiae subsp. dysgalactiae	10281	\N	\N	\N	\N	Streptococcus dysgalactiae subsp. dysgalactiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3748	578	Streptococcus downei	10280	\N	\N	\N	\N	Streptococcus downei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3749	578	Streptococcus didelphis	10279	\N	\N	\N	\N	Streptococcus didelphis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3750	578	Streptococcus devriesei	10278	\N	\N	\N	\N	Streptococcus devriesei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3751	578	Streptococcus dentirousetti	10277	\N	\N	\N	\N	Streptococcus dentirousetti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3752	578	Streptococcus dentapri	10276	\N	\N	\N	\N	Streptococcus dentapri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3753	578	Streptococcus cristatus	10275	\N	\N	\N	\N	Streptococcus cristatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3754	578	Streptococcus constellatus subsp. pharyngis	10274	\N	\N	\N	\N	Streptococcus constellatus subsp. pharyngis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3755	578	Streptococcus constellatus subsp. constellatus	10273	\N	\N	\N	\N	Streptococcus constellatus subsp. constellatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3756	578	Streptococcus castoreus	10272	\N	\N	\N	\N	Streptococcus castoreus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3757	578	Streptococcus canis	10271	\N	\N	\N	\N	Streptococcus canis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3758	578	Streptococcus caballi	10270	\N	\N	\N	\N	Streptococcus caballi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3759	578	Streptococcus australis	10269	\N	\N	\N	\N	Streptococcus australis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3760	578	Streptococcus anginosus	10268	\N	\N	\N	\N	Streptococcus anginosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3761	578	Streptococcus agalactiae	10267	\N	\N	\N	\N	Streptococcus agalactiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3762	579	Lactovum miscens	10265	\N	\N	\N	\N	Lactovum miscens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3763	580	Lactococcus raffinolactis	10263	\N	\N	\N	\N	Lactococcus raffinolactis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3764	580	Lactococcus plantarum	10262	\N	\N	\N	\N	Lactococcus plantarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3765	580	Lactococcus piscium	10261	\N	\N	\N	\N	Lactococcus piscium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3766	580	Lactococcus lactis subsp. tructae	10260	\N	\N	\N	\N	Lactococcus lactis subsp. tructae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3767	580	Lactococcus lactis subsp. lactis	10259	\N	\N	\N	\N	Lactococcus lactis subsp. lactis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3768	580	Lactococcus lactis subsp. hordniae	10258	\N	\N	\N	\N	Lactococcus lactis subsp. hordniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3769	580	Lactococcus lactis subsp. cremoris	10257	\N	\N	\N	\N	Lactococcus lactis subsp. cremoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3770	580	Lactococcus garvieae	10256	\N	\N	\N	\N	Lactococcus garvieae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3771	580	Lactococcus chungangensis	10255	\N	\N	\N	\N	Lactococcus chungangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3772	581	Iphinoe spelaeobios	10252	\N	\N	\N	\N	Iphinoe spelaeobios	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3773	582	Staphylococcus xylosus	10249	\N	\N	\N	\N	Staphylococcus xylosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3774	582	Staphylococcus warneri	10248	\N	\N	\N	\N	Staphylococcus warneri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3775	582	Staphylococcus vitulinus	10247	\N	\N	\N	\N	Staphylococcus vitulinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3776	582	Staphylococcus succinus subsp. succinus	10246	\N	\N	\N	\N	Staphylococcus succinus subsp. succinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3777	582	Staphylococcus succinus subsp. casei	10245	\N	\N	\N	\N	Staphylococcus succinus subsp. casei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3778	582	Staphylococcus stepanovicii	10244	\N	\N	\N	\N	Staphylococcus stepanovicii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3779	582	Staphylococcus simulans	10243	\N	\N	\N	\N	Staphylococcus simulans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3780	582	Staphylococcus simiae	10242	\N	\N	\N	\N	Staphylococcus simiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3781	582	Staphylococcus sciuri subsp. sciuri	10241	\N	\N	\N	\N	Staphylococcus sciuri subsp. sciuri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3782	582	Staphylococcus sciuri subsp. rodentium	10240	\N	\N	\N	\N	Staphylococcus sciuri subsp. rodentium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3783	582	Staphylococcus sciuri subsp. carnaticus	10239	\N	\N	\N	\N	Staphylococcus sciuri subsp. carnaticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3784	582	Staphylococcus schleiferi subsp. schleiferi	10238	\N	\N	\N	\N	Staphylococcus schleiferi subsp. schleiferi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3785	582	Staphylococcus schleiferi subsp. coagulans	10237	\N	\N	\N	\N	Staphylococcus schleiferi subsp. coagulans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3786	582	Staphylococcus saprophyticus subsp. saprophyticus	10236	\N	\N	\N	\N	Staphylococcus saprophyticus subsp. saprophyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3787	582	Staphylococcus saprophyticus subsp. bovis	10235	\N	\N	\N	\N	Staphylococcus saprophyticus subsp. bovis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3788	582	Staphylococcus saccharolyticus	10234	\N	\N	\N	\N	Staphylococcus saccharolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3789	582	Staphylococcus pseudintermedius	10233	\N	\N	\N	\N	Staphylococcus pseudintermedius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3790	582	Staphylococcus piscifermentans	10232	\N	\N	\N	\N	Staphylococcus piscifermentans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3791	582	Staphylococcus pettenkoferi	10231	\N	\N	\N	\N	Staphylococcus pettenkoferi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3792	582	Staphylococcus pasteuri	10230	\N	\N	\N	\N	Staphylococcus pasteuri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3793	582	Staphylococcus nepalensis	10229	\N	\N	\N	\N	Staphylococcus nepalensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3794	582	Staphylococcus muscae	10228	\N	\N	\N	\N	Staphylococcus muscae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3795	582	Staphylococcus microti	10227	\N	\N	\N	\N	Staphylococcus microti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3796	582	Staphylococcus massiliensis	10226	\N	\N	\N	\N	Staphylococcus massiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3797	582	Staphylococcus lutrae	10225	\N	\N	\N	\N	Staphylococcus lutrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3798	582	Staphylococcus lugdunensis	10224	\N	\N	\N	\N	Staphylococcus lugdunensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3799	582	Staphylococcus lentus	10223	\N	\N	\N	\N	Staphylococcus lentus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3800	582	Staphylococcus kloosii	10222	\N	\N	\N	\N	Staphylococcus kloosii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3801	582	Staphylococcus intermedius	10221	\N	\N	\N	\N	Staphylococcus intermedius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3802	582	Staphylococcus hyicus	10220	\N	\N	\N	\N	Staphylococcus hyicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3803	582	Staphylococcus hominis subsp. novobiosepticus	10219	\N	\N	\N	\N	Staphylococcus hominis subsp. novobiosepticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3804	582	Staphylococcus hominis subsp. hominis	10218	\N	\N	\N	\N	Staphylococcus hominis subsp. hominis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3805	582	Staphylococcus haemolyticus	10217	\N	\N	\N	\N	Staphylococcus haemolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3806	582	Staphylococcus gallinarum	10216	\N	\N	\N	\N	Staphylococcus gallinarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3807	582	Staphylococcus fleurettii	10215	\N	\N	\N	\N	Staphylococcus fleurettii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3808	582	Staphylococcus felis	10214	\N	\N	\N	\N	Staphylococcus felis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3809	582	Staphylococcus equorum subsp. linens	10213	\N	\N	\N	\N	Staphylococcus equorum subsp. linens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3810	582	Staphylococcus equorum subsp. equorum	10212	\N	\N	\N	\N	Staphylococcus equorum subsp. equorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3811	582	Staphylococcus epidermidis	10211	\N	\N	\N	\N	Staphylococcus epidermidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3812	582	Staphylococcus devriesei	10210	\N	\N	\N	\N	Staphylococcus devriesei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3813	582	Staphylococcus delphini	10209	\N	\N	\N	\N	Staphylococcus delphini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3814	582	Staphylococcus condimenti	10208	\N	\N	\N	\N	Staphylococcus condimenti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3815	582	Staphylococcus cohnii subsp. urealyticus	10207	\N	\N	\N	\N	Staphylococcus cohnii subsp. urealyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3816	582	Staphylococcus cohnii subsp. cohnii	10206	\N	\N	\N	\N	Staphylococcus cohnii subsp. cohnii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3817	582	Staphylococcus chromogenes	10205	\N	\N	\N	\N	Staphylococcus chromogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3818	582	Staphylococcus carnosus subsp. utilis	10204	\N	\N	\N	\N	Staphylococcus carnosus subsp. utilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3819	582	Staphylococcus carnosus subsp. carnosus	10203	\N	\N	\N	\N	Staphylococcus carnosus subsp. carnosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3820	582	Staphylococcus caprae	10202	\N	\N	\N	\N	Staphylococcus caprae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3821	582	Staphylococcus capitis subsp. urealyticus	10201	\N	\N	\N	\N	Staphylococcus capitis subsp. urealyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3822	582	Staphylococcus capitis subsp. capitis	10200	\N	\N	\N	\N	Staphylococcus capitis subsp. capitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3823	582	Staphylococcus auricularis	10199	\N	\N	\N	\N	Staphylococcus auricularis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3824	582	Staphylococcus aureus subsp. aureus	10198	\N	\N	\N	\N	Staphylococcus aureus subsp. aureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3825	582	Staphylococcus aureus subsp. anaerobius	10197	\N	\N	\N	\N	Staphylococcus aureus subsp. anaerobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3826	582	Staphylococcus arlettae	10196	\N	\N	\N	\N	Staphylococcus arlettae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3827	583	Salinicoccus siamensis	10194	\N	\N	\N	\N	Salinicoccus siamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3828	583	Salinicoccus sesuvii	10193	\N	\N	\N	\N	Salinicoccus sesuvii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3829	583	Salinicoccus salsiraiae	10192	\N	\N	\N	\N	Salinicoccus salsiraiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3830	583	Salinicoccus roseus	10191	\N	\N	\N	\N	Salinicoccus roseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3831	583	Salinicoccus qingdaonensis	10190	\N	\N	\N	\N	Salinicoccus qingdaonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3832	583	Salinicoccus luteus	10189	\N	\N	\N	\N	Salinicoccus luteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3833	583	Salinicoccus kunmingensis	10188	\N	\N	\N	\N	Salinicoccus kunmingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3834	583	Salinicoccus jeotgali	10187	\N	\N	\N	\N	Salinicoccus jeotgali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3835	583	Salinicoccus iranensis	10186	\N	\N	\N	\N	Salinicoccus iranensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3836	583	Salinicoccus hispanicus	10185	\N	\N	\N	\N	Salinicoccus hispanicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3837	583	Salinicoccus halodurans	10184	\N	\N	\N	\N	Salinicoccus halodurans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3838	583	Salinicoccus carnicancri	10183	\N	\N	\N	\N	Salinicoccus carnicancri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3839	583	Salinicoccus alkaliphilus	10182	\N	\N	\N	\N	Salinicoccus alkaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3840	583	Salinicoccus albus	10181	\N	\N	\N	\N	Salinicoccus albus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3841	584	Nosocomiicoccus ampullae	10179	\N	\N	\N	\N	Nosocomiicoccus ampullae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3842	585	Macrococcus lamae	10177	\N	\N	\N	\N	Macrococcus lamae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3843	585	Macrococcus hajekii	10176	\N	\N	\N	\N	Macrococcus hajekii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3844	585	Macrococcus equipercicus	10175	\N	\N	\N	\N	Macrococcus equipercicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3845	585	Macrococcus caseolyticus	10174	\N	\N	\N	\N	Macrococcus caseolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3846	585	Macrococcus carouselicus	10173	\N	\N	\N	\N	Macrococcus carouselicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3847	585	Macrococcus brunensis	10172	\N	\N	\N	\N	Macrococcus brunensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3848	585	Macrococcus bovicus	10171	\N	\N	\N	\N	Macrococcus bovicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3849	586	Jeotgalicoccus psychrophilus	10169	\N	\N	\N	\N	Jeotgalicoccus psychrophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3850	586	Jeotgalicoccus nanhaiensis	10168	\N	\N	\N	\N	Jeotgalicoccus nanhaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3851	586	Jeotgalicoccus marinus	10167	\N	\N	\N	\N	Jeotgalicoccus marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3852	586	Jeotgalicoccus huakuii	10166	\N	\N	\N	\N	Jeotgalicoccus huakuii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3853	586	Jeotgalicoccus halotolerans	10165	\N	\N	\N	\N	Jeotgalicoccus halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3854	586	Jeotgalicoccus halophilus	10164	\N	\N	\N	\N	Jeotgalicoccus halophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3855	587	Tuberibacillus calidus	10161	\N	\N	\N	\N	Tuberibacillus calidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3856	588	Sporolactobacillus vineae	10159	\N	\N	\N	\N	Sporolactobacillus vineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3857	588	Sporolactobacillus terrae	10158	\N	\N	\N	\N	Sporolactobacillus terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3858	588	Sporolactobacillus putidus	10157	\N	\N	\N	\N	Sporolactobacillus putidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3859	588	Sporolactobacillus nakayamae subsp. racemicus	10156	\N	\N	\N	\N	Sporolactobacillus nakayamae subsp. racemicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3860	588	Sporolactobacillus nakayamae subsp. nakayamae	10155	\N	\N	\N	\N	Sporolactobacillus nakayamae subsp. nakayamae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3861	588	Sporolactobacillus laevolacticus	10154	\N	\N	\N	\N	Sporolactobacillus laevolacticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3862	588	Sporolactobacillus kofuensis	10153	\N	\N	\N	\N	Sporolactobacillus kofuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3863	588	Sporolactobacillus inulinus	10152	\N	\N	\N	\N	Sporolactobacillus inulinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3864	589	Sinobaca qinghaiensis	10150	\N	\N	\N	\N	Sinobaca qinghaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3865	590	Pullulanibacillus naganoensis	10148	\N	\N	\N	\N	Pullulanibacillus naganoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3866	591	Sporichthya polymorpha	10145	\N	\N	\N	\N	Sporichthya polymorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3867	591	Sporichthya brevicatena	10144	\N	\N	\N	\N	Sporichthya brevicatena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3868	592	Spiroplasma velocicrescens	10141	\N	\N	\N	\N	Spiroplasma velocicrescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3869	592	Spiroplasma turonicum	10140	\N	\N	\N	\N	Spiroplasma turonicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3870	592	Spiroplasma taiwanense	10139	\N	\N	\N	\N	Spiroplasma taiwanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3871	592	Spiroplasma tabanidicola	10138	\N	\N	\N	\N	Spiroplasma tabanidicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3872	592	Spiroplasma syrphidicola	10137	\N	\N	\N	\N	Spiroplasma syrphidicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3873	592	Spiroplasma sabaudiense	10136	\N	\N	\N	\N	Spiroplasma sabaudiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3874	592	Spiroplasma poulsonii	10135	\N	\N	\N	\N	Spiroplasma poulsonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3875	592	Spiroplasma platyhelix	10134	\N	\N	\N	\N	Spiroplasma platyhelix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3876	592	Spiroplasma phoeniceum	10133	\N	\N	\N	\N	Spiroplasma phoeniceum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3877	592	Spiroplasma penaei	10132	\N	\N	\N	\N	Spiroplasma penaei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3878	592	Spiroplasma montanense	10131	\N	\N	\N	\N	Spiroplasma montanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3879	592	Spiroplasma monobiae	10130	\N	\N	\N	\N	Spiroplasma monobiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3880	592	Spiroplasma melliferum	10129	\N	\N	\N	\N	Spiroplasma melliferum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3881	592	Spiroplasma litorale	10128	\N	\N	\N	\N	Spiroplasma litorale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3882	592	Spiroplasma lineolae	10127	\N	\N	\N	\N	Spiroplasma lineolae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3883	592	Spiroplasma leptinotarsae	10126	\N	\N	\N	\N	Spiroplasma leptinotarsae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3884	592	Spiroplasma lampyridicola	10125	\N	\N	\N	\N	Spiroplasma lampyridicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3885	592	Spiroplasma kunkelii	10124	\N	\N	\N	\N	Spiroplasma kunkelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3886	592	Spiroplasma ixodetis	10123	\N	\N	\N	\N	Spiroplasma ixodetis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3887	592	Spiroplasma insolitum	10122	\N	\N	\N	\N	Spiroplasma insolitum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3888	592	Spiroplasma helicoides	10121	\N	\N	\N	\N	Spiroplasma helicoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3889	592	Spiroplasma gladiatoris	10120	\N	\N	\N	\N	Spiroplasma gladiatoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3890	592	Spiroplasma eriocheiris	10119	\N	\N	\N	\N	Spiroplasma eriocheiris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3891	592	Spiroplasma diminutum	10118	\N	\N	\N	\N	Spiroplasma diminutum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3892	592	Spiroplasma diabroticae	10117	\N	\N	\N	\N	Spiroplasma diabroticae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3893	592	Spiroplasma culicicola	10116	\N	\N	\N	\N	Spiroplasma culicicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3894	592	Spiroplasma corruscae	10115	\N	\N	\N	\N	Spiroplasma corruscae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3895	592	Spiroplasma clarkii	10114	\N	\N	\N	\N	Spiroplasma clarkii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3896	592	Spiroplasma citri	10113	\N	\N	\N	\N	Spiroplasma citri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3897	592	Spiroplasma chrysopicola	10112	\N	\N	\N	\N	Spiroplasma chrysopicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3898	592	Spiroplasma chinense	10111	\N	\N	\N	\N	Spiroplasma chinense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3899	592	Spiroplasma cantharicola	10110	\N	\N	\N	\N	Spiroplasma cantharicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3900	592	Spiroplasma apis	10109	\N	\N	\N	\N	Spiroplasma apis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3901	592	Spiroplasma alleghenense	10108	\N	\N	\N	\N	Spiroplasma alleghenense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3902	593	Exilispira thermophila	10105	\N	\N	\N	\N	Exilispira thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3903	594	Treponema succinifaciens	10102	\N	\N	\N	\N	Treponema succinifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3904	594	Treponema socranskii subsp. socranskii	10101	\N	\N	\N	\N	Treponema socranskii subsp. socranskii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3905	594	Treponema socranskii subsp. paredis	10100	\N	\N	\N	\N	Treponema socranskii subsp. paredis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3906	594	Treponema socranskii subsp. buccale	10099	\N	\N	\N	\N	Treponema socranskii subsp. buccale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3907	594	Treponema saccharophilum	10098	\N	\N	\N	\N	Treponema saccharophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3908	594	Treponema putidum	10097	\N	\N	\N	\N	Treponema putidum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3909	594	Treponema porcinum	10096	\N	\N	\N	\N	Treponema porcinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3910	594	Treponema pedis	10095	\N	\N	\N	\N	Treponema pedis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3911	594	Treponema pectinovorum	10094	\N	\N	\N	\N	Treponema pectinovorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3912	594	Treponema parvum	10093	\N	\N	\N	\N	Treponema parvum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3913	594	Treponema maltophilum	10092	\N	\N	\N	\N	Treponema maltophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3914	594	Treponema lecithinolyticum	10091	\N	\N	\N	\N	Treponema lecithinolyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3915	594	Treponema isoptericolens	10090	\N	\N	\N	\N	Treponema isoptericolens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3916	594	Treponema denticola	10089	\N	\N	\N	\N	Treponema denticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3917	594	Treponema bryantii	10088	\N	\N	\N	\N	Treponema bryantii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3918	594	Treponema brennaborense	10087	\N	\N	\N	\N	Treponema brennaborense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3919	594	Treponema berlinense	10086	\N	\N	\N	\N	Treponema berlinense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3920	594	Treponema azotonutricium	10085	\N	\N	\N	\N	Treponema azotonutricium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3921	594	Treponema amylovorum	10084	\N	\N	\N	\N	Treponema amylovorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3922	595	Spirochaeta zuelzerae	10082	\N	\N	\N	\N	Spirochaeta zuelzerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3923	595	Spirochaeta thermophila	10081	\N	\N	\N	\N	Spirochaeta thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3924	595	Spirochaeta stenostrepta	10080	\N	\N	\N	\N	Spirochaeta stenostrepta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3925	595	Spirochaeta smaragdinae	10079	\N	\N	\N	\N	Spirochaeta smaragdinae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3926	595	Spirochaeta perfilievii	10078	\N	\N	\N	\N	Spirochaeta perfilievii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3927	595	Spirochaeta litoralis	10077	\N	\N	\N	\N	Spirochaeta litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3928	595	Spirochaeta isovalerica	10076	\N	\N	\N	\N	Spirochaeta isovalerica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3929	595	Spirochaeta halophila	10075	\N	\N	\N	\N	Spirochaeta halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3930	595	Spirochaeta dissipatitropha	10074	\N	\N	\N	\N	Spirochaeta dissipatitropha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3931	595	Spirochaeta coccoides	10073	\N	\N	\N	\N	Spirochaeta coccoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3932	595	Spirochaeta cellobiosiphila	10072	\N	\N	\N	\N	Spirochaeta cellobiosiphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3933	595	Spirochaeta caldaria	10071	\N	\N	\N	\N	Spirochaeta caldaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3934	595	Spirochaeta bajacaliforniensis	10070	\N	\N	\N	\N	Spirochaeta bajacaliforniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3935	595	Spirochaeta aurantia subsp. aurantia	10069	\N	\N	\N	\N	Spirochaeta aurantia subsp. aurantia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3936	595	Spirochaeta asiatica	10068	\N	\N	\N	\N	Spirochaeta asiatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3937	595	Spirochaeta americana	10067	\N	\N	\N	\N	Spirochaeta americana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3938	595	Spirochaeta alkalica	10066	\N	\N	\N	\N	Spirochaeta alkalica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3939	595	Spirochaeta africana	10065	\N	\N	\N	\N	Spirochaeta africana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3940	596	Sphaerochaeta pleomorpha	10063	\N	\N	\N	\N	Sphaerochaeta pleomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3941	596	Sphaerochaeta globosa	10062	\N	\N	\N	\N	Sphaerochaeta globosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3942	597	Borrelia valaisiana	10060	\N	\N	\N	\N	Borrelia valaisiana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3943	597	Borrelia sinica	10059	\N	\N	\N	\N	Borrelia sinica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3944	597	Borrelia lusitaniae	10058	\N	\N	\N	\N	Borrelia lusitaniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3945	597	Borrelia japonica	10057	\N	\N	\N	\N	Borrelia japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3946	597	Borrelia coriaceae	10056	\N	\N	\N	\N	Borrelia coriaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3947	597	Borrelia carolinensis	10055	\N	\N	\N	\N	Borrelia carolinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3948	597	Borrelia burgdorferi	10054	\N	\N	\N	\N	Borrelia burgdorferi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3949	597	Borrelia americana	10053	\N	\N	\N	\N	Borrelia americana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3950	597	Borrelia afzelii	10052	\N	\N	\N	\N	Borrelia afzelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3951	598	Spirillum winogradskyi	10049	\N	\N	\N	\N	Spirillum winogradskyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3952	598	Spirillum volutans	10048	\N	\N	\N	\N	Spirillum volutans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3953	599	Zymomonas mobilis subsp. pomaceae	10045	\N	\N	\N	\N	Zymomonas mobilis subsp. pomaceae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3954	599	Zymomonas mobilis subsp. mobilis	10044	\N	\N	\N	\N	Zymomonas mobilis subsp. mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3955	600	Stakelama pacifica	10042	\N	\N	\N	\N	Stakelama pacifica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3956	601	Sphingosinicella xenopeptidilytica	10040	\N	\N	\N	\N	Sphingosinicella xenopeptidilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3957	601	Sphingosinicella soli	10039	\N	\N	\N	\N	Sphingosinicella soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3958	601	Sphingosinicella microcystinivorans	10038	\N	\N	\N	\N	Sphingosinicella microcystinivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3959	602	Sphingopyxis witflariensis	10036	\N	\N	\N	\N	Sphingopyxis witflariensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3960	602	Sphingopyxis ummariensis	10035	\N	\N	\N	\N	Sphingopyxis ummariensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3961	602	Sphingopyxis taejonensis	10034	\N	\N	\N	\N	Sphingopyxis taejonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3962	602	Sphingopyxis soli	10033	\N	\N	\N	\N	Sphingopyxis soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3963	602	Sphingopyxis panaciterrulae	10032	\N	\N	\N	\N	Sphingopyxis panaciterrulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3964	602	Sphingopyxis panaciterrae	10031	\N	\N	\N	\N	Sphingopyxis panaciterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3965	602	Sphingopyxis granuli	10030	\N	\N	\N	\N	Sphingopyxis granuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3966	602	Sphingopyxis ginsengisoli	10029	\N	\N	\N	\N	Sphingopyxis ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3967	602	Sphingopyxis flavimaris	10028	\N	\N	\N	\N	Sphingopyxis flavimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3968	602	Sphingopyxis chilensis	10027	\N	\N	\N	\N	Sphingopyxis chilensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3969	602	Sphingopyxis bauzanensis	10026	\N	\N	\N	\N	Sphingopyxis bauzanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3970	602	Sphingopyxis baekryungensis	10025	\N	\N	\N	\N	Sphingopyxis baekryungensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3971	602	Sphingopyxis alaskensis	10024	\N	\N	\N	\N	Sphingopyxis alaskensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3972	603	Sphingomonas yunnanensis	10022	\N	\N	\N	\N	Sphingomonas yunnanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3973	603	Sphingomonas yanoikuyae	10021	\N	\N	\N	\N	Sphingomonas yanoikuyae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3974	603	Sphingomonas yabuuchiae	10020	\N	\N	\N	\N	Sphingomonas yabuuchiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3975	603	Sphingomonas xinjiangensis	10019	\N	\N	\N	\N	Sphingomonas xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3976	603	Sphingomonas wittichii	10018	\N	\N	\N	\N	Sphingomonas wittichii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3977	603	Sphingomonas ursincola	10017	\N	\N	\N	\N	Sphingomonas ursincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3978	603	Sphingomonas trueperi	10016	\N	\N	\N	\N	Sphingomonas trueperi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3979	603	Sphingomonas terrae	10015	\N	\N	\N	\N	Sphingomonas terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3980	603	Sphingomonas subterranea	10014	\N	\N	\N	\N	Sphingomonas subterranea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3981	603	Sphingomonas suberifaciens	10013	\N	\N	\N	\N	Sphingomonas suberifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3982	603	Sphingomonas stygia	10012	\N	\N	\N	\N	Sphingomonas stygia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3983	603	Sphingomonas soli	10011	\N	\N	\N	\N	Sphingomonas soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3984	603	Sphingomonas sanxanigenens	10010	\N	\N	\N	\N	Sphingomonas sanxanigenens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3985	603	Sphingomonas rubra	10009	\N	\N	\N	\N	Sphingomonas rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3986	603	Sphingomonas roseiflava	10008	\N	\N	\N	\N	Sphingomonas roseiflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3987	603	Sphingomonas pseudosanguinis	10007	\N	\N	\N	\N	Sphingomonas pseudosanguinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3988	603	Sphingomonas pruni	10006	\N	\N	\N	\N	Sphingomonas pruni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3989	603	Sphingomonas polyaromaticivorans	10005	\N	\N	\N	\N	Sphingomonas polyaromaticivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3990	603	Sphingomonas pituitosa	10004	\N	\N	\N	\N	Sphingomonas pituitosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3991	603	Sphingomonas phyllosphaerae	10003	\N	\N	\N	\N	Sphingomonas phyllosphaerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3992	603	Sphingomonas paucimobilis	10002	\N	\N	\N	\N	Sphingomonas paucimobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3993	603	Sphingomonas parapaucimobilis	10001	\N	\N	\N	\N	Sphingomonas parapaucimobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3994	603	Sphingomonas panni	10000	\N	\N	\N	\N	Sphingomonas panni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3995	603	Sphingomonas oryziterrae	9999	\N	\N	\N	\N	Sphingomonas oryziterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3996	603	Sphingomonas mucosissima	9998	\N	\N	\N	\N	Sphingomonas mucosissima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3997	603	Sphingomonas molluscorum	9997	\N	\N	\N	\N	Sphingomonas molluscorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3998	603	Sphingomonas melonis	9996	\N	\N	\N	\N	Sphingomonas melonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
3999	603	Sphingomonas mali	9995	\N	\N	\N	\N	Sphingomonas mali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4000	603	Sphingomonas macrogoltabidus	9994	\N	\N	\N	\N	Sphingomonas macrogoltabidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4001	603	Sphingomonas leidyi	9993	\N	\N	\N	\N	Sphingomonas leidyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4002	603	Sphingomonas koreensis	9992	\N	\N	\N	\N	Sphingomonas koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4003	603	Sphingomonas kaistensis	9991	\N	\N	\N	\N	Sphingomonas kaistensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4004	603	Sphingomonas jinjuensis	9990	\N	\N	\N	\N	Sphingomonas jinjuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4005	603	Sphingomonas jejuensis	9989	\N	\N	\N	\N	Sphingomonas jejuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4006	603	Sphingomonas jaspsi	9988	\N	\N	\N	\N	Sphingomonas jaspsi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4007	603	Sphingomonas japonica	9987	\N	\N	\N	\N	Sphingomonas japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4008	603	Sphingomonas insulae	9986	\N	\N	\N	\N	Sphingomonas insulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4009	603	Sphingomonas histidinilytica	9985	\N	\N	\N	\N	Sphingomonas histidinilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4010	603	Sphingomonas herbicidovorans	9984	\N	\N	\N	\N	Sphingomonas herbicidovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4011	603	Sphingomonas hankookensis	9983	\N	\N	\N	\N	Sphingomonas hankookensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4012	603	Sphingomonas haloaromaticamans	9982	\N	\N	\N	\N	Sphingomonas haloaromaticamans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4013	603	Sphingomonas glacialis	9981	\N	\N	\N	\N	Sphingomonas glacialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4014	603	Sphingomonas ginsenosidimutans	9980	\N	\N	\N	\N	Sphingomonas ginsenosidimutans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4015	603	Sphingomonas formosensis	9979	\N	\N	\N	\N	Sphingomonas formosensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4016	603	Sphingomonas fennica	9978	\N	\N	\N	\N	Sphingomonas fennica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4017	603	Sphingomonas faeni	9977	\N	\N	\N	\N	Sphingomonas faeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4018	603	Sphingomonas endophytica	9976	\N	\N	\N	\N	Sphingomonas endophytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4019	603	Sphingomonas echinoides	9975	\N	\N	\N	\N	Sphingomonas echinoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4020	603	Sphingomonas dokdonensis	9974	\N	\N	\N	\N	Sphingomonas dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4021	603	Sphingomonas desiccabilis	9973	\N	\N	\N	\N	Sphingomonas desiccabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4022	603	Sphingomonas chlorophenolica	9972	\N	\N	\N	\N	Sphingomonas chlorophenolica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4023	603	Sphingomonas changbaiensis	9971	\N	\N	\N	\N	Sphingomonas changbaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4024	603	Sphingomonas capsulata	9970	\N	\N	\N	\N	Sphingomonas capsulata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4025	603	Sphingomonas azotifigens	9969	\N	\N	\N	\N	Sphingomonas azotifigens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4026	603	Sphingomonas aurantiaca	9968	\N	\N	\N	\N	Sphingomonas aurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4027	603	Sphingomonas astaxanthinifaciens	9967	\N	\N	\N	\N	Sphingomonas astaxanthinifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4028	603	Sphingomonas asaccharolytica	9966	\N	\N	\N	\N	Sphingomonas asaccharolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4029	603	Sphingomonas aromaticivorans	9965	\N	\N	\N	\N	Sphingomonas aromaticivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4030	603	Sphingomonas aquatilis	9964	\N	\N	\N	\N	Sphingomonas aquatilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4031	603	Sphingomonas alpina	9963	\N	\N	\N	\N	Sphingomonas alpina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4032	603	Sphingomonas aestuarii	9962	\N	\N	\N	\N	Sphingomonas aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4033	603	Sphingomonas aerolata	9961	\N	\N	\N	\N	Sphingomonas aerolata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4034	603	Sphingomonas adhaesiva	9960	\N	\N	\N	\N	Sphingomonas adhaesiva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4035	603	Sphingomonas abaci	9959	\N	\N	\N	\N	Sphingomonas abaci	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4036	604	Sphingomicrobium lutaoense	9957	\N	\N	\N	\N	Sphingomicrobium lutaoense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4037	605	Sphingobium xenophagum	9955	\N	\N	\N	\N	Sphingobium xenophagum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4038	605	Sphingobium wenxiniae	9954	\N	\N	\N	\N	Sphingobium wenxiniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4039	605	Sphingobium vulgare	9953	\N	\N	\N	\N	Sphingobium vulgare	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4040	605	Sphingobium vermicomposti	9952	\N	\N	\N	\N	Sphingobium vermicomposti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4041	605	Sphingobium ummariense	9951	\N	\N	\N	\N	Sphingobium ummariense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4042	605	Sphingobium rhizovicinum	9950	\N	\N	\N	\N	Sphingobium rhizovicinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4043	605	Sphingobium quisquiliarum	9949	\N	\N	\N	\N	Sphingobium quisquiliarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4044	605	Sphingobium qiguonii	9948	\N	\N	\N	\N	Sphingobium qiguonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4045	605	Sphingobium olei	9947	\N	\N	\N	\N	Sphingobium olei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4046	605	Sphingobium lucknowense	9946	\N	\N	\N	\N	Sphingobium lucknowense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4047	605	Sphingobium lactosutens	9945	\N	\N	\N	\N	Sphingobium lactosutens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4048	605	Sphingobium jiangsuense	9944	\N	\N	\N	\N	Sphingobium jiangsuense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4049	605	Sphingobium japonicum	9943	\N	\N	\N	\N	Sphingobium japonicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4050	605	Sphingobium indicum	9942	\N	\N	\N	\N	Sphingobium indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4051	605	Sphingobium fuliginis	9941	\N	\N	\N	\N	Sphingobium fuliginis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4052	605	Sphingobium francense	9940	\N	\N	\N	\N	Sphingobium francense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4053	605	Sphingobium faniae	9939	\N	\N	\N	\N	Sphingobium faniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4054	605	Sphingobium cloacae	9938	\N	\N	\N	\N	Sphingobium cloacae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4055	605	Sphingobium chungbukense	9937	\N	\N	\N	\N	Sphingobium chungbukense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4056	605	Sphingobium chinhatense	9936	\N	\N	\N	\N	Sphingobium chinhatense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4057	605	Sphingobium aromaticiconvertens	9935	\N	\N	\N	\N	Sphingobium aromaticiconvertens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4058	605	Sphingobium amiense	9934	\N	\N	\N	\N	Sphingobium amiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4059	605	Sphingobium abikonense	9933	\N	\N	\N	\N	Sphingobium abikonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4060	606	Sandarakinorhabdus limnophila	9931	\N	\N	\N	\N	Sandarakinorhabdus limnophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4061	607	Sandaracinobacter sibiricus	9929	\N	\N	\N	\N	Sandaracinobacter sibiricus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4062	608	Novosphingobium tardaugens	9927	\N	\N	\N	\N	Novosphingobium tardaugens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4063	608	Novosphingobium taihuense	9926	\N	\N	\N	\N	Novosphingobium taihuense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4064	608	Novosphingobium soli	9925	\N	\N	\N	\N	Novosphingobium soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4065	608	Novosphingobium sediminicola	9924	\N	\N	\N	\N	Novosphingobium sediminicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4066	608	Novosphingobium resinovorum	9923	\N	\N	\N	\N	Novosphingobium resinovorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4067	608	Novosphingobium pentaromativorans	9922	\N	\N	\N	\N	Novosphingobium pentaromativorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4068	608	Novosphingobium panipatense	9921	\N	\N	\N	\N	Novosphingobium panipatense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4069	608	Novosphingobium nitrogenifigens	9920	\N	\N	\N	\N	Novosphingobium nitrogenifigens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4070	608	Novosphingobium naphthalenivorans	9919	\N	\N	\N	\N	Novosphingobium naphthalenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4071	608	Novosphingobium mathurense	9918	\N	\N	\N	\N	Novosphingobium mathurense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4072	608	Novosphingobium lentum	9917	\N	\N	\N	\N	Novosphingobium lentum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4073	608	Novosphingobium indicum	9916	\N	\N	\N	\N	Novosphingobium indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4074	608	Novosphingobium hassiacum	9915	\N	\N	\N	\N	Novosphingobium hassiacum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4075	608	Novosphingobium acidiphilum	9914	\N	\N	\N	\N	Novosphingobium acidiphilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4076	609	Blastomonas natatoria	9912	\N	\N	\N	\N	Blastomonas natatoria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4077	610	Fodinibius salinus	9909	\N	\N	\N	\N	Fodinibius salinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4078	611	Sphingobacterium wenxiniae	9906	\N	\N	\N	\N	Sphingobacterium wenxiniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4079	611	Sphingobacterium thalpophilum	9905	\N	\N	\N	\N	Sphingobacterium thalpophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4080	611	Sphingobacterium siyangense	9904	\N	\N	\N	\N	Sphingobacterium siyangense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4081	611	Sphingobacterium shayense	9903	\N	\N	\N	\N	Sphingobacterium shayense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4082	611	Sphingobacterium multivorum	9902	\N	\N	\N	\N	Sphingobacterium multivorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4083	611	Sphingobacterium lactis	9901	\N	\N	\N	\N	Sphingobacterium lactis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4084	611	Sphingobacterium kitahiroshimense	9900	\N	\N	\N	\N	Sphingobacterium kitahiroshimense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4085	611	Sphingobacterium faecium	9899	\N	\N	\N	\N	Sphingobacterium faecium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4086	611	Sphingobacterium daejeonense	9898	\N	\N	\N	\N	Sphingobacterium daejeonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4087	611	Sphingobacterium canadense	9897	\N	\N	\N	\N	Sphingobacterium canadense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4088	611	Sphingobacterium bambusae	9896	\N	\N	\N	\N	Sphingobacterium bambusae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4089	611	Sphingobacterium antarcticum	9895	\N	\N	\N	\N	Sphingobacterium antarcticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4090	611	Sphingobacterium alimentarium	9894	\N	\N	\N	\N	Sphingobacterium alimentarium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4091	612	Solitalea koreensis	9892	\N	\N	\N	\N	Solitalea koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4092	612	Solitalea canadensis	9891	\N	\N	\N	\N	Solitalea canadensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4093	613	Pseudosphingobacterium domesticum	9889	\N	\N	\N	\N	Pseudosphingobacterium domesticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4094	614	Pedobacter westerhofensis	9887	\N	\N	\N	\N	Pedobacter westerhofensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4095	614	Pedobacter terricola	9886	\N	\N	\N	\N	Pedobacter terricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4096	614	Pedobacter terrae	9885	\N	\N	\N	\N	Pedobacter terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4097	614	Pedobacter steynii	9884	\N	\N	\N	\N	Pedobacter steynii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4098	614	Pedobacter soli	9883	\N	\N	\N	\N	Pedobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4099	614	Pedobacter sandarakinus	9882	\N	\N	\N	\N	Pedobacter sandarakinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4100	614	Pedobacter saltans	9881	\N	\N	\N	\N	Pedobacter saltans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4101	614	Pedobacter rhizosphaerae	9880	\N	\N	\N	\N	Pedobacter rhizosphaerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4102	614	Pedobacter piscium	9879	\N	\N	\N	\N	Pedobacter piscium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4103	614	Pedobacter panaciterrae	9878	\N	\N	\N	\N	Pedobacter panaciterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4104	614	Pedobacter oryzae	9877	\N	\N	\N	\N	Pedobacter oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4105	614	Pedobacter nyackensis	9876	\N	\N	\N	\N	Pedobacter nyackensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4106	614	Pedobacter metabolipauper	9875	\N	\N	\N	\N	Pedobacter metabolipauper	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4107	614	Pedobacter lentus	9874	\N	\N	\N	\N	Pedobacter lentus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4108	614	Pedobacter insulae	9873	\N	\N	\N	\N	Pedobacter insulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4109	614	Pedobacter himalayensis	9872	\N	\N	\N	\N	Pedobacter himalayensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4110	614	Pedobacter heparinus	9871	\N	\N	\N	\N	Pedobacter heparinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4111	614	Pedobacter hartonius	9870	\N	\N	\N	\N	Pedobacter hartonius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4112	614	Pedobacter ginsengisoli	9869	\N	\N	\N	\N	Pedobacter ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4113	614	Pedobacter duraquae	9868	\N	\N	\N	\N	Pedobacter duraquae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4114	614	Pedobacter daechungensis	9867	\N	\N	\N	\N	Pedobacter daechungensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4115	614	Pedobacter cryoconitis	9866	\N	\N	\N	\N	Pedobacter cryoconitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4116	614	Pedobacter composti	9865	\N	\N	\N	\N	Pedobacter composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4117	614	Pedobacter boryungensis	9864	\N	\N	\N	\N	Pedobacter boryungensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4118	614	Pedobacter borealis	9863	\N	\N	\N	\N	Pedobacter borealis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4119	614	Pedobacter bauzanensis	9862	\N	\N	\N	\N	Pedobacter bauzanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4120	614	Pedobacter arcticus	9861	\N	\N	\N	\N	Pedobacter arcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4121	614	Pedobacter aquatilis	9860	\N	\N	\N	\N	Pedobacter aquatilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4122	614	Pedobacter alluvionis	9859	\N	\N	\N	\N	Pedobacter alluvionis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4123	614	Pedobacter agri	9858	\N	\N	\N	\N	Pedobacter agri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4124	614	Pedobacter africanus	9857	\N	\N	\N	\N	Pedobacter africanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4125	615	Parapedobacter soli	9855	\N	\N	\N	\N	Parapedobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4126	615	Parapedobacter luteus	9854	\N	\N	\N	\N	Parapedobacter luteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4127	615	Parapedobacter koreensis	9853	\N	\N	\N	\N	Parapedobacter koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4128	616	Olivibacter terrae	9851	\N	\N	\N	\N	Olivibacter terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4129	616	Olivibacter soli	9850	\N	\N	\N	\N	Olivibacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4130	616	Olivibacter sitiensis	9849	\N	\N	\N	\N	Olivibacter sitiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4131	616	Olivibacter oleidegradans	9848	\N	\N	\N	\N	Olivibacter oleidegradans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4132	616	Olivibacter ginsengisoli	9847	\N	\N	\N	\N	Olivibacter ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4133	617	Nubsella zeaxanthinifaciens	9845	\N	\N	\N	\N	Nubsella zeaxanthinifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4134	618	Mucilaginibacter ximonensis	9843	\N	\N	\N	\N	Mucilaginibacter ximonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4135	618	Mucilaginibacter rigui	9842	\N	\N	\N	\N	Mucilaginibacter rigui	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4136	618	Mucilaginibacter oryzae	9841	\N	\N	\N	\N	Mucilaginibacter oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4137	618	Mucilaginibacter myungsuensis	9840	\N	\N	\N	\N	Mucilaginibacter myungsuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4138	618	Mucilaginibacter kameinonensis	9839	\N	\N	\N	\N	Mucilaginibacter kameinonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4139	618	Mucilaginibacter gracilis	9838	\N	\N	\N	\N	Mucilaginibacter gracilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4140	618	Mucilaginibacter gossypiicola	9837	\N	\N	\N	\N	Mucilaginibacter gossypiicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4141	618	Mucilaginibacter daejeonensis	9836	\N	\N	\N	\N	Mucilaginibacter daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4142	618	Mucilaginibacter composti	9835	\N	\N	\N	\N	Mucilaginibacter composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4143	619	Sphaerobacter thermophilus	9832	\N	\N	\N	\N	Sphaerobacter thermophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4144	620	Solirubrobacter soli	9829	\N	\N	\N	\N	Solirubrobacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4145	620	Solirubrobacter ginsenosidimutans	9828	\N	\N	\N	\N	Solirubrobacter ginsenosidimutans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4146	621	Sneathiella glossodoripedis	9825	\N	\N	\N	\N	Sneathiella glossodoripedis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4147	621	Sneathiella chinensis	9824	\N	\N	\N	\N	Sneathiella chinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4148	622	Alkanibacter difficilis	9821	\N	\N	\N	\N	Alkanibacter difficilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4149	623	Simkania negevensis	9818	\N	\N	\N	\N	Simkania negevensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4150	624	Shewanella xiamenensis	9815	\N	\N	\N	\N	Shewanella xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4151	624	Shewanella woodyi	9814	\N	\N	\N	\N	Shewanella woodyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4152	624	Shewanella waksmanii	9813	\N	\N	\N	\N	Shewanella waksmanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4153	624	Shewanella violacea	9812	\N	\N	\N	\N	Shewanella violacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4154	624	Shewanella vesiculosa	9811	\N	\N	\N	\N	Shewanella vesiculosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4155	624	Shewanella upenei	9810	\N	\N	\N	\N	Shewanella upenei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4156	624	Shewanella surugensis	9809	\N	\N	\N	\N	Shewanella surugensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4157	624	Shewanella spongiae	9808	\N	\N	\N	\N	Shewanella spongiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4158	624	Shewanella sediminis	9807	\N	\N	\N	\N	Shewanella sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4159	624	Shewanella schlegeliana	9806	\N	\N	\N	\N	Shewanella schlegeliana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4160	624	Shewanella sairae	9805	\N	\N	\N	\N	Shewanella sairae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4161	624	Shewanella putrefaciens	9804	\N	\N	\N	\N	Shewanella putrefaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4162	624	Shewanella psychrophila	9803	\N	\N	\N	\N	Shewanella psychrophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4163	624	Shewanella profunda	9802	\N	\N	\N	\N	Shewanella profunda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4164	624	Shewanella pneumatophori	9801	\N	\N	\N	\N	Shewanella pneumatophori	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4165	624	Shewanella piezotolerans	9800	\N	\N	\N	\N	Shewanella piezotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4166	624	Shewanella pealeana	9799	\N	\N	\N	\N	Shewanella pealeana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4167	624	Shewanella pacifica	9798	\N	\N	\N	\N	Shewanella pacifica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4168	624	Shewanella oneidensis	9797	\N	\N	\N	\N	Shewanella oneidensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4169	624	Shewanella olleyana	9796	\N	\N	\N	\N	Shewanella olleyana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4170	624	Shewanella morhuae	9795	\N	\N	\N	\N	Shewanella morhuae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4171	624	Shewanella marisflavi	9794	\N	\N	\N	\N	Shewanella marisflavi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4172	624	Shewanella marinintestina	9793	\N	\N	\N	\N	Shewanella marinintestina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4173	624	Shewanella marina	9792	\N	\N	\N	\N	Shewanella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4174	624	Shewanella loihica	9791	\N	\N	\N	\N	Shewanella loihica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4175	624	Shewanella livingstonensis	9790	\N	\N	\N	\N	Shewanella livingstonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4176	624	Shewanella kaireitica	9789	\N	\N	\N	\N	Shewanella kaireitica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4177	624	Shewanella japonica	9788	\N	\N	\N	\N	Shewanella japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4178	624	Shewanella irciniae	9787	\N	\N	\N	\N	Shewanella irciniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4179	624	Shewanella indica	9786	\N	\N	\N	\N	Shewanella indica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4180	624	Shewanella hanedai	9785	\N	\N	\N	\N	Shewanella hanedai	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4181	624	Shewanella haliotis	9784	\N	\N	\N	\N	Shewanella haliotis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4182	624	Shewanella hafniensis	9783	\N	\N	\N	\N	Shewanella hafniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4183	624	Shewanella glacialipiscicola	9782	\N	\N	\N	\N	Shewanella glacialipiscicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4184	624	Shewanella gelidimarina	9781	\N	\N	\N	\N	Shewanella gelidimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4185	624	Shewanella gaetbuli	9780	\N	\N	\N	\N	Shewanella gaetbuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4186	624	Shewanella frigidimarina	9779	\N	\N	\N	\N	Shewanella frigidimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4187	624	Shewanella fodinae	9778	\N	\N	\N	\N	Shewanella fodinae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4188	624	Shewanella fidelis	9777	\N	\N	\N	\N	Shewanella fidelis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4189	624	Shewanella donghaensis	9776	\N	\N	\N	\N	Shewanella donghaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4190	624	Shewanella dokdonensis	9775	\N	\N	\N	\N	Shewanella dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4191	624	Shewanella denitrificans	9774	\N	\N	\N	\N	Shewanella denitrificans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4192	624	Shewanella decolorationis	9773	\N	\N	\N	\N	Shewanella decolorationis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4193	624	Shewanella corallii	9772	\N	\N	\N	\N	Shewanella corallii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4194	624	Shewanella colwelliana	9771	\N	\N	\N	\N	Shewanella colwelliana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4195	624	Shewanella chilikensis	9770	\N	\N	\N	\N	Shewanella chilikensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4196	624	Shewanella benthica	9769	\N	\N	\N	\N	Shewanella benthica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4197	624	Shewanella basaltis	9768	\N	\N	\N	\N	Shewanella basaltis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4198	624	Shewanella baltica	9767	\N	\N	\N	\N	Shewanella baltica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4199	624	Shewanella arctica	9766	\N	\N	\N	\N	Shewanella arctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4200	624	Shewanella aquimarina	9765	\N	\N	\N	\N	Shewanella aquimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4201	624	Shewanella amazonensis	9764	\N	\N	\N	\N	Shewanella amazonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4202	624	Shewanella algidipiscicola	9763	\N	\N	\N	\N	Shewanella algidipiscicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4203	624	Shewanella algae	9762	\N	\N	\N	\N	Shewanella algae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4204	624	Shewanella abyssi	9761	\N	\N	\N	\N	Shewanella abyssi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4205	625	Segniliparus rugosus	9758	\N	\N	\N	\N	Segniliparus rugosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4206	625	Segniliparus rotundus	9757	\N	\N	\N	\N	Segniliparus rotundus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4207	626	Schleiferia thermophila	9754	\N	\N	\N	\N	Schleiferia thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4208	627	Lewinella persica	9751	\N	\N	\N	\N	Lewinella persica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4209	627	Lewinella nigricans	9750	\N	\N	\N	\N	Lewinella nigricans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4210	627	Lewinella marina	9749	\N	\N	\N	\N	Lewinella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4211	627	Lewinella lutea	9748	\N	\N	\N	\N	Lewinella lutea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4212	627	Lewinella cohaerens	9747	\N	\N	\N	\N	Lewinella cohaerens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4213	627	Lewinella antarctica	9746	\N	\N	\N	\N	Lewinella antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4214	627	Lewinella agarilytica	9745	\N	\N	\N	\N	Lewinella agarilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4215	628	Haliscomenobacter hydrossis	9743	\N	\N	\N	\N	Haliscomenobacter hydrossis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4216	629	Aureispira marina	9741	\N	\N	\N	\N	Aureispira marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4217	630	Sanguibacter suarezii	9738	\N	\N	\N	\N	Sanguibacter suarezii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4218	630	Sanguibacter soli	9737	\N	\N	\N	\N	Sanguibacter soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4219	630	Sanguibacter marinus	9736	\N	\N	\N	\N	Sanguibacter marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4220	630	Sanguibacter keddieii	9735	\N	\N	\N	\N	Sanguibacter keddieii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4221	630	Sanguibacter inulinus	9734	\N	\N	\N	\N	Sanguibacter inulinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4222	630	Sanguibacter antarcticus	9733	\N	\N	\N	\N	Sanguibacter antarcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4223	631	Sandaracinus amylolyticus	9730	\N	\N	\N	\N	Sandaracinus amylolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4224	632	Salinisphaera shabanensis	9727	\N	\N	\N	\N	Salinisphaera shabanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4225	632	Salinisphaera orenii	9726	\N	\N	\N	\N	Salinisphaera orenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4226	632	Salinisphaera dokdonensis	9725	\N	\N	\N	\N	Salinisphaera dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4227	633	Saccharospirillum salsuginis	9722	\N	\N	\N	\N	Saccharospirillum salsuginis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4228	633	Saccharospirillum impatiens	9721	\N	\N	\N	\N	Saccharospirillum impatiens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4229	633	Saccharospirillum aestuarii	9720	\N	\N	\N	\N	Saccharospirillum aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4230	634	Subdoligranulum variabile	9717	\N	\N	\N	\N	Subdoligranulum variabile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4231	635	Sporobacter termitidis	9715	\N	\N	\N	\N	Sporobacter termitidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4232	636	Ruminococcus obeum	9713	\N	\N	\N	\N	Ruminococcus obeum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4233	636	Ruminococcus gnavus	9712	\N	\N	\N	\N	Ruminococcus gnavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4234	636	Ruminococcus gauvreauii	9711	\N	\N	\N	\N	Ruminococcus gauvreauii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4235	636	Ruminococcus faecis	9710	\N	\N	\N	\N	Ruminococcus faecis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4236	636	Ruminococcus champanellensis	9709	\N	\N	\N	\N	Ruminococcus champanellensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4237	637	Papillibacter cinnamivorans	9707	\N	\N	\N	\N	Papillibacter cinnamivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4238	638	Hydrogenoanaerobacterium saccharovorans	9705	\N	\N	\N	\N	Hydrogenoanaerobacterium saccharovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4239	639	Fastidiosipila sanguinis	9703	\N	\N	\N	\N	Fastidiosipila sanguinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4240	640	Faecalibacterium prausnitzii	9701	\N	\N	\N	\N	Faecalibacterium prausnitzii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4241	641	Ethanoligenens harbinense	9699	\N	\N	\N	\N	Ethanoligenens harbinense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4242	642	Anaerofilum pentosovorans	9697	\N	\N	\N	\N	Anaerofilum pentosovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4243	642	Anaerofilum agile	9696	\N	\N	\N	\N	Anaerofilum agile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4244	643	Acetivibrio multivorans	9694	\N	\N	\N	\N	Acetivibrio multivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4245	643	Acetivibrio ethanolgignens	9693	\N	\N	\N	\N	Acetivibrio ethanolgignens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4246	643	Acetivibrio cellulolyticus	9692	\N	\N	\N	\N	Acetivibrio cellulolyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4247	644	Acetanaerobacterium elongatum	9690	\N	\N	\N	\N	Acetanaerobacterium elongatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4248	645	Rubrobacter xylanophilus	9687	\N	\N	\N	\N	Rubrobacter xylanophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4249	645	Rubrobacter taiwanensis	9686	\N	\N	\N	\N	Rubrobacter taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4250	645	Rubrobacter radiotolerans	9685	\N	\N	\N	\N	Rubrobacter radiotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4251	646	Rubritalea tangerina	9682	\N	\N	\N	\N	Rubritalea tangerina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4252	646	Rubritalea squalenifaciens	9681	\N	\N	\N	\N	Rubritalea squalenifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4253	646	Rubritalea spongiae	9680	\N	\N	\N	\N	Rubritalea spongiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4254	646	Rubritalea sabuli	9679	\N	\N	\N	\N	Rubritalea sabuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4255	646	Rubritalea marina	9678	\N	\N	\N	\N	Rubritalea marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4256	646	Rubritalea halochordaticola	9677	\N	\N	\N	\N	Rubritalea halochordaticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4257	647	Ruania albidiflava	9674	\N	\N	\N	\N	Ruania albidiflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4258	648	Haloactinobacterium album	9672	\N	\N	\N	\N	Haloactinobacterium album	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4259	649	Rikenella microfusus	9669	\N	\N	\N	\N	Rikenella microfusus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4260	650	Alistipes shahii	9667	\N	\N	\N	\N	Alistipes shahii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4261	650	Alistipes putredinis	9666	\N	\N	\N	\N	Alistipes putredinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4262	650	Alistipes onderdonkii	9665	\N	\N	\N	\N	Alistipes onderdonkii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4263	650	Alistipes indistinctus	9664	\N	\N	\N	\N	Alistipes indistinctus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4264	650	Alistipes finegoldii	9663	\N	\N	\N	\N	Alistipes finegoldii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4265	651	Rickettsia typhi	9660	\N	\N	\N	\N	Rickettsia typhi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4266	651	Rickettsia tamurae	9659	\N	\N	\N	\N	Rickettsia tamurae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4267	651	Rickettsia sibirica	9658	\N	\N	\N	\N	Rickettsia sibirica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4268	651	Rickettsia rickettsii	9657	\N	\N	\N	\N	Rickettsia rickettsii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4269	651	Rickettsia rhipicephali	9656	\N	\N	\N	\N	Rickettsia rhipicephali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4270	651	Rickettsia raoultii	9655	\N	\N	\N	\N	Rickettsia raoultii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4271	651	Rickettsia prowazekii	9654	\N	\N	\N	\N	Rickettsia prowazekii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4272	651	Rickettsia parkeri	9653	\N	\N	\N	\N	Rickettsia parkeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4273	651	Rickettsia montanensis	9652	\N	\N	\N	\N	Rickettsia montanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4274	651	Rickettsia massiliae	9651	\N	\N	\N	\N	Rickettsia massiliae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4275	651	Rickettsia honei	9650	\N	\N	\N	\N	Rickettsia honei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4276	651	Rickettsia heilongjiangensis	9649	\N	\N	\N	\N	Rickettsia heilongjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4277	651	Rickettsia conorii	9648	\N	\N	\N	\N	Rickettsia conorii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4278	651	Rickettsia canadensis	9647	\N	\N	\N	\N	Rickettsia canadensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4279	651	Rickettsia bellii	9646	\N	\N	\N	\N	Rickettsia bellii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4280	651	Rickettsia australis	9645	\N	\N	\N	\N	Rickettsia australis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4281	651	Rickettsia asiatica	9644	\N	\N	\N	\N	Rickettsia asiatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4282	651	Rickettsia akari	9643	\N	\N	\N	\N	Rickettsia akari	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4283	651	Rickettsia aeschlimannii	9642	\N	\N	\N	\N	Rickettsia aeschlimannii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4284	652	Orientia tsutsugamushi	9640	\N	\N	\N	\N	Orientia tsutsugamushi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4285	653	Salisaeta longa	9637	\N	\N	\N	\N	Salisaeta longa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4286	654	Salinibacter ruber	9635	\N	\N	\N	\N	Salinibacter ruber	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4287	654	Salinibacter luteus	9634	\N	\N	\N	\N	Salinibacter luteus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4288	654	Salinibacter iranicus	9633	\N	\N	\N	\N	Salinibacter iranicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4289	655	Rubricoccus marinus	9631	\N	\N	\N	\N	Rubricoccus marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4290	656	Rhodothermus profundi	9629	\N	\N	\N	\N	Rhodothermus profundi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4291	656	Rhodothermus marinus	9628	\N	\N	\N	\N	Rhodothermus marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4292	657	Reyranella massiliensis	9625	\N	\N	\N	\N	Reyranella massiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4293	658	Elioraea tepidiphila	9623	\N	\N	\N	\N	Elioraea tepidiphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4294	659	Tistrella mobilis	9620	\N	\N	\N	\N	Tistrella mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4295	659	Tistrella bauzanensis	9619	\N	\N	\N	\N	Tistrella bauzanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4296	660	Thalassospira xianhensis	9617	\N	\N	\N	\N	Thalassospira xianhensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4297	660	Thalassospira xiamenensis	9616	\N	\N	\N	\N	Thalassospira xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4298	660	Thalassospira tepidiphila	9615	\N	\N	\N	\N	Thalassospira tepidiphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4299	660	Thalassospira profundimaris	9614	\N	\N	\N	\N	Thalassospira profundimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4300	660	Thalassospira lucentensis	9613	\N	\N	\N	\N	Thalassospira lucentensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4301	661	Skermanella xinjiangensis	9611	\N	\N	\N	\N	Skermanella xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4302	661	Skermanella stibiiresistens	9610	\N	\N	\N	\N	Skermanella stibiiresistens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4303	661	Skermanella parooensis	9609	\N	\N	\N	\N	Skermanella parooensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4304	661	Skermanella aerolata	9608	\N	\N	\N	\N	Skermanella aerolata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4305	662	Roseospira visakhapatnamensis	9606	\N	\N	\N	\N	Roseospira visakhapatnamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4306	662	Roseospira marina	9605	\N	\N	\N	\N	Roseospira marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4307	662	Roseospira goensis	9604	\N	\N	\N	\N	Roseospira goensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4308	663	Rhodovibrio sodomensis	9602	\N	\N	\N	\N	Rhodovibrio sodomensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4309	663	Rhodovibrio salinarum	9601	\N	\N	\N	\N	Rhodovibrio salinarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4310	664	Rhodospirillum sulfurexigens	9599	\N	\N	\N	\N	Rhodospirillum sulfurexigens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4311	664	Rhodospirillum rubrum	9598	\N	\N	\N	\N	Rhodospirillum rubrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4312	664	Rhodospirillum photometricum	9597	\N	\N	\N	\N	Rhodospirillum photometricum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4313	665	Rhodospira trueperi	9595	\N	\N	\N	\N	Rhodospira trueperi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4314	666	Rhodocista pekingensis	9593	\N	\N	\N	\N	Rhodocista pekingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4315	667	Phaeovibrio sulfidiphilus	9591	\N	\N	\N	\N	Phaeovibrio sulfidiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4316	668	Phaeospirillum tilakii	9589	\N	\N	\N	\N	Phaeospirillum tilakii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4317	668	Phaeospirillum oryzae	9588	\N	\N	\N	\N	Phaeospirillum oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4318	668	Phaeospirillum molischianum	9587	\N	\N	\N	\N	Phaeospirillum molischianum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4319	668	Phaeospirillum fulvum	9586	\N	\N	\N	\N	Phaeospirillum fulvum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4320	668	Phaeospirillum chandramohanii	9585	\N	\N	\N	\N	Phaeospirillum chandramohanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4321	669	Pelagibius litoralis	9583	\N	\N	\N	\N	Pelagibius litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4322	670	Oceanibaculum pacificum	9581	\N	\N	\N	\N	Oceanibaculum pacificum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4323	670	Oceanibaculum indicum	9580	\N	\N	\N	\N	Oceanibaculum indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4324	671	Novispirillum itersonii subsp. nipponicum	9578	\N	\N	\N	\N	Novispirillum itersonii subsp. nipponicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4325	671	Novispirillum itersonii subsp. itersonii	9577	\N	\N	\N	\N	Novispirillum itersonii subsp. itersonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4326	672	Marispirillum indicum	9575	\N	\N	\N	\N	Marispirillum indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4327	673	Magnetospirillum magnetotacticum	9573	\N	\N	\N	\N	Magnetospirillum magnetotacticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4328	673	Magnetospirillum gryphiswaldense	9572	\N	\N	\N	\N	Magnetospirillum gryphiswaldense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4329	674	Insolitispirillum peregrinum subsp. peregrinum	9570	\N	\N	\N	\N	Insolitispirillum peregrinum subsp. peregrinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4330	674	Insolitispirillum peregrinum subsp. integrum	9569	\N	\N	\N	\N	Insolitispirillum peregrinum subsp. integrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4331	675	Inquilinus limosus	9567	\N	\N	\N	\N	Inquilinus limosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4332	675	Inquilinus ginsengisoli	9566	\N	\N	\N	\N	Inquilinus ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4333	676	Fodinicurvata sediminis	9564	\N	\N	\N	\N	Fodinicurvata sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4334	676	Fodinicurvata fenggangensis	9563	\N	\N	\N	\N	Fodinicurvata fenggangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4335	677	Elstera litoralis	9561	\N	\N	\N	\N	Elstera litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4336	678	Dongia mobilis	9559	\N	\N	\N	\N	Dongia mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4337	679	Desertibacter roseus	9557	\N	\N	\N	\N	Desertibacter roseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4338	680	Defluviicoccus vanus	9555	\N	\N	\N	\N	Defluviicoccus vanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4339	681	Constrictibacter antarcticus	9553	\N	\N	\N	\N	Constrictibacter antarcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4340	682	Caenispirillum salinarum	9551	\N	\N	\N	\N	Caenispirillum salinarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4341	682	Caenispirillum bisanense	9550	\N	\N	\N	\N	Caenispirillum bisanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4342	683	Azospirillum zeae	9548	\N	\N	\N	\N	Azospirillum zeae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4343	683	Azospirillum rugosum	9547	\N	\N	\N	\N	Azospirillum rugosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4344	683	Azospirillum picis	9546	\N	\N	\N	\N	Azospirillum picis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4345	683	Azospirillum melinis	9545	\N	\N	\N	\N	Azospirillum melinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4346	683	Azospirillum lipoferum	9544	\N	\N	\N	\N	Azospirillum lipoferum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4347	683	Azospirillum irakense	9543	\N	\N	\N	\N	Azospirillum irakense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4348	683	Azospirillum formosense	9542	\N	\N	\N	\N	Azospirillum formosense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4349	683	Azospirillum canadense	9541	\N	\N	\N	\N	Azospirillum canadense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4350	683	Azospirillum brasilense	9540	\N	\N	\N	\N	Azospirillum brasilense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4351	683	Azospirillum amazonense	9539	\N	\N	\N	\N	Azospirillum amazonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4352	684	Zoogloea resiniphila	9536	\N	\N	\N	\N	Zoogloea resiniphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4353	684	Zoogloea ramigera	9535	\N	\N	\N	\N	Zoogloea ramigera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4354	684	Zoogloea oryzae	9534	\N	\N	\N	\N	Zoogloea oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4355	684	Zoogloea caeni	9533	\N	\N	\N	\N	Zoogloea caeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4356	685	Uliginosibacterium gangwonense	9531	\N	\N	\N	\N	Uliginosibacterium gangwonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4357	686	Thauera terpenica	9529	\N	\N	\N	\N	Thauera terpenica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4358	686	Thauera selenatis	9528	\N	\N	\N	\N	Thauera selenatis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4359	686	Thauera phenylacetica	9527	\N	\N	\N	\N	Thauera phenylacetica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4360	686	Thauera mechernichensis	9526	\N	\N	\N	\N	Thauera mechernichensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4361	686	Thauera linaloolentis	9525	\N	\N	\N	\N	Thauera linaloolentis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4362	686	Thauera chlorobenzoica	9524	\N	\N	\N	\N	Thauera chlorobenzoica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4363	686	Thauera butanivorans	9523	\N	\N	\N	\N	Thauera butanivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4364	686	Thauera aromatica	9522	\N	\N	\N	\N	Thauera aromatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4365	686	Thauera aminoaromatica	9521	\N	\N	\N	\N	Thauera aminoaromatica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4366	687	Sulfuritalea hydrogenivorans	9519	\N	\N	\N	\N	Sulfuritalea hydrogenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4367	688	Sterolibacterium denitrificans	9517	\N	\N	\N	\N	Sterolibacterium denitrificans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4368	689	Rhodocyclus tenuis	9515	\N	\N	\N	\N	Rhodocyclus tenuis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4369	689	Rhodocyclus purpureus	9514	\N	\N	\N	\N	Rhodocyclus purpureus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4370	690	Quatrionicoccus australiensis	9512	\N	\N	\N	\N	Quatrionicoccus australiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4371	691	Propionivibrio pelophilus	9510	\N	\N	\N	\N	Propionivibrio pelophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4372	691	Propionivibrio limicola	9509	\N	\N	\N	\N	Propionivibrio limicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4373	691	Propionivibrio dicarboxylicus	9508	\N	\N	\N	\N	Propionivibrio dicarboxylicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4374	692	Georgfuchsia toluolica	9506	\N	\N	\N	\N	Georgfuchsia toluolica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4375	693	Ferribacterium limneticum	9504	\N	\N	\N	\N	Ferribacterium limneticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4376	694	Denitratisoma oestradiolicum	9502	\N	\N	\N	\N	Denitratisoma oestradiolicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4377	695	Dechloromonas hortensis	9500	\N	\N	\N	\N	Dechloromonas hortensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4378	695	Dechloromonas denitrificans	9499	\N	\N	\N	\N	Dechloromonas denitrificans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4379	695	Dechloromonas agitata	9498	\N	\N	\N	\N	Dechloromonas agitata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4380	696	Azovibrio restrictus	9496	\N	\N	\N	\N	Azovibrio restrictus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4381	697	Azospira restricta	9494	\N	\N	\N	\N	Azospira restricta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4382	697	Azospira oryzae	9493	\N	\N	\N	\N	Azospira oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4383	698	Azonexus hydrophilus	9491	\N	\N	\N	\N	Azonexus hydrophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4384	698	Azonexus fungiphilus	9490	\N	\N	\N	\N	Azonexus fungiphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4385	698	Azonexus caeni	9489	\N	\N	\N	\N	Azonexus caeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4386	699	Azoarcus toluvorans	9487	\N	\N	\N	\N	Azoarcus toluvorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4387	699	Azoarcus tolulyticus	9486	\N	\N	\N	\N	Azoarcus tolulyticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4388	699	Azoarcus toluclasticus	9485	\N	\N	\N	\N	Azoarcus toluclasticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4389	699	Azoarcus indigens	9484	\N	\N	\N	\N	Azoarcus indigens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4390	699	Azoarcus evansii	9483	\N	\N	\N	\N	Azoarcus evansii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4391	699	Azoarcus buckelii	9482	\N	\N	\N	\N	Azoarcus buckelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4392	699	Azoarcus anaerobius	9481	\N	\N	\N	\N	Azoarcus anaerobius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4393	700	Tepidamorphus gemmatus	9478	\N	\N	\N	\N	Tepidamorphus gemmatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4394	701	Rhodoligotrophos appendicifer	9476	\N	\N	\N	\N	Rhodoligotrophos appendicifer	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4395	702	Rhodobium orientis	9474	\N	\N	\N	\N	Rhodobium orientis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4396	702	Rhodobium gokarnense	9473	\N	\N	\N	\N	Rhodobium gokarnense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4397	703	Parvibaculum lavamentivorans	9471	\N	\N	\N	\N	Parvibaculum lavamentivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4398	703	Parvibaculum indicum	9470	\N	\N	\N	\N	Parvibaculum indicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4399	704	Lutibaculum baratangense	9468	\N	\N	\N	\N	Lutibaculum baratangense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4400	705	Anderseniella baltica	9466	\N	\N	\N	\N	Anderseniella baltica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4401	706	Afifella pfennigii	9464	\N	\N	\N	\N	Afifella pfennigii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4402	706	Afifella marina	9463	\N	\N	\N	\N	Afifella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4403	707	Yangia pacifica	9460	\N	\N	\N	\N	Yangia pacifica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4404	708	Wenxinia marina	9458	\N	\N	\N	\N	Wenxinia marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4405	709	Vadicella arenosi	9456	\N	\N	\N	\N	Vadicella arenosi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4406	710	Tropicimonas isoalkanivorans	9454	\N	\N	\N	\N	Tropicimonas isoalkanivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4407	710	Tropicimonas aquimaris	9453	\N	\N	\N	\N	Tropicimonas aquimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4408	711	Tropicibacter naphthalenivorans	9451	\N	\N	\N	\N	Tropicibacter naphthalenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4409	711	Tropicibacter multivorans	9450	\N	\N	\N	\N	Tropicibacter multivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4410	712	Tranquillimonas alkanivorans	9448	\N	\N	\N	\N	Tranquillimonas alkanivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4411	713	Thioclava pacifica	9446	\N	\N	\N	\N	Thioclava pacifica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4412	714	Thalassococcus halodurans	9444	\N	\N	\N	\N	Thalassococcus halodurans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4413	715	Thalassobius mediterraneus	9442	\N	\N	\N	\N	Thalassobius mediterraneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4414	715	Thalassobius maritimus	9441	\N	\N	\N	\N	Thalassobius maritimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4415	715	Thalassobius gelatinovorus	9440	\N	\N	\N	\N	Thalassobius gelatinovorus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4416	715	Thalassobius aestuarii	9439	\N	\N	\N	\N	Thalassobius aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4417	716	Thalassobacter stenotrophicus	9437	\N	\N	\N	\N	Thalassobacter stenotrophicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4418	717	Tateyamaria omphalii	9435	\N	\N	\N	\N	Tateyamaria omphalii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4419	718	Sulfitobacter pontiacus	9433	\N	\N	\N	\N	Sulfitobacter pontiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4420	718	Sulfitobacter mediterraneus	9432	\N	\N	\N	\N	Sulfitobacter mediterraneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4421	718	Sulfitobacter marinus	9431	\N	\N	\N	\N	Sulfitobacter marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4422	718	Sulfitobacter litoralis	9430	\N	\N	\N	\N	Sulfitobacter litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4423	718	Sulfitobacter guttiformis	9429	\N	\N	\N	\N	Sulfitobacter guttiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4424	718	Sulfitobacter dubius	9428	\N	\N	\N	\N	Sulfitobacter dubius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4425	718	Sulfitobacter donghicola	9427	\N	\N	\N	\N	Sulfitobacter donghicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4426	718	Sulfitobacter delicatus	9426	\N	\N	\N	\N	Sulfitobacter delicatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4427	718	Sulfitobacter brevis	9425	\N	\N	\N	\N	Sulfitobacter brevis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4428	719	Stappia stellulata	9423	\N	\N	\N	\N	Stappia stellulata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4429	719	Stappia indica	9422	\N	\N	\N	\N	Stappia indica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4430	720	Silicibacter pomeroyi	9420	\N	\N	\N	\N	Silicibacter pomeroyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4431	721	Shimia marina	9418	\N	\N	\N	\N	Shimia marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4432	721	Shimia isoporae	9417	\N	\N	\N	\N	Shimia isoporae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4433	722	Seohaeicola saemankumensis	9415	\N	\N	\N	\N	Seohaeicola saemankumensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4434	723	Sediminimonas qiaohouensis	9413	\N	\N	\N	\N	Sediminimonas qiaohouensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4435	724	Salipiger mucosus	9411	\N	\N	\N	\N	Salipiger mucosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4436	725	Salinihabitans flavidus	9409	\N	\N	\N	\N	Salinihabitans flavidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4437	726	Sagittula stellata	9407	\N	\N	\N	\N	Sagittula stellata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4438	727	Ruegeria scottomollicae	9405	\N	\N	\N	\N	Ruegeria scottomollicae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4439	727	Ruegeria mobilis	9404	\N	\N	\N	\N	Ruegeria mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4440	727	Ruegeria marina	9403	\N	\N	\N	\N	Ruegeria marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4441	727	Ruegeria halocynthiae	9402	\N	\N	\N	\N	Ruegeria halocynthiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4442	727	Ruegeria faecimaris	9401	\N	\N	\N	\N	Ruegeria faecimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4443	727	Ruegeria atlantica	9400	\N	\N	\N	\N	Ruegeria atlantica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4444	728	Rubribacterium polymorphum	9398	\N	\N	\N	\N	Rubribacterium polymorphum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4445	729	Rubellimicrobium thermophilum	9396	\N	\N	\N	\N	Rubellimicrobium thermophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4446	729	Rubellimicrobium mesophilum	9395	\N	\N	\N	\N	Rubellimicrobium mesophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4447	729	Rubellimicrobium aerolatum	9394	\N	\N	\N	\N	Rubellimicrobium aerolatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4448	730	Roseovarius tolerans	9392	\N	\N	\N	\N	Roseovarius tolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4449	730	Roseovarius pacificus	9391	\N	\N	\N	\N	Roseovarius pacificus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4450	730	Roseovarius nubinhibens	9390	\N	\N	\N	\N	Roseovarius nubinhibens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4451	730	Roseovarius nanhaiticus	9389	\N	\N	\N	\N	Roseovarius nanhaiticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4452	730	Roseovarius mucosus	9388	\N	\N	\N	\N	Roseovarius mucosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4453	730	Roseovarius marinus	9387	\N	\N	\N	\N	Roseovarius marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4454	730	Roseovarius indicus	9386	\N	\N	\N	\N	Roseovarius indicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4455	730	Roseovarius halotolerans	9385	\N	\N	\N	\N	Roseovarius halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4456	730	Roseovarius halocynthiae	9384	\N	\N	\N	\N	Roseovarius halocynthiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4457	730	Roseovarius crassostreae	9383	\N	\N	\N	\N	Roseovarius crassostreae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4458	730	Roseovarius aestuarii	9382	\N	\N	\N	\N	Roseovarius aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4459	731	Roseobacter litoralis	9380	\N	\N	\N	\N	Roseobacter litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4460	732	Roseivivax sediminis	9378	\N	\N	\N	\N	Roseivivax sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4461	732	Roseivivax lentus	9377	\N	\N	\N	\N	Roseivivax lentus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4462	732	Roseivivax isoporae	9376	\N	\N	\N	\N	Roseivivax isoporae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4463	732	Roseivivax halotolerans	9375	\N	\N	\N	\N	Roseivivax halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4464	732	Roseivivax halodurans	9374	\N	\N	\N	\N	Roseivivax halodurans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4465	733	Roseisalinus antarcticus	9372	\N	\N	\N	\N	Roseisalinus antarcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4466	734	Roseinatronobacter monicus	9370	\N	\N	\N	\N	Roseinatronobacter monicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4467	735	Roseicyclus mahoneyensis	9368	\N	\N	\N	\N	Roseicyclus mahoneyensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4468	736	Roseicitreum antarcticum	9366	\N	\N	\N	\N	Roseicitreum antarcticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4469	737	Roseibium hamelinense	9364	\N	\N	\N	\N	Roseibium hamelinense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4470	737	Roseibium denhamense	9363	\N	\N	\N	\N	Roseibium denhamense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4471	738	Roseibacterium elongatum	9361	\N	\N	\N	\N	Roseibacterium elongatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4472	739	Roseibaca ekhonensis	9359	\N	\N	\N	\N	Roseibaca ekhonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4473	740	Rhodovulum visakhapatnamense	9357	\N	\N	\N	\N	Rhodovulum visakhapatnamense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4474	740	Rhodovulum sulfidophilum	9356	\N	\N	\N	\N	Rhodovulum sulfidophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4475	740	Rhodovulum strictum	9355	\N	\N	\N	\N	Rhodovulum strictum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4476	740	Rhodovulum steppense	9354	\N	\N	\N	\N	Rhodovulum steppense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4477	740	Rhodovulum robiginosum	9353	\N	\N	\N	\N	Rhodovulum robiginosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4478	740	Rhodovulum marinum	9352	\N	\N	\N	\N	Rhodovulum marinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4479	740	Rhodovulum lacipunicei	9351	\N	\N	\N	\N	Rhodovulum lacipunicei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4480	740	Rhodovulum kholense	9350	\N	\N	\N	\N	Rhodovulum kholense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4481	740	Rhodovulum iodosum	9349	\N	\N	\N	\N	Rhodovulum iodosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4482	740	Rhodovulum imhoffii	9348	\N	\N	\N	\N	Rhodovulum imhoffii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4483	740	Rhodovulum euryhalinum	9347	\N	\N	\N	\N	Rhodovulum euryhalinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4484	740	Rhodovulum adriaticum	9346	\N	\N	\N	\N	Rhodovulum adriaticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4485	741	Rhodobacter vinaykumarii	9344	\N	\N	\N	\N	Rhodobacter vinaykumarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4486	741	Rhodobacter veldkampii	9343	\N	\N	\N	\N	Rhodobacter veldkampii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4487	741	Rhodobacter sphaeroides	9342	\N	\N	\N	\N	Rhodobacter sphaeroides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4488	741	Rhodobacter megalophilus	9341	\N	\N	\N	\N	Rhodobacter megalophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4489	741	Rhodobacter maris	9340	\N	\N	\N	\N	Rhodobacter maris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4490	741	Rhodobacter johrii	9339	\N	\N	\N	\N	Rhodobacter johrii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4491	741	Rhodobacter capsulatus	9338	\N	\N	\N	\N	Rhodobacter capsulatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4492	741	Rhodobacter blasticus	9337	\N	\N	\N	\N	Rhodobacter blasticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4493	741	Rhodobacter azotoformans	9336	\N	\N	\N	\N	Rhodobacter azotoformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4494	741	Rhodobacter aestuarii	9335	\N	\N	\N	\N	Rhodobacter aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4495	742	Rhodobaca bogoriensis	9333	\N	\N	\N	\N	Rhodobaca bogoriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4496	742	Rhodobaca barguzinensis	9332	\N	\N	\N	\N	Rhodobaca barguzinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4497	743	Pseudovibrio japonicus	9330	\N	\N	\N	\N	Pseudovibrio japonicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4498	743	Pseudovibrio denitrificans	9329	\N	\N	\N	\N	Pseudovibrio denitrificans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4499	743	Pseudovibrio ascidiaceicola	9328	\N	\N	\N	\N	Pseudovibrio ascidiaceicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4500	744	Pseudoruegeria lutimaris	9326	\N	\N	\N	\N	Pseudoruegeria lutimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4501	744	Pseudoruegeria aquimaris	9325	\N	\N	\N	\N	Pseudoruegeria aquimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4502	745	Pseudorhodobacter ferrugineus	9323	\N	\N	\N	\N	Pseudorhodobacter ferrugineus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4503	745	Pseudorhodobacter aquimaris	9322	\N	\N	\N	\N	Pseudorhodobacter aquimaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4504	746	Primorskyibacter sedentarius	9320	\N	\N	\N	\N	Primorskyibacter sedentarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4505	747	Poseidonocella sedimentorum	9318	\N	\N	\N	\N	Poseidonocella sedimentorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4506	747	Poseidonocella pacifica	9317	\N	\N	\N	\N	Poseidonocella pacifica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4507	748	Ponticoccus litoralis	9315	\N	\N	\N	\N	Ponticoccus litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4508	749	Pontibaca methylaminivorans	9313	\N	\N	\N	\N	Pontibaca methylaminivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4509	750	Planktotalea frisia	9311	\N	\N	\N	\N	Planktotalea frisia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4510	751	Phaeobacter inhibens	9309	\N	\N	\N	\N	Phaeobacter inhibens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4511	751	Phaeobacter gallaeciensis	9308	\N	\N	\N	\N	Phaeobacter gallaeciensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4512	751	Phaeobacter daeponensis	9307	\N	\N	\N	\N	Phaeobacter daeponensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4513	751	Phaeobacter caeruleus	9306	\N	\N	\N	\N	Phaeobacter caeruleus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4514	751	Phaeobacter arcticus	9305	\N	\N	\N	\N	Phaeobacter arcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4515	752	Pelagicola litoralis	9303	\N	\N	\N	\N	Pelagicola litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4516	753	Pelagibaca bermudensis	9301	\N	\N	\N	\N	Pelagibaca bermudensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4517	754	Paracoccus zeaxanthinifaciens	9299	\N	\N	\N	\N	Paracoccus zeaxanthinifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4518	754	Paracoccus yeei	9298	\N	\N	\N	\N	Paracoccus yeei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4519	754	Paracoccus versutus	9297	\N	\N	\N	\N	Paracoccus versutus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4520	754	Paracoccus thiocyanatus	9296	\N	\N	\N	\N	Paracoccus thiocyanatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4521	754	Paracoccus sulfuroxidans	9295	\N	\N	\N	\N	Paracoccus sulfuroxidans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4522	754	Paracoccus stylophorae	9294	\N	\N	\N	\N	Paracoccus stylophorae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4523	754	Paracoccus sphaerophysae	9293	\N	\N	\N	\N	Paracoccus sphaerophysae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4524	754	Paracoccus solventivorans	9292	\N	\N	\N	\N	Paracoccus solventivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4525	754	Paracoccus seriniphilus	9291	\N	\N	\N	\N	Paracoccus seriniphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4526	754	Paracoccus saliphilus	9290	\N	\N	\N	\N	Paracoccus saliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4527	754	Paracoccus pantotrophus	9289	\N	\N	\N	\N	Paracoccus pantotrophus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4528	754	Paracoccus niistensis	9288	\N	\N	\N	\N	Paracoccus niistensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4529	754	Paracoccus marinus	9287	\N	\N	\N	\N	Paracoccus marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4530	754	Paracoccus marcusii	9286	\N	\N	\N	\N	Paracoccus marcusii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4531	754	Paracoccus koreensis	9285	\N	\N	\N	\N	Paracoccus koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4532	754	Paracoccus kondratievae	9284	\N	\N	\N	\N	Paracoccus kondratievae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4533	754	Paracoccus kocurii	9283	\N	\N	\N	\N	Paracoccus kocurii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4534	754	Paracoccus isoporae	9282	\N	\N	\N	\N	Paracoccus isoporae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4535	754	Paracoccus homiensis	9281	\N	\N	\N	\N	Paracoccus homiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4536	754	Paracoccus halophilus	9280	\N	\N	\N	\N	Paracoccus halophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4537	754	Paracoccus haeundaensis	9279	\N	\N	\N	\N	Paracoccus haeundaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4538	754	Paracoccus fistulariae	9278	\N	\N	\N	\N	Paracoccus fistulariae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4539	754	Paracoccus denitrificans	9277	\N	\N	\N	\N	Paracoccus denitrificans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4540	754	Paracoccus chinensis	9276	\N	\N	\N	\N	Paracoccus chinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4541	754	Paracoccus carotinifaciens	9275	\N	\N	\N	\N	Paracoccus carotinifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4542	754	Paracoccus caeni	9274	\N	\N	\N	\N	Paracoccus caeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4543	754	Paracoccus bengalensis	9273	\N	\N	\N	\N	Paracoccus bengalensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4544	754	Paracoccus aminovorans	9272	\N	\N	\N	\N	Paracoccus aminovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4545	754	Paracoccus aminophilus	9271	\N	\N	\N	\N	Paracoccus aminophilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4546	754	Paracoccus alkenifer	9270	\N	\N	\N	\N	Paracoccus alkenifer	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4547	754	Paracoccus alcaliphilus	9269	\N	\N	\N	\N	Paracoccus alcaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4548	754	Paracoccus aestuarii	9268	\N	\N	\N	\N	Paracoccus aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4549	755	Pannonibacter phragmitetus	9266	\N	\N	\N	\N	Pannonibacter phragmitetus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4550	756	Palleronia marisminoris	9264	\N	\N	\N	\N	Palleronia marisminoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4551	757	Pacificibacter maritimus	9262	\N	\N	\N	\N	Pacificibacter maritimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4552	758	Octadecabacter arcticus	9260	\N	\N	\N	\N	Octadecabacter arcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4553	758	Octadecabacter antarcticus	9259	\N	\N	\N	\N	Octadecabacter antarcticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4554	759	Oceanicola pacificus	9257	\N	\N	\N	\N	Oceanicola pacificus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4555	759	Oceanicola nitratireducens	9256	\N	\N	\N	\N	Oceanicola nitratireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4556	759	Oceanicola nanhaiensis	9255	\N	\N	\N	\N	Oceanicola nanhaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4557	759	Oceanicola marinus	9254	\N	\N	\N	\N	Oceanicola marinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4558	759	Oceanicola granulosus	9253	\N	\N	\N	\N	Oceanicola granulosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4559	759	Oceanicola batsensis	9252	\N	\N	\N	\N	Oceanicola batsensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4560	760	Oceanibulbus indolifex	9250	\N	\N	\N	\N	Oceanibulbus indolifex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4561	761	Nesiotobacter exalbescens	9248	\N	\N	\N	\N	Nesiotobacter exalbescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4562	762	Nereida ignava	9246	\N	\N	\N	\N	Nereida ignava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4563	763	Nautella italica	9244	\N	\N	\N	\N	Nautella italica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4564	764	Methylarcula terricola	9242	\N	\N	\N	\N	Methylarcula terricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4565	765	Marivita litorea	9240	\N	\N	\N	\N	Marivita litorea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4566	765	Marivita hallyeonensis	9239	\N	\N	\N	\N	Marivita hallyeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4567	765	Marivita cryptomonadis	9238	\N	\N	\N	\N	Marivita cryptomonadis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4568	765	Marivita byunsanensis	9237	\N	\N	\N	\N	Marivita byunsanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4569	766	Maritimibacter alkaliphilus	9235	\N	\N	\N	\N	Maritimibacter alkaliphilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4570	767	Marinovum algicola	9233	\N	\N	\N	\N	Marinovum algicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4571	768	Maribius salinus	9231	\N	\N	\N	\N	Maribius salinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4572	768	Maribius pelagius	9230	\N	\N	\N	\N	Maribius pelagius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4573	769	Mameliella alba	9228	\N	\N	\N	\N	Mameliella alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4574	770	Lutimaribacter saemankumensis	9226	\N	\N	\N	\N	Lutimaribacter saemankumensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4575	771	Loktanella vestfoldensis	9224	\N	\N	\N	\N	Loktanella vestfoldensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4576	771	Loktanella tamlensis	9223	\N	\N	\N	\N	Loktanella tamlensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4577	771	Loktanella salsilacus	9222	\N	\N	\N	\N	Loktanella salsilacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4578	771	Loktanella rosea	9221	\N	\N	\N	\N	Loktanella rosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4579	771	Loktanella pyoseonensis	9220	\N	\N	\N	\N	Loktanella pyoseonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4580	771	Loktanella maricola	9219	\N	\N	\N	\N	Loktanella maricola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4581	771	Loktanella koreensis	9218	\N	\N	\N	\N	Loktanella koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4582	771	Loktanella hongkongensis	9217	\N	\N	\N	\N	Loktanella hongkongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4583	771	Loktanella fryxellensis	9216	\N	\N	\N	\N	Loktanella fryxellensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4584	771	Loktanella atrilutea	9215	\N	\N	\N	\N	Loktanella atrilutea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4585	771	Loktanella agnita	9214	\N	\N	\N	\N	Loktanella agnita	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4586	772	Litorimicrobium taeanense	9212	\N	\N	\N	\N	Litorimicrobium taeanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4587	773	Litoreibacter meonggei	9210	\N	\N	\N	\N	Litoreibacter meonggei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4588	773	Litoreibacter janthinus	9209	\N	\N	\N	\N	Litoreibacter janthinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4589	773	Litoreibacter arenae	9208	\N	\N	\N	\N	Litoreibacter arenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4590	773	Litoreibacter albidus	9207	\N	\N	\N	\N	Litoreibacter albidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4591	774	Lentibacter algarum	9205	\N	\N	\N	\N	Lentibacter algarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4592	775	Leisingera nanhaiensis	9203	\N	\N	\N	\N	Leisingera nanhaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4593	775	Leisingera methylohalidivorans	9202	\N	\N	\N	\N	Leisingera methylohalidivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4594	775	Leisingera aquimarina	9201	\N	\N	\N	\N	Leisingera aquimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4595	776	Labrenzia marina	9199	\N	\N	\N	\N	Labrenzia marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4596	776	Labrenzia alba	9198	\N	\N	\N	\N	Labrenzia alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4597	776	Labrenzia aggregata	9197	\N	\N	\N	\N	Labrenzia aggregata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4598	777	Ketogulonicigenium vulgare	9195	\N	\N	\N	\N	Ketogulonicigenium vulgare	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4599	777	Ketogulonicigenium robustum	9194	\N	\N	\N	\N	Ketogulonicigenium robustum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4600	778	Jhaorihella thermophila	9192	\N	\N	\N	\N	Jhaorihella thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4601	779	Jannaschia seosinensis	9190	\N	\N	\N	\N	Jannaschia seosinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4602	779	Jannaschia seohaensis	9189	\N	\N	\N	\N	Jannaschia seohaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4603	779	Jannaschia rubra	9188	\N	\N	\N	\N	Jannaschia rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4604	779	Jannaschia pohangensis	9187	\N	\N	\N	\N	Jannaschia pohangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4605	779	Jannaschia helgolandensis	9186	\N	\N	\N	\N	Jannaschia helgolandensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4606	779	Jannaschia donghaensis	9185	\N	\N	\N	\N	Jannaschia donghaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4607	780	Hwanghaeicola aestuarii	9183	\N	\N	\N	\N	Hwanghaeicola aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4608	781	Huaishuia halophila	9181	\N	\N	\N	\N	Huaishuia halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4609	782	Hasllibacter halocynthiae	9179	\N	\N	\N	\N	Hasllibacter halocynthiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4610	783	Haematobacter missouriensis	9177	\N	\N	\N	\N	Haematobacter missouriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4611	783	Haematobacter massiliensis	9176	\N	\N	\N	\N	Haematobacter massiliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4612	784	Gemmobacter aquatilis	9174	\N	\N	\N	\N	Gemmobacter aquatilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4613	785	Donghicola xiamenensis	9172	\N	\N	\N	\N	Donghicola xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4614	785	Donghicola eburneus	9171	\N	\N	\N	\N	Donghicola eburneus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4615	786	Citreimonas salinaria	9169	\N	\N	\N	\N	Citreimonas salinaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4616	787	Citreicella thiooxidans	9167	\N	\N	\N	\N	Citreicella thiooxidans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4617	787	Citreicella marina	9166	\N	\N	\N	\N	Citreicella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4618	787	Citreicella aestuarii	9165	\N	\N	\N	\N	Citreicella aestuarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4619	788	Celeribacter neptunius	9163	\N	\N	\N	\N	Celeribacter neptunius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4620	788	Celeribacter baekdonensis	9162	\N	\N	\N	\N	Celeribacter baekdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4621	789	Catellibacterium nectariphilum	9160	\N	\N	\N	\N	Catellibacterium nectariphilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4622	789	Catellibacterium nanjingense	9159	\N	\N	\N	\N	Catellibacterium nanjingense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4623	789	Catellibacterium changlense	9158	\N	\N	\N	\N	Catellibacterium changlense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4624	789	Catellibacterium caeni	9157	\N	\N	\N	\N	Catellibacterium caeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4625	789	Catellibacterium aquatile	9156	\N	\N	\N	\N	Catellibacterium aquatile	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4626	790	Antarctobacter heliothermus	9154	\N	\N	\N	\N	Antarctobacter heliothermus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4627	791	Amaricoccus veronensis	9152	\N	\N	\N	\N	Amaricoccus veronensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4628	791	Amaricoccus tamworthensis	9151	\N	\N	\N	\N	Amaricoccus tamworthensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4629	791	Amaricoccus macauensis	9150	\N	\N	\N	\N	Amaricoccus macauensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4630	791	Amaricoccus kaplicensis	9149	\N	\N	\N	\N	Amaricoccus kaplicensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4631	792	Albimonas donghaensis	9147	\N	\N	\N	\N	Albimonas donghaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4632	793	Albidovulum xiamenense	9145	\N	\N	\N	\N	Albidovulum xiamenense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4633	793	Albidovulum inexpectatum	9144	\N	\N	\N	\N	Albidovulum inexpectatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4634	794	Ahrensia kielensis	9142	\N	\N	\N	\N	Ahrensia kielensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4635	795	Agaricicola taiwanensis	9140	\N	\N	\N	\N	Agaricicola taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4636	796	Vasilyevaea mishustinii	9137	\N	\N	\N	\N	Vasilyevaea mishustinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4637	796	Vasilyevaea enhydra	9136	\N	\N	\N	\N	Vasilyevaea enhydra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4638	797	Bauldia litoralis	9134	\N	\N	\N	\N	Bauldia litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4639	797	Bauldia consociata	9133	\N	\N	\N	\N	Bauldia consociata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4640	798	Amorphus orientalis	9131	\N	\N	\N	\N	Amorphus orientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4641	798	Amorphus coralli	9130	\N	\N	\N	\N	Amorphus coralli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4642	799	Sinorhizobium americanum	9127	\N	\N	\N	\N	Sinorhizobium americanum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4643	800	Shinella zoogloeoides	9125	\N	\N	\N	\N	Shinella zoogloeoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4644	800	Shinella yambaruensis	9124	\N	\N	\N	\N	Shinella yambaruensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4645	800	Shinella kummerowiae	9123	\N	\N	\N	\N	Shinella kummerowiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4646	800	Shinella granuli	9122	\N	\N	\N	\N	Shinella granuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4647	800	Shinella fusca	9121	\N	\N	\N	\N	Shinella fusca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4648	800	Shinella daejeonensis	9120	\N	\N	\N	\N	Shinella daejeonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4649	801	Rhizobium yanglingense	9118	\N	\N	\N	\N	Rhizobium yanglingense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4650	801	Rhizobium vitis	9117	\N	\N	\N	\N	Rhizobium vitis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4651	801	Rhizobium vallis	9116	\N	\N	\N	\N	Rhizobium vallis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4652	801	Rhizobium undicola	9115	\N	\N	\N	\N	Rhizobium undicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4653	801	Rhizobium tubonense	9114	\N	\N	\N	\N	Rhizobium tubonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4654	801	Rhizobium tropici	9113	\N	\N	\N	\N	Rhizobium tropici	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4655	801	Rhizobium tibeticum	9112	\N	\N	\N	\N	Rhizobium tibeticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4656	801	Rhizobium taibaishanense	9111	\N	\N	\N	\N	Rhizobium taibaishanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4657	801	Rhizobium sullae	9110	\N	\N	\N	\N	Rhizobium sullae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4658	801	Rhizobium soli	9109	\N	\N	\N	\N	Rhizobium soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4659	801	Rhizobium skierniewicense	9108	\N	\N	\N	\N	Rhizobium skierniewicense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4660	801	Rhizobium selenitireducens	9107	\N	\N	\N	\N	Rhizobium selenitireducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4661	801	Rhizobium rubi	9106	\N	\N	\N	\N	Rhizobium rubi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4662	801	Rhizobium rosettiformans	9105	\N	\N	\N	\N	Rhizobium rosettiformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4663	801	Rhizobium rhizogenes	9104	\N	\N	\N	\N	Rhizobium rhizogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4664	801	Rhizobium radiobacter	9103	\N	\N	\N	\N	Rhizobium radiobacter	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4665	801	Rhizobium pusense	9102	\N	\N	\N	\N	Rhizobium pusense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4666	801	Rhizobium pseudoryzae	9101	\N	\N	\N	\N	Rhizobium pseudoryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4667	801	Rhizobium pisi	9100	\N	\N	\N	\N	Rhizobium pisi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4668	801	Rhizobium phaseoli	9099	\N	\N	\N	\N	Rhizobium phaseoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4669	801	Rhizobium petrolearium	9098	\N	\N	\N	\N	Rhizobium petrolearium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4670	801	Rhizobium oryzae	9097	\N	\N	\N	\N	Rhizobium oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4671	801	Rhizobium multihospitium	9096	\N	\N	\N	\N	Rhizobium multihospitium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4672	801	Rhizobium mongolense	9095	\N	\N	\N	\N	Rhizobium mongolense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4673	801	Rhizobium miluonense	9094	\N	\N	\N	\N	Rhizobium miluonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4674	801	Rhizobium mesosinicum	9093	\N	\N	\N	\N	Rhizobium mesosinicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4675	801	Rhizobium lusitanum	9092	\N	\N	\N	\N	Rhizobium lusitanum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4676	801	Rhizobium lupini	9091	\N	\N	\N	\N	Rhizobium lupini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4677	801	Rhizobium loessense	9090	\N	\N	\N	\N	Rhizobium loessense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4678	801	Rhizobium leucaenae	9089	\N	\N	\N	\N	Rhizobium leucaenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4679	801	Rhizobium leguminosarum	9088	\N	\N	\N	\N	Rhizobium leguminosarum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4680	801	Rhizobium larrymoorei	9087	\N	\N	\N	\N	Rhizobium larrymoorei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4681	801	Rhizobium indigoferae	9086	\N	\N	\N	\N	Rhizobium indigoferae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4682	801	Rhizobium huautlense	9085	\N	\N	\N	\N	Rhizobium huautlense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4683	801	Rhizobium halophytocola	9084	\N	\N	\N	\N	Rhizobium halophytocola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4684	801	Rhizobium hainanense	9083	\N	\N	\N	\N	Rhizobium hainanense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4685	801	Rhizobium giardinii	9082	\N	\N	\N	\N	Rhizobium giardinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4686	801	Rhizobium gallicum	9081	\N	\N	\N	\N	Rhizobium gallicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4687	801	Rhizobium galegae	9080	\N	\N	\N	\N	Rhizobium galegae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4688	801	Rhizobium fabae	9079	\N	\N	\N	\N	Rhizobium fabae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4689	801	Rhizobium etli	9078	\N	\N	\N	\N	Rhizobium etli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4690	801	Rhizobium endophyticum	9077	\N	\N	\N	\N	Rhizobium endophyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4691	801	Rhizobium daejeonense	9076	\N	\N	\N	\N	Rhizobium daejeonense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4692	801	Rhizobium cellulosilyticum	9075	\N	\N	\N	\N	Rhizobium cellulosilyticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4693	801	Rhizobium alkalisoli	9074	\N	\N	\N	\N	Rhizobium alkalisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4694	801	Rhizobium alamii	9073	\N	\N	\N	\N	Rhizobium alamii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4695	801	Rhizobium aggregatum	9072	\N	\N	\N	\N	Rhizobium aggregatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4696	802	Kaistia terrae	9070	\N	\N	\N	\N	Kaistia terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4697	802	Kaistia soli	9069	\N	\N	\N	\N	Kaistia soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4698	802	Kaistia granuli	9068	\N	\N	\N	\N	Kaistia granuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4699	802	Kaistia geumhonensis	9067	\N	\N	\N	\N	Kaistia geumhonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4700	802	Kaistia dalseonensis	9066	\N	\N	\N	\N	Kaistia dalseonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4701	802	Kaistia adipata	9065	\N	\N	\N	\N	Kaistia adipata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4702	803	Ensifer terangae	9063	\N	\N	\N	\N	Ensifer terangae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4703	803	Ensifer sojae	9062	\N	\N	\N	\N	Ensifer sojae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4704	803	Ensifer saheli	9061	\N	\N	\N	\N	Ensifer saheli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4705	803	Ensifer numidicus	9060	\N	\N	\N	\N	Ensifer numidicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4706	803	Ensifer mexicanus	9059	\N	\N	\N	\N	Ensifer mexicanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4707	803	Ensifer meliloti	9058	\N	\N	\N	\N	Ensifer meliloti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4708	803	Ensifer medicae	9057	\N	\N	\N	\N	Ensifer medicae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4709	803	Ensifer kummerowiae	9056	\N	\N	\N	\N	Ensifer kummerowiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4710	803	Ensifer kostiensis	9055	\N	\N	\N	\N	Ensifer kostiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4711	803	Ensifer garamanticus	9054	\N	\N	\N	\N	Ensifer garamanticus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4712	803	Ensifer fredii	9053	\N	\N	\N	\N	Ensifer fredii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4713	803	Ensifer arboris	9052	\N	\N	\N	\N	Ensifer arboris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4714	803	Ensifer adhaerens	9051	\N	\N	\N	\N	Ensifer adhaerens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4715	804	Rarobacter incanus	9048	\N	\N	\N	\N	Rarobacter incanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4716	804	Rarobacter faecitabidus	9047	\N	\N	\N	\N	Rarobacter faecitabidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4717	805	Puniceicoccus vermicola	9044	\N	\N	\N	\N	Puniceicoccus vermicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4718	806	Pelagicoccus mobilis	9042	\N	\N	\N	\N	Pelagicoccus mobilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4719	806	Pelagicoccus litoralis	9041	\N	\N	\N	\N	Pelagicoccus litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4720	806	Pelagicoccus croceus	9040	\N	\N	\N	\N	Pelagicoccus croceus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4721	806	Pelagicoccus albus	9039	\N	\N	\N	\N	Pelagicoccus albus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4722	807	Coraliomargarita akajimensis	9037	\N	\N	\N	\N	Coraliomargarita akajimensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4723	808	Cerasicoccus arenae	9035	\N	\N	\N	\N	Cerasicoccus arenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4724	809	Psychromonas profunda	9032	\N	\N	\N	\N	Psychromonas profunda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4725	809	Psychromonas ossibalaenae	9031	\N	\N	\N	\N	Psychromonas ossibalaenae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4726	809	Psychromonas marina	9030	\N	\N	\N	\N	Psychromonas marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4727	809	Psychromonas macrocephali	9029	\N	\N	\N	\N	Psychromonas macrocephali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4728	809	Psychromonas kaikoae	9028	\N	\N	\N	\N	Psychromonas kaikoae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4729	809	Psychromonas japonica	9027	\N	\N	\N	\N	Psychromonas japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4730	809	Psychromonas ingrahamii	9026	\N	\N	\N	\N	Psychromonas ingrahamii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4731	809	Psychromonas heitensis	9025	\N	\N	\N	\N	Psychromonas heitensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4732	809	Psychromonas hadalis	9024	\N	\N	\N	\N	Psychromonas hadalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4733	809	Psychromonas boydii	9023	\N	\N	\N	\N	Psychromonas boydii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4734	809	Psychromonas arctica	9022	\N	\N	\N	\N	Psychromonas arctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4735	809	Psychromonas aquimarina	9021	\N	\N	\N	\N	Psychromonas aquimarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4736	809	Psychromonas antarctica	9020	\N	\N	\N	\N	Psychromonas antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4737	809	Psychromonas agarivorans	9019	\N	\N	\N	\N	Psychromonas agarivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4738	810	Yuhushiella deserti	9016	\N	\N	\N	\N	Yuhushiella deserti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4739	811	Umezawaea tangerina	9014	\N	\N	\N	\N	Umezawaea tangerina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4740	812	Thermocrispum agreste	9012	\N	\N	\N	\N	Thermocrispum agreste	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4741	813	Thermobispora bispora	9010	\N	\N	\N	\N	Thermobispora bispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4742	814	Streptoalloteichus tenebrarius	9008	\N	\N	\N	\N	Streptoalloteichus tenebrarius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4743	814	Streptoalloteichus hindustanus	9007	\N	\N	\N	\N	Streptoalloteichus hindustanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4744	815	Sciscionella marina	9005	\N	\N	\N	\N	Sciscionella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4745	816	Saccharothrix xinjiangensis	9003	\N	\N	\N	\N	Saccharothrix xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4746	816	Saccharothrix violaceirubra	9002	\N	\N	\N	\N	Saccharothrix violaceirubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4747	816	Saccharothrix variisporea	9001	\N	\N	\N	\N	Saccharothrix variisporea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4748	816	Saccharothrix texasensis	9000	\N	\N	\N	\N	Saccharothrix texasensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4749	816	Saccharothrix syringae	8999	\N	\N	\N	\N	Saccharothrix syringae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4750	816	Saccharothrix mutabilis subsp. mutabilis	8998	\N	\N	\N	\N	Saccharothrix mutabilis subsp. mutabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4751	816	Saccharothrix mutabilis subsp. capreolus	8997	\N	\N	\N	\N	Saccharothrix mutabilis subsp. capreolus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4752	816	Saccharothrix longispora	8996	\N	\N	\N	\N	Saccharothrix longispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4753	816	Saccharothrix espanaensis	8995	\N	\N	\N	\N	Saccharothrix espanaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4754	816	Saccharothrix coeruleofusca	8994	\N	\N	\N	\N	Saccharothrix coeruleofusca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4755	816	Saccharothrix algeriensis	8993	\N	\N	\N	\N	Saccharothrix algeriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4756	817	Saccharopolyspora tripterygii	8991	\N	\N	\N	\N	Saccharopolyspora tripterygii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4757	817	Saccharopolyspora thermophila	8990	\N	\N	\N	\N	Saccharopolyspora thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4758	817	Saccharopolyspora taberi	8989	\N	\N	\N	\N	Saccharopolyspora taberi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4759	817	Saccharopolyspora spinosporotrichia	8988	\N	\N	\N	\N	Saccharopolyspora spinosporotrichia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4760	817	Saccharopolyspora spinosa	8987	\N	\N	\N	\N	Saccharopolyspora spinosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4761	817	Saccharopolyspora shandongensis	8986	\N	\N	\N	\N	Saccharopolyspora shandongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4762	817	Saccharopolyspora rosea	8985	\N	\N	\N	\N	Saccharopolyspora rosea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4763	817	Saccharopolyspora rectivirgula	8984	\N	\N	\N	\N	Saccharopolyspora rectivirgula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4764	817	Saccharopolyspora qijiaojingensis	8983	\N	\N	\N	\N	Saccharopolyspora qijiaojingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4765	817	Saccharopolyspora phatthalungensis	8982	\N	\N	\N	\N	Saccharopolyspora phatthalungensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4766	817	Saccharopolyspora jiangxiensis	8981	\N	\N	\N	\N	Saccharopolyspora jiangxiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4767	817	Saccharopolyspora hordei	8980	\N	\N	\N	\N	Saccharopolyspora hordei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4768	817	Saccharopolyspora hirsuta subsp. kobensis	8979	\N	\N	\N	\N	Saccharopolyspora hirsuta subsp. kobensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4769	817	Saccharopolyspora halophila	8978	\N	\N	\N	\N	Saccharopolyspora halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4770	817	Saccharopolyspora gregorii	8977	\N	\N	\N	\N	Saccharopolyspora gregorii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4771	817	Saccharopolyspora gloriosae	8976	\N	\N	\N	\N	Saccharopolyspora gloriosae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4772	817	Saccharopolyspora flava	8975	\N	\N	\N	\N	Saccharopolyspora flava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4773	817	Saccharopolyspora erythraea	8974	\N	\N	\N	\N	Saccharopolyspora erythraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4774	817	Saccharopolyspora cebuensis	8973	\N	\N	\N	\N	Saccharopolyspora cebuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4775	817	Saccharopolyspora antimicrobica	8972	\N	\N	\N	\N	Saccharopolyspora antimicrobica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4776	818	Saccharomonospora xinjiangensis	8970	\N	\N	\N	\N	Saccharomonospora xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4777	818	Saccharomonospora viridis	8969	\N	\N	\N	\N	Saccharomonospora viridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4778	818	Saccharomonospora saliphila	8968	\N	\N	\N	\N	Saccharomonospora saliphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4779	818	Saccharomonospora paurometabolica	8967	\N	\N	\N	\N	Saccharomonospora paurometabolica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4780	818	Saccharomonospora marina	8966	\N	\N	\N	\N	Saccharomonospora marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4781	818	Saccharomonospora halophila	8965	\N	\N	\N	\N	Saccharomonospora halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4782	818	Saccharomonospora glauca	8964	\N	\N	\N	\N	Saccharomonospora glauca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4783	818	Saccharomonospora cyanea	8963	\N	\N	\N	\N	Saccharomonospora cyanea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4784	818	Saccharomonospora azurea	8962	\N	\N	\N	\N	Saccharomonospora azurea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4785	819	Pseudonocardia zijingensis	8960	\N	\N	\N	\N	Pseudonocardia zijingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4786	819	Pseudonocardia yunnanensis	8959	\N	\N	\N	\N	Pseudonocardia yunnanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4787	819	Pseudonocardia xinjiangensis	8958	\N	\N	\N	\N	Pseudonocardia xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4788	819	Pseudonocardia tropica	8957	\N	\N	\N	\N	Pseudonocardia tropica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4789	819	Pseudonocardia tetrahydrofuranoxydans	8956	\N	\N	\N	\N	Pseudonocardia tetrahydrofuranoxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4790	819	Pseudonocardia sulfidoxydans	8955	\N	\N	\N	\N	Pseudonocardia sulfidoxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4791	819	Pseudonocardia spinosispora	8954	\N	\N	\N	\N	Pseudonocardia spinosispora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4792	819	Pseudonocardia spinosa	8953	\N	\N	\N	\N	Pseudonocardia spinosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4793	819	Pseudonocardia saturnea	8952	\N	\N	\N	\N	Pseudonocardia saturnea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4794	819	Pseudonocardia petroleophila	8951	\N	\N	\N	\N	Pseudonocardia petroleophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4795	819	Pseudonocardia parietis	8950	\N	\N	\N	\N	Pseudonocardia parietis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4796	819	Pseudonocardia oroxyli	8949	\N	\N	\N	\N	Pseudonocardia oroxyli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4797	819	Pseudonocardia mongoliensis	8948	\N	\N	\N	\N	Pseudonocardia mongoliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4798	819	Pseudonocardia kunmingensis	8947	\N	\N	\N	\N	Pseudonocardia kunmingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4799	819	Pseudonocardia kongjuensis	8946	\N	\N	\N	\N	Pseudonocardia kongjuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4800	819	Pseudonocardia khuvsgulensis	8945	\N	\N	\N	\N	Pseudonocardia khuvsgulensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4801	819	Pseudonocardia hydrocarbonoxydans	8944	\N	\N	\N	\N	Pseudonocardia hydrocarbonoxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4802	819	Pseudonocardia halophobica	8943	\N	\N	\N	\N	Pseudonocardia halophobica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4803	819	Pseudonocardia eucalypti	8942	\N	\N	\N	\N	Pseudonocardia eucalypti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4804	819	Pseudonocardia endophytica	8941	\N	\N	\N	\N	Pseudonocardia endophytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4805	819	Pseudonocardia dioxanivorans	8940	\N	\N	\N	\N	Pseudonocardia dioxanivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4806	819	Pseudonocardia compacta	8939	\N	\N	\N	\N	Pseudonocardia compacta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4807	819	Pseudonocardia chloroethenivorans	8938	\N	\N	\N	\N	Pseudonocardia chloroethenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4808	819	Pseudonocardia carboxydivorans	8937	\N	\N	\N	\N	Pseudonocardia carboxydivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4809	819	Pseudonocardia benzenivorans	8936	\N	\N	\N	\N	Pseudonocardia benzenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4810	819	Pseudonocardia babensis	8935	\N	\N	\N	\N	Pseudonocardia babensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4811	819	Pseudonocardia autotrophica	8934	\N	\N	\N	\N	Pseudonocardia autotrophica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4812	819	Pseudonocardia aurantiaca	8933	\N	\N	\N	\N	Pseudonocardia aurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4813	819	Pseudonocardia asaccharolytica	8932	\N	\N	\N	\N	Pseudonocardia asaccharolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4814	819	Pseudonocardia artemisiae	8931	\N	\N	\N	\N	Pseudonocardia artemisiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4815	819	Pseudonocardia antarctica	8930	\N	\N	\N	\N	Pseudonocardia antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4816	819	Pseudonocardia ammonioxydans	8929	\N	\N	\N	\N	Pseudonocardia ammonioxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4817	819	Pseudonocardia alni	8928	\N	\N	\N	\N	Pseudonocardia alni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4818	819	Pseudonocardia alaniniphila	8927	\N	\N	\N	\N	Pseudonocardia alaniniphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4819	819	Pseudonocardia ailaonensis	8926	\N	\N	\N	\N	Pseudonocardia ailaonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4820	819	Pseudonocardia adelaidensis	8925	\N	\N	\N	\N	Pseudonocardia adelaidensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4821	819	Pseudonocardia acaciae	8924	\N	\N	\N	\N	Pseudonocardia acaciae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4822	820	Prauserella sediminis	8922	\N	\N	\N	\N	Prauserella sediminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4823	820	Prauserella rugosa	8920	\N	\N	\N	\N	Prauserella rugosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4824	820	Prauserella muralis	8919	\N	\N	\N	\N	Prauserella muralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4825	820	Prauserella marina	8918	\N	\N	\N	\N	Prauserella marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4826	820	Prauserella halophila	8917	\N	\N	\N	\N	Prauserella halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4827	820	Prauserella flava	8916	\N	\N	\N	\N	Prauserella flava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4828	820	Prauserella alba	8915	\N	\N	\N	\N	Prauserella alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4829	820	Prauserella aidingensis	8914	\N	\N	\N	\N	Prauserella aidingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4830	820	Prauserella salsuginis	8921	\N	\N	\N	\N	Prauserella salsuginis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4831	821	Lentzea waywayandensis	8912	\N	\N	\N	\N	Lentzea waywayandensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4832	821	Lentzea violacea	8911	\N	\N	\N	\N	Lentzea violacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4833	821	Lentzea flaviverrucosa	8910	\N	\N	\N	\N	Lentzea flaviverrucosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4834	821	Lentzea californiensis	8909	\N	\N	\N	\N	Lentzea californiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4835	821	Lentzea albidocapillata	8908	\N	\N	\N	\N	Lentzea albidocapillata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4836	821	Lentzea albida	8907	\N	\N	\N	\N	Lentzea albida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4837	822	Lechevalieria xinjiangensis	8905	\N	\N	\N	\N	Lechevalieria xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4838	822	Lechevalieria roselyniae	8904	\N	\N	\N	\N	Lechevalieria roselyniae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4839	822	Lechevalieria fradiae	8903	\N	\N	\N	\N	Lechevalieria fradiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4840	822	Lechevalieria flava	8902	\N	\N	\N	\N	Lechevalieria flava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4841	822	Lechevalieria atacamensis	8901	\N	\N	\N	\N	Lechevalieria atacamensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4842	822	Lechevalieria aerocolonigenes	8900	\N	\N	\N	\N	Lechevalieria aerocolonigenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4843	823	Labedaea rhizosphaerae	8898	\N	\N	\N	\N	Labedaea rhizosphaerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4844	824	Kutzneria viridogrisea	8896	\N	\N	\N	\N	Kutzneria viridogrisea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4845	824	Kutzneria kofuensis	8895	\N	\N	\N	\N	Kutzneria kofuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4846	824	Kutzneria albida	8894	\N	\N	\N	\N	Kutzneria albida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4847	825	Kibdelosporangium philippinense	8892	\N	\N	\N	\N	Kibdelosporangium philippinense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4848	825	Kibdelosporangium aridum subsp. largum	8891	\N	\N	\N	\N	Kibdelosporangium aridum subsp. largum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4849	825	Kibdelosporangium aridum subsp. aridum	8890	\N	\N	\N	\N	Kibdelosporangium aridum subsp. aridum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4850	826	Haloechinothrix alba	8888	\N	\N	\N	\N	Haloechinothrix alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4851	827	Goodfellowiella coeruleoviolacea	8886	\N	\N	\N	\N	Goodfellowiella coeruleoviolacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4852	828	Crossiella equi	8884	\N	\N	\N	\N	Crossiella equi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4853	828	Crossiella cryophila	8883	\N	\N	\N	\N	Crossiella cryophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4854	829	Amycolatopsis xylanica	8881	\N	\N	\N	\N	Amycolatopsis xylanica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4855	829	Amycolatopsis viridis	8880	\N	\N	\N	\N	Amycolatopsis viridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4856	829	Amycolatopsis vancoresmycina	8879	\N	\N	\N	\N	Amycolatopsis vancoresmycina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4857	829	Amycolatopsis ultiminotia	8878	\N	\N	\N	\N	Amycolatopsis ultiminotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4858	829	Amycolatopsis tucumanensis	8877	\N	\N	\N	\N	Amycolatopsis tucumanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4859	829	Amycolatopsis tolypomycina	8876	\N	\N	\N	\N	Amycolatopsis tolypomycina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4860	829	Amycolatopsis thermophila	8875	\N	\N	\N	\N	Amycolatopsis thermophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4861	829	Amycolatopsis thermoflava	8874	\N	\N	\N	\N	Amycolatopsis thermoflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4862	829	Amycolatopsis thailandensis	8873	\N	\N	\N	\N	Amycolatopsis thailandensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4863	829	Amycolatopsis taiwanensis	8872	\N	\N	\N	\N	Amycolatopsis taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4864	829	Amycolatopsis sulphurea	8871	\N	\N	\N	\N	Amycolatopsis sulphurea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4865	829	Amycolatopsis samaneae	8870	\N	\N	\N	\N	Amycolatopsis samaneae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4866	829	Amycolatopsis salitolerans	8869	\N	\N	\N	\N	Amycolatopsis salitolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4867	829	Amycolatopsis sacchari	8868	\N	\N	\N	\N	Amycolatopsis sacchari	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4868	829	Amycolatopsis saalfeldensis	8867	\N	\N	\N	\N	Amycolatopsis saalfeldensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4869	829	Amycolatopsis rubida	8866	\N	\N	\N	\N	Amycolatopsis rubida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4870	829	Amycolatopsis ruanii	8865	\N	\N	\N	\N	Amycolatopsis ruanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4871	829	Amycolatopsis rifamycinica	8864	\N	\N	\N	\N	Amycolatopsis rifamycinica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4872	829	Amycolatopsis regifaucium	8863	\N	\N	\N	\N	Amycolatopsis regifaucium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4873	829	Amycolatopsis plumensis	8862	\N	\N	\N	\N	Amycolatopsis plumensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4874	829	Amycolatopsis pigmentata	8861	\N	\N	\N	\N	Amycolatopsis pigmentata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4875	829	Amycolatopsis palatopharyngis	8860	\N	\N	\N	\N	Amycolatopsis palatopharyngis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4876	829	Amycolatopsis orientalis	8859	\N	\N	\N	\N	Amycolatopsis orientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4877	829	Amycolatopsis niigatensis	8858	\N	\N	\N	\N	Amycolatopsis niigatensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4878	829	Amycolatopsis nigrescens	8857	\N	\N	\N	\N	Amycolatopsis nigrescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4879	829	Amycolatopsis minnesotensis	8856	\N	\N	\N	\N	Amycolatopsis minnesotensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4880	829	Amycolatopsis methanolica	8855	\N	\N	\N	\N	Amycolatopsis methanolica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4881	829	Amycolatopsis mediterranei	8854	\N	\N	\N	\N	Amycolatopsis mediterranei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4882	829	Amycolatopsis marina	8853	\N	\N	\N	\N	Amycolatopsis marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4883	829	Amycolatopsis lurida	8852	\N	\N	\N	\N	Amycolatopsis lurida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4884	829	Amycolatopsis lexingtonensis	8851	\N	\N	\N	\N	Amycolatopsis lexingtonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4885	829	Amycolatopsis keratiniphila subsp. nogabecina	8850	\N	\N	\N	\N	Amycolatopsis keratiniphila subsp. nogabecina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4886	829	Amycolatopsis kentuckyensis	8849	\N	\N	\N	\N	Amycolatopsis kentuckyensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4887	829	Amycolatopsis jejuensis	8848	\N	\N	\N	\N	Amycolatopsis jejuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4888	829	Amycolatopsis japonica	8847	\N	\N	\N	\N	Amycolatopsis japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4889	829	Amycolatopsis hippodromi	8846	\N	\N	\N	\N	Amycolatopsis hippodromi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4890	829	Amycolatopsis helveola	8845	\N	\N	\N	\N	Amycolatopsis helveola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4891	829	Amycolatopsis halotolerans	8844	\N	\N	\N	\N	Amycolatopsis halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4892	829	Amycolatopsis halophila	8843	\N	\N	\N	\N	Amycolatopsis halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4893	829	Amycolatopsis granulosa	8842	\N	\N	\N	\N	Amycolatopsis granulosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4894	829	Amycolatopsis eurytherma	8841	\N	\N	\N	\N	Amycolatopsis eurytherma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4895	829	Amycolatopsis equina	8840	\N	\N	\N	\N	Amycolatopsis equina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4896	829	Amycolatopsis echigonensis	8839	\N	\N	\N	\N	Amycolatopsis echigonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4897	829	Amycolatopsis decaplanina	8838	\N	\N	\N	\N	Amycolatopsis decaplanina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4898	829	Amycolatopsis coloradensis	8837	\N	\N	\N	\N	Amycolatopsis coloradensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4899	829	Amycolatopsis circi	8836	\N	\N	\N	\N	Amycolatopsis circi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4900	829	Amycolatopsis benzoatilytica	8835	\N	\N	\N	\N	Amycolatopsis benzoatilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4901	829	Amycolatopsis balhimycina	8834	\N	\N	\N	\N	Amycolatopsis balhimycina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4902	829	Amycolatopsis azurea	8833	\N	\N	\N	\N	Amycolatopsis azurea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4903	829	Amycolatopsis australiensis	8832	\N	\N	\N	\N	Amycolatopsis australiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4904	829	Amycolatopsis albidoflavus	8831	\N	\N	\N	\N	Amycolatopsis albidoflavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4905	829	Amycolatopsis alba	8830	\N	\N	\N	\N	Amycolatopsis alba	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4906	830	Allokutzneria albata	8828	\N	\N	\N	\N	Allokutzneria albata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4907	831	Alloactinosynnema album	8826	\N	\N	\N	\N	Alloactinosynnema album	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4908	832	Actinosynnema pretiosum subsp. pretiosum	8824	\N	\N	\N	\N	Actinosynnema pretiosum subsp. pretiosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4909	832	Actinosynnema pretiosum subsp. auranticum	8823	\N	\N	\N	\N	Actinosynnema pretiosum subsp. auranticum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4910	832	Actinosynnema mirum	8822	\N	\N	\N	\N	Actinosynnema mirum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4911	833	Actinophytocola xinjiangensis	8820	\N	\N	\N	\N	Actinophytocola xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4912	833	Actinophytocola timorensis	8819	\N	\N	\N	\N	Actinophytocola timorensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4913	833	Actinophytocola oryzae	8818	\N	\N	\N	\N	Actinophytocola oryzae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4914	833	Actinophytocola corallina	8817	\N	\N	\N	\N	Actinophytocola corallina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4915	833	Actinophytocola burenkhanensis	8816	\N	\N	\N	\N	Actinophytocola burenkhanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4916	834	Actinomycetospora succinea	8814	\N	\N	\N	\N	Actinomycetospora succinea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4917	834	Actinomycetospora straminea	8813	\N	\N	\N	\N	Actinomycetospora straminea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4918	834	Actinomycetospora rishiriensis	8812	\N	\N	\N	\N	Actinomycetospora rishiriensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4919	834	Actinomycetospora lutea	8811	\N	\N	\N	\N	Actinomycetospora lutea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4920	834	Actinomycetospora iriomotensis	8810	\N	\N	\N	\N	Actinomycetospora iriomotensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4921	834	Actinomycetospora corticicola	8809	\N	\N	\N	\N	Actinomycetospora corticicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4922	834	Actinomycetospora cinnamomea	8808	\N	\N	\N	\N	Actinomycetospora cinnamomea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4923	834	Actinomycetospora chlora	8807	\N	\N	\N	\N	Actinomycetospora chlora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4924	834	Actinomycetospora chibensis	8806	\N	\N	\N	\N	Actinomycetospora chibensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4925	834	Actinomycetospora chiangmaiensis	8805	\N	\N	\N	\N	Actinomycetospora chiangmaiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4926	835	Actinokineospora terrae	8803	\N	\N	\N	\N	Actinokineospora terrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4927	835	Actinokineospora soli	8802	\N	\N	\N	\N	Actinokineospora soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4928	835	Actinokineospora riparia	8801	\N	\N	\N	\N	Actinokineospora riparia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4929	835	Actinokineospora inagensis	8800	\N	\N	\N	\N	Actinokineospora inagensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4930	835	Actinokineospora globicatena	8799	\N	\N	\N	\N	Actinokineospora globicatena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4931	835	Actinokineospora fastidiosa	8798	\N	\N	\N	\N	Actinokineospora fastidiosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4932	835	Actinokineospora enzanensis	8797	\N	\N	\N	\N	Actinokineospora enzanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4933	835	Actinokineospora diospyrosa	8796	\N	\N	\N	\N	Actinokineospora diospyrosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4934	835	Actinokineospora cibodasensis	8795	\N	\N	\N	\N	Actinokineospora cibodasensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4935	835	Actinokineospora cianjurensis	8794	\N	\N	\N	\N	Actinokineospora cianjurensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4936	835	Actinokineospora baliensis	8793	\N	\N	\N	\N	Actinokineospora baliensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4937	835	Actinokineospora auranticolor	8792	\N	\N	\N	\N	Actinokineospora auranticolor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4938	836	Actinoalloteichus spitiensis	8790	\N	\N	\N	\N	Actinoalloteichus spitiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4939	836	Actinoalloteichus nanshanensis	8789	\N	\N	\N	\N	Actinoalloteichus nanshanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4940	836	Actinoalloteichus hymeniacidonis	8788	\N	\N	\N	\N	Actinoalloteichus hymeniacidonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4941	836	Actinoalloteichus cyanogriseus	8787	\N	\N	\N	\N	Actinoalloteichus cyanogriseus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4942	837	Dasania marina	8784	\N	\N	\N	\N	Dasania marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4943	838	Serpens flexibilis	8781	\N	\N	\N	\N	Serpens flexibilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4944	839	Rugamonas rubra	8779	\N	\N	\N	\N	Rugamonas rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4945	840	Rhizobacter fulvus	8777	\N	\N	\N	\N	Rhizobacter fulvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4946	840	Rhizobacter dauci	8776	\N	\N	\N	\N	Rhizobacter dauci	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4947	841	Pseudomonas xinjiangensis	8774	\N	\N	\N	\N	Pseudomonas xinjiangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4948	841	Pseudomonas xiamenensis	8773	\N	\N	\N	\N	Pseudomonas xiamenensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4949	841	Pseudomonas xanthomarina	8772	\N	\N	\N	\N	Pseudomonas xanthomarina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4950	841	Pseudomonas vranovensis	8771	\N	\N	\N	\N	Pseudomonas vranovensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4951	841	Pseudomonas viridiflava	8770	\N	\N	\N	\N	Pseudomonas viridiflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4952	841	Pseudomonas veronii	8769	\N	\N	\N	\N	Pseudomonas veronii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4953	841	Pseudomonas vancouverensis	8768	\N	\N	\N	\N	Pseudomonas vancouverensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4954	841	Pseudomonas umsongensis	8767	\N	\N	\N	\N	Pseudomonas umsongensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4955	841	Pseudomonas tuomuerensis	8766	\N	\N	\N	\N	Pseudomonas tuomuerensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4956	841	Pseudomonas trivialis	8765	\N	\N	\N	\N	Pseudomonas trivialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4957	841	Pseudomonas tremae	8764	\N	\N	\N	\N	Pseudomonas tremae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4958	841	Pseudomonas toyotomiensis	8763	\N	\N	\N	\N	Pseudomonas toyotomiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4959	841	Pseudomonas tolaasii	8762	\N	\N	\N	\N	Pseudomonas tolaasii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4960	841	Pseudomonas thermotolerans	8761	\N	\N	\N	\N	Pseudomonas thermotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4961	841	Pseudomonas taiwanensis	8760	\N	\N	\N	\N	Pseudomonas taiwanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4962	841	Pseudomonas taetrolens	8759	\N	\N	\N	\N	Pseudomonas taetrolens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4963	841	Pseudomonas taeanensis	8758	\N	\N	\N	\N	Pseudomonas taeanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4964	841	Pseudomonas syringae	8757	\N	\N	\N	\N	Pseudomonas syringae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4965	841	Pseudomonas synxantha	8756	\N	\N	\N	\N	Pseudomonas synxantha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4966	841	Pseudomonas stutzeri	8755	\N	\N	\N	\N	Pseudomonas stutzeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4967	841	Pseudomonas straminea	8754	\N	\N	\N	\N	Pseudomonas straminea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4968	841	Pseudomonas segetis	8753	\N	\N	\N	\N	Pseudomonas segetis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4969	841	Pseudomonas savastanoi	8752	\N	\N	\N	\N	Pseudomonas savastanoi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4970	841	Pseudomonas saponiphila	8751	\N	\N	\N	\N	Pseudomonas saponiphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4971	841	Pseudomonas salomonii	8750	\N	\N	\N	\N	Pseudomonas salomonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4972	841	Pseudomonas sabulinigri	8749	\N	\N	\N	\N	Pseudomonas sabulinigri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4973	841	Pseudomonas rhodesiae	8748	\N	\N	\N	\N	Pseudomonas rhodesiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4974	841	Pseudomonas rhizosphaerae	8747	\N	\N	\N	\N	Pseudomonas rhizosphaerae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4975	841	Pseudomonas resinovorans	8746	\N	\N	\N	\N	Pseudomonas resinovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4976	841	Pseudomonas reinekei	8745	\N	\N	\N	\N	Pseudomonas reinekei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4977	841	Pseudomonas putida	8744	\N	\N	\N	\N	Pseudomonas putida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4978	841	Pseudomonas psychrotolerans	8743	\N	\N	\N	\N	Pseudomonas psychrotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4979	841	Pseudomonas psychrophila	8742	\N	\N	\N	\N	Pseudomonas psychrophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4980	841	Pseudomonas pseudoalcaligenes	8741	\N	\N	\N	\N	Pseudomonas pseudoalcaligenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4981	841	Pseudomonas proteolytica	8740	\N	\N	\N	\N	Pseudomonas proteolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4982	841	Pseudomonas protegens	8739	\N	\N	\N	\N	Pseudomonas protegens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4983	841	Pseudomonas pohangensis	8738	\N	\N	\N	\N	Pseudomonas pohangensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4984	841	Pseudomonas poae	8737	\N	\N	\N	\N	Pseudomonas poae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4985	841	Pseudomonas plecoglossicida	8736	\N	\N	\N	\N	Pseudomonas plecoglossicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4986	841	Pseudomonas pictorum	8735	\N	\N	\N	\N	Pseudomonas pictorum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4987	841	Pseudomonas pertucinogena	8734	\N	\N	\N	\N	Pseudomonas pertucinogena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4988	841	Pseudomonas peli	8733	\N	\N	\N	\N	Pseudomonas peli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4989	841	Pseudomonas pelagia	8732	\N	\N	\N	\N	Pseudomonas pelagia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4990	841	Pseudomonas parafulva	8731	\N	\N	\N	\N	Pseudomonas parafulva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4991	841	Pseudomonas panacis	8730	\N	\N	\N	\N	Pseudomonas panacis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4992	841	Pseudomonas palleroniana	8729	\N	\N	\N	\N	Pseudomonas palleroniana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4993	841	Pseudomonas pachastrellae	8728	\N	\N	\N	\N	Pseudomonas pachastrellae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4994	841	Pseudomonas otitidis	8727	\N	\N	\N	\N	Pseudomonas otitidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4995	841	Pseudomonas oryzihabitans	8726	\N	\N	\N	\N	Pseudomonas oryzihabitans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4996	841	Pseudomonas orientalis	8725	\N	\N	\N	\N	Pseudomonas orientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4997	841	Pseudomonas oleovorans subsp. oleovorans	8724	\N	\N	\N	\N	Pseudomonas oleovorans subsp. oleovorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4998	841	Pseudomonas oleovorans subsp. lubricantis	8723	\N	\N	\N	\N	Pseudomonas oleovorans subsp. lubricantis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
4999	841	Pseudomonas nitroreducens	8722	\N	\N	\N	\N	Pseudomonas nitroreducens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5000	841	Pseudomonas mucidolens	8721	\N	\N	\N	\N	Pseudomonas mucidolens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5001	841	Pseudomonas mosselii	8720	\N	\N	\N	\N	Pseudomonas mosselii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5002	841	Pseudomonas moraviensis	8719	\N	\N	\N	\N	Pseudomonas moraviensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5003	841	Pseudomonas moorei	8718	\N	\N	\N	\N	Pseudomonas moorei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5004	841	Pseudomonas monteilii	8717	\N	\N	\N	\N	Pseudomonas monteilii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5005	841	Pseudomonas mohnii	8716	\N	\N	\N	\N	Pseudomonas mohnii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5006	841	Pseudomonas migulae	8715	\N	\N	\N	\N	Pseudomonas migulae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5007	841	Pseudomonas meridiana	8714	\N	\N	\N	\N	Pseudomonas meridiana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5008	841	Pseudomonas mendocina	8713	\N	\N	\N	\N	Pseudomonas mendocina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5009	841	Pseudomonas mediterranea	8712	\N	\N	\N	\N	Pseudomonas mediterranea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5010	841	Pseudomonas marincola	8711	\N	\N	\N	\N	Pseudomonas marincola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5011	841	Pseudomonas marginalis	8710	\N	\N	\N	\N	Pseudomonas marginalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5012	841	Pseudomonas mandelii	8709	\N	\N	\N	\N	Pseudomonas mandelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5013	841	Pseudomonas luteola	8708	\N	\N	\N	\N	Pseudomonas luteola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5014	841	Pseudomonas lutea	8707	\N	\N	\N	\N	Pseudomonas lutea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5015	841	Pseudomonas lurida	8706	\N	\N	\N	\N	Pseudomonas lurida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5016	841	Pseudomonas lundensis	8705	\N	\N	\N	\N	Pseudomonas lundensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5017	841	Pseudomonas litoralis	8704	\N	\N	\N	\N	Pseudomonas litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5018	841	Pseudomonas lini	8703	\N	\N	\N	\N	Pseudomonas lini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5019	841	Pseudomonas libanensis	8702	\N	\N	\N	\N	Pseudomonas libanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5020	841	Pseudomonas koreensis	8701	\N	\N	\N	\N	Pseudomonas koreensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5021	841	Pseudomonas knackmussii	8700	\N	\N	\N	\N	Pseudomonas knackmussii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5022	841	Pseudomonas jinjuensis	8698	\N	\N	\N	\N	Pseudomonas jinjuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5023	841	Pseudomonas jessenii	8697	\N	\N	\N	\N	Pseudomonas jessenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5024	841	Pseudomonas japonica	8696	\N	\N	\N	\N	Pseudomonas japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5025	841	Pseudomonas indica	8695	\N	\N	\N	\N	Pseudomonas indica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5026	841	Pseudomonas hibiscicola	8694	\N	\N	\N	\N	Pseudomonas hibiscicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5027	841	Pseudomonas halophila	8693	\N	\N	\N	\N	Pseudomonas halophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5028	841	Pseudomonas guineae	8692	\N	\N	\N	\N	Pseudomonas guineae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5029	841	Pseudomonas grimontii	8691	\N	\N	\N	\N	Pseudomonas grimontii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5030	841	Pseudomonas graminis	8690	\N	\N	\N	\N	Pseudomonas graminis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5031	841	Pseudomonas gessardii	8689	\N	\N	\N	\N	Pseudomonas gessardii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5032	841	Pseudomonas geniculata	8688	\N	\N	\N	\N	Pseudomonas geniculata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5033	841	Pseudomonas fuscovaginae	8687	\N	\N	\N	\N	Pseudomonas fuscovaginae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5034	841	Pseudomonas fulva	8686	\N	\N	\N	\N	Pseudomonas fulva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5035	841	Pseudomonas frederiksbergensis	8685	\N	\N	\N	\N	Pseudomonas frederiksbergensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5036	841	Pseudomonas fragi	8684	\N	\N	\N	\N	Pseudomonas fragi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5037	841	Pseudomonas fluorescens	8683	\N	\N	\N	\N	Pseudomonas fluorescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5038	841	Pseudomonas flectens	8682	\N	\N	\N	\N	Pseudomonas flectens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5039	841	Pseudomonas flavescens	8681	\N	\N	\N	\N	Pseudomonas flavescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5040	841	Pseudomonas ficuserectae	8680	\N	\N	\N	\N	Pseudomonas ficuserectae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5041	841	Pseudomonas extremorientalis	8679	\N	\N	\N	\N	Pseudomonas extremorientalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5042	841	Pseudomonas extremaustralis	8678	\N	\N	\N	\N	Pseudomonas extremaustralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5043	841	Pseudomonas entomophila	8677	\N	\N	\N	\N	Pseudomonas entomophila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5044	841	Pseudomonas duriflava	8676	\N	\N	\N	\N	Pseudomonas duriflava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5045	841	Pseudomonas delhiensis	8675	\N	\N	\N	\N	Pseudomonas delhiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5046	841	Pseudomonas deceptionensis	8674	\N	\N	\N	\N	Pseudomonas deceptionensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5047	841	Pseudomonas cuatrocienegasensis	8673	\N	\N	\N	\N	Pseudomonas cuatrocienegasensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5048	841	Pseudomonas cremoricolorata	8672	\N	\N	\N	\N	Pseudomonas cremoricolorata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5049	841	Pseudomonas costantinii	8671	\N	\N	\N	\N	Pseudomonas costantinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5050	841	Pseudomonas corrugata	8670	\N	\N	\N	\N	Pseudomonas corrugata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5051	841	Pseudomonas congelans	8669	\N	\N	\N	\N	Pseudomonas congelans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5052	841	Pseudomonas composti	8668	\N	\N	\N	\N	Pseudomonas composti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5053	841	Pseudomonas citronellolis	8667	\N	\N	\N	\N	Pseudomonas citronellolis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5054	841	Pseudomonas cissicola	8666	\N	\N	\N	\N	Pseudomonas cissicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5055	841	Pseudomonas cichorii	8665	\N	\N	\N	\N	Pseudomonas cichorii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5056	841	Pseudomonas chlororaphis subsp. chlororaphis	8664	\N	\N	\N	\N	Pseudomonas chlororaphis subsp. chlororaphis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5057	841	Pseudomonas chlororaphis subsp. aureofaciens	8663	\N	\N	\N	\N	Pseudomonas chlororaphis subsp. aureofaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5058	841	Pseudomonas chlororaphis subsp. aurantiaca	8662	\N	\N	\N	\N	Pseudomonas chlororaphis subsp. aurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5059	841	Pseudomonas cedrina subsp. fulgida	8661	\N	\N	\N	\N	Pseudomonas cedrina subsp. fulgida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5060	841	Pseudomonas cedrina subsp. cedrina	8660	\N	\N	\N	\N	Pseudomonas cedrina subsp. cedrina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5061	841	Pseudomonas caricapapayae	8659	\N	\N	\N	\N	Pseudomonas caricapapayae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5062	841	Pseudomonas carboxydohydrogena	8658	\N	\N	\N	\N	Pseudomonas carboxydohydrogena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5063	841	Pseudomonas cannabina	8657	\N	\N	\N	\N	Pseudomonas cannabina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5064	841	Pseudomonas caeni	8656	\N	\N	\N	\N	Pseudomonas caeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5065	841	Pseudomonas brenneri	8655	\N	\N	\N	\N	Pseudomonas brenneri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5066	841	Pseudomonas brassicacearum subsp. neoaurantiaca	8654	\N	\N	\N	\N	Pseudomonas brassicacearum subsp. neoaurantiaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5067	841	Pseudomonas brassicacearum subsp. brassicacearum	8653	\N	\N	\N	\N	Pseudomonas brassicacearum subsp. brassicacearum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5068	841	Pseudomonas boreopolis	8652	\N	\N	\N	\N	Pseudomonas boreopolis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5069	841	Pseudomonas borbori	8651	\N	\N	\N	\N	Pseudomonas borbori	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5070	841	Pseudomonas beteli	8650	\N	\N	\N	\N	Pseudomonas beteli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5071	841	Pseudomonas benzenivorans	8649	\N	\N	\N	\N	Pseudomonas benzenivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5072	841	Pseudomonas bauzanensis	8648	\N	\N	\N	\N	Pseudomonas bauzanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5073	841	Pseudomonas balearica	8647	\N	\N	\N	\N	Pseudomonas balearica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5074	841	Pseudomonas baetica	8646	\N	\N	\N	\N	Pseudomonas baetica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5075	841	Pseudomonas azotoformans	8645	\N	\N	\N	\N	Pseudomonas azotoformans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5076	841	Pseudomonas azotifigens	8644	\N	\N	\N	\N	Pseudomonas azotifigens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5077	841	Pseudomonas asplenii	8643	\N	\N	\N	\N	Pseudomonas asplenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5078	841	Pseudomonas arsenicoxydans	8642	\N	\N	\N	\N	Pseudomonas arsenicoxydans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5079	841	Pseudomonas argentinensis	8641	\N	\N	\N	\N	Pseudomonas argentinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5080	841	Pseudomonas antarctica	8640	\N	\N	\N	\N	Pseudomonas antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5081	841	Pseudomonas anguilliseptica	8639	\N	\N	\N	\N	Pseudomonas anguilliseptica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5082	841	Pseudomonas amygdali	8638	\N	\N	\N	\N	Pseudomonas amygdali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5083	841	Pseudomonas alcaliphila	8637	\N	\N	\N	\N	Pseudomonas alcaliphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5084	841	Pseudomonas alcaligenes	8636	\N	\N	\N	\N	Pseudomonas alcaligenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5085	841	Pseudomonas agarici	8635	\N	\N	\N	\N	Pseudomonas agarici	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5086	841	Pseudomonas aeruginosa	8634	\N	\N	\N	\N	Pseudomonas aeruginosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5087	841	Pseudomonas abietaniphila	8633	\N	\N	\N	\N	Pseudomonas abietaniphila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5088	841	Pseudomonas kilonensis	8699	\N	\N	\N	\N	Pseudomonas kilonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5089	842	Cellvibrio vulgaris	8631	\N	\N	\N	\N	Cellvibrio vulgaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5090	842	Cellvibrio ostraviensis	8630	\N	\N	\N	\N	Cellvibrio ostraviensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5091	842	Cellvibrio mixtus subsp. mixtus	8629	\N	\N	\N	\N	Cellvibrio mixtus subsp. mixtus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5092	842	Cellvibrio japonicus	8628	\N	\N	\N	\N	Cellvibrio japonicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5093	842	Cellvibrio gandavensis	8627	\N	\N	\N	\N	Cellvibrio gandavensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5094	842	Cellvibrio fulvus	8626	\N	\N	\N	\N	Cellvibrio fulvus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5095	842	Cellvibrio fibrivorans	8625	\N	\N	\N	\N	Cellvibrio fibrivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5096	843	Azotobacter vinelandii	8623	\N	\N	\N	\N	Azotobacter vinelandii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5097	843	Azotobacter salinestris	8622	\N	\N	\N	\N	Azotobacter salinestris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5098	843	Azotobacter nigricans subsp. nigricans	8621	\N	\N	\N	\N	Azotobacter nigricans subsp. nigricans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5099	843	Azotobacter chroococcum	8620	\N	\N	\N	\N	Azotobacter chroococcum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5100	843	Azotobacter beijerinckii	8619	\N	\N	\N	\N	Azotobacter beijerinckii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5101	843	Azotobacter armeniacus	8618	\N	\N	\N	\N	Azotobacter armeniacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5102	844	Azorhizophilus paspali	8616	\N	\N	\N	\N	Azorhizophilus paspali	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5103	845	Azomonas macrocytogenes	8614	\N	\N	\N	\N	Azomonas macrocytogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5104	845	Azomonas agilis	8613	\N	\N	\N	\N	Azomonas agilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5105	846	Psychrosphaera saromensis	8610	\N	\N	\N	\N	Psychrosphaera saromensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5106	847	Pseudoalteromonas undina	8608	\N	\N	\N	\N	Pseudoalteromonas undina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5107	847	Pseudoalteromonas translucida	8607	\N	\N	\N	\N	Pseudoalteromonas translucida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5108	847	Pseudoalteromonas tetraodonis	8606	\N	\N	\N	\N	Pseudoalteromonas tetraodonis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5109	847	Pseudoalteromonas spongiae	8605	\N	\N	\N	\N	Pseudoalteromonas spongiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5110	847	Pseudoalteromonas ruthenica	8604	\N	\N	\N	\N	Pseudoalteromonas ruthenica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5111	847	Pseudoalteromonas rubra	8603	\N	\N	\N	\N	Pseudoalteromonas rubra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5112	847	Pseudoalteromonas prydzensis	8602	\N	\N	\N	\N	Pseudoalteromonas prydzensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5113	847	Pseudoalteromonas piscicida	8601	\N	\N	\N	\N	Pseudoalteromonas piscicida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5114	847	Pseudoalteromonas phenolica	8600	\N	\N	\N	\N	Pseudoalteromonas phenolica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5115	847	Pseudoalteromonas peptidolytica	8599	\N	\N	\N	\N	Pseudoalteromonas peptidolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5116	847	Pseudoalteromonas paragorgicola	8598	\N	\N	\N	\N	Pseudoalteromonas paragorgicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5117	847	Pseudoalteromonas nigrifaciens	8597	\N	\N	\N	\N	Pseudoalteromonas nigrifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5118	847	Pseudoalteromonas mariniglutinosa	8596	\N	\N	\N	\N	Pseudoalteromonas mariniglutinosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5119	847	Pseudoalteromonas marina	8595	\N	\N	\N	\N	Pseudoalteromonas marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5120	847	Pseudoalteromonas maricaloris	8594	\N	\N	\N	\N	Pseudoalteromonas maricaloris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5121	847	Pseudoalteromonas luteoviolacea	8593	\N	\N	\N	\N	Pseudoalteromonas luteoviolacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5122	847	Pseudoalteromonas lipolytica	8592	\N	\N	\N	\N	Pseudoalteromonas lipolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5123	847	Pseudoalteromonas issachenkonii	8591	\N	\N	\N	\N	Pseudoalteromonas issachenkonii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5124	847	Pseudoalteromonas haloplanktis	8590	\N	\N	\N	\N	Pseudoalteromonas haloplanktis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5125	847	Pseudoalteromonas flavipulchra	8589	\N	\N	\N	\N	Pseudoalteromonas flavipulchra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5126	847	Pseudoalteromonas espejiana	8588	\N	\N	\N	\N	Pseudoalteromonas espejiana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5127	847	Pseudoalteromonas elyakovii	8587	\N	\N	\N	\N	Pseudoalteromonas elyakovii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5128	847	Pseudoalteromonas donghaensis	8586	\N	\N	\N	\N	Pseudoalteromonas donghaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5129	847	Pseudoalteromonas distincta	8585	\N	\N	\N	\N	Pseudoalteromonas distincta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5130	847	Pseudoalteromonas citrea	8584	\N	\N	\N	\N	Pseudoalteromonas citrea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5131	847	Pseudoalteromonas carrageenovora	8583	\N	\N	\N	\N	Pseudoalteromonas carrageenovora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5132	847	Pseudoalteromonas byunsanensis	8582	\N	\N	\N	\N	Pseudoalteromonas byunsanensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5133	847	Pseudoalteromonas aurantia	8581	\N	\N	\N	\N	Pseudoalteromonas aurantia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5134	847	Pseudoalteromonas atlantica	8580	\N	\N	\N	\N	Pseudoalteromonas atlantica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5135	847	Pseudoalteromonas arctica	8579	\N	\N	\N	\N	Pseudoalteromonas arctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5136	847	Pseudoalteromonas antarctica	8578	\N	\N	\N	\N	Pseudoalteromonas antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5137	847	Pseudoalteromonas aliena	8577	\N	\N	\N	\N	Pseudoalteromonas aliena	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5138	847	Pseudoalteromonas agarivorans	8576	\N	\N	\N	\N	Pseudoalteromonas agarivorans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5139	848	Algicola sagamiensis	8574	\N	\N	\N	\N	Algicola sagamiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5140	848	Algicola bacteriolytica	8573	\N	\N	\N	\N	Algicola bacteriolytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5141	849	Synechococcales	8567	\N	\N	\N	\N	Synechococcales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5142	850	SAR11	8563	\N	\N	\N	\N	SAR11<Alphaproteobacteria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
5143	850	Rickettsiales	8359	\N	\N	\N	\N	Rickettsiales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5144	851	Tessaracoccus oleiagri	8356	\N	\N	\N	\N	Tessaracoccus oleiagri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5145	851	Tessaracoccus lubricantis	8355	\N	\N	\N	\N	Tessaracoccus lubricantis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5146	851	Tessaracoccus flavescens	8354	\N	\N	\N	\N	Tessaracoccus flavescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5147	851	Tessaracoccus bendigoensis	8353	\N	\N	\N	\N	Tessaracoccus bendigoensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5148	852	Propionimicrobium lymphophilum	8351	\N	\N	\N	\N	Propionimicrobium lymphophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5149	853	Propioniferax innocua	8349	\N	\N	\N	\N	Propioniferax innocua	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5150	854	Propionicimonas paludicola	8347	\N	\N	\N	\N	Propionicimonas paludicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5151	855	Propioniciclava tarda	8345	\N	\N	\N	\N	Propioniciclava tarda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5152	856	Propionicicella superfundia	8343	\N	\N	\N	\N	Propionicicella superfundia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5153	857	Propionibacterium thoenii	8341	\N	\N	\N	\N	Propionibacterium thoenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5154	857	Propionibacterium propionicum	8340	\N	\N	\N	\N	Propionibacterium propionicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5155	857	Propionibacterium microaerophilum	8339	\N	\N	\N	\N	Propionibacterium microaerophilum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5156	857	Propionibacterium jensenii	8338	\N	\N	\N	\N	Propionibacterium jensenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5157	857	Propionibacterium granulosum	8337	\N	\N	\N	\N	Propionibacterium granulosum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5158	857	Propionibacterium freudenreichii subsp. shermanii	8336	\N	\N	\N	\N	Propionibacterium freudenreichii subsp. shermanii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5159	857	Propionibacterium freudenreichii subsp. freudenreichii	8335	\N	\N	\N	\N	Propionibacterium freudenreichii subsp. freudenreichii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5160	857	Propionibacterium cyclohexanicum	8334	\N	\N	\N	\N	Propionibacterium cyclohexanicum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5161	857	Propionibacterium avidum	8333	\N	\N	\N	\N	Propionibacterium avidum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5162	857	Propionibacterium australiense	8332	\N	\N	\N	\N	Propionibacterium australiense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5163	857	Propionibacterium acnes	8331	\N	\N	\N	\N	Propionibacterium acnes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5164	857	Propionibacterium acidipropionici	8330	\N	\N	\N	\N	Propionibacterium acidipropionici	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5165	857	Propionibacterium acidifaciens	8329	\N	\N	\N	\N	Propionibacterium acidifaciens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5166	858	Micropruina glycogenica	8327	\N	\N	\N	\N	Micropruina glycogenica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5167	859	Microlunatus soli	8325	\N	\N	\N	\N	Microlunatus soli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5168	859	Microlunatus phosphovorus	8324	\N	\N	\N	\N	Microlunatus phosphovorus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5169	859	Microlunatus parietis	8323	\N	\N	\N	\N	Microlunatus parietis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5170	859	Microlunatus panaciterrae	8322	\N	\N	\N	\N	Microlunatus panaciterrae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5171	859	Microlunatus ginsengisoli	8321	\N	\N	\N	\N	Microlunatus ginsengisoli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5172	859	Microlunatus aurantiacus	8320	\N	\N	\N	\N	Microlunatus aurantiacus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5173	860	Luteococcus sanguinis	8318	\N	\N	\N	\N	Luteococcus sanguinis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5174	860	Luteococcus japonicus	8317	\N	\N	\N	\N	Luteococcus japonicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5175	861	Friedmanniella spumicola	8315	\N	\N	\N	\N	Friedmanniella spumicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5176	861	Friedmanniella sagamiharensis	8314	\N	\N	\N	\N	Friedmanniella sagamiharensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5177	861	Friedmanniella okinawensis	8313	\N	\N	\N	\N	Friedmanniella okinawensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5178	861	Friedmanniella luteola	8312	\N	\N	\N	\N	Friedmanniella luteola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5179	861	Friedmanniella lucida	8311	\N	\N	\N	\N	Friedmanniella lucida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5180	861	Friedmanniella lacustris	8310	\N	\N	\N	\N	Friedmanniella lacustris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5181	861	Friedmanniella capsulata	8309	\N	\N	\N	\N	Friedmanniella capsulata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5182	861	Friedmanniella antarctica	8308	\N	\N	\N	\N	Friedmanniella antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5183	862	Brooklawnia cerclae	8306	\N	\N	\N	\N	Brooklawnia cerclae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5184	863	Auraticoccus monumenti	8304	\N	\N	\N	\N	Auraticoccus monumenti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5185	864	Aestuariimicrobium kwangyangense	8302	\N	\N	\N	\N	Aestuariimicrobium kwangyangense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5186	865	Xylanimonas cellulosilytica	8299	\N	\N	\N	\N	Xylanimonas cellulosilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5187	866	Xylanimicrobium pachnodae	8297	\N	\N	\N	\N	Xylanimicrobium pachnodae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5188	867	Xylanibacterium ulmi	8295	\N	\N	\N	\N	Xylanibacterium ulmi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5189	868	Promicromonospora xylanilytica	8293	\N	\N	\N	\N	Promicromonospora xylanilytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5190	868	Promicromonospora sukumoe	8292	\N	\N	\N	\N	Promicromonospora sukumoe	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5191	868	Promicromonospora kroppenstedtii	8291	\N	\N	\N	\N	Promicromonospora kroppenstedtii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5192	868	Promicromonospora flava	8290	\N	\N	\N	\N	Promicromonospora flava	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5193	868	Promicromonospora endophytica	8289	\N	\N	\N	\N	Promicromonospora endophytica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5194	868	Promicromonospora citrea	8288	\N	\N	\N	\N	Promicromonospora citrea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5195	869	Myceligenerans xiligouense	8286	\N	\N	\N	\N	Myceligenerans xiligouense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5196	869	Myceligenerans crystallogenes	8285	\N	\N	\N	\N	Myceligenerans crystallogenes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5197	870	Isoptericola variabilis	8283	\N	\N	\N	\N	Isoptericola variabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5198	870	Isoptericola nanjingensis	8282	\N	\N	\N	\N	Isoptericola nanjingensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5199	870	Isoptericola jiangsuensis	8281	\N	\N	\N	\N	Isoptericola jiangsuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5200	870	Isoptericola hypogeus	8280	\N	\N	\N	\N	Isoptericola hypogeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5201	870	Isoptericola halotolerans	8279	\N	\N	\N	\N	Isoptericola halotolerans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5202	870	Isoptericola dokdonensis	8278	\N	\N	\N	\N	Isoptericola dokdonensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5203	870	Isoptericola chiayiensis	8277	\N	\N	\N	\N	Isoptericola chiayiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5204	871	Cellulosimicrobium terreum	8275	\N	\N	\N	\N	Cellulosimicrobium terreum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5205	871	Cellulosimicrobium funkei	8274	\N	\N	\N	\N	Cellulosimicrobium funkei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
5206	871	Cellulosimicrobium cellulans	8273	\N	\N	\N	\N	Cellulosimicrobium cellulans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
11517	2367	Arthropoda	42976	74	7891704	\N	\N	Arthropoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
12846	11517	Crustacea	46068	43726	7836241	\N	\N	Crustacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
16621	12846	Maxillopoda	48506	\N	6832368	\N	\N	Maxillopoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25828	16621	Copepoda	48519	\N	\N	\N	\N	Copepoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25829	16620	Nectiopoda	49716	\N	\N	\N	\N	Nectiopoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
12845	11517	Hexapoda	49722	\N	11439	\N	\N	Hexapoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
16630	12845	Collembola	49723	\N	34	\N	\N	Collembola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25830	16630	Symphypleona	49815	\N	\N	\N	\N	Symphypleona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25831	16630	Stemonitis	49813	\N	\N	\N	\N	Stemonitis<Collembola	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25832	16630	Pseudachorutes	49811	\N	\N	\N	\N	Pseudachorutes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25833	16630	Poduromorpha	49772	\N	\N	\N	\N	Poduromorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25834	16630	Neelipleona	49767	\N	\N	\N	\N	Neelipleona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25835	16630	Entomobryomorpha	49726	\N	\N	\N	\N	Entomobryomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25836	16630	Collembola X	49724	\N	\N	\N	\N	Collembola X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25837	16629	Projapygoidea	49868	\N	\N	\N	\N	Projapygoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25838	16629	Metajapyx	49866	\N	\N	\N	\N	Metajapyx	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25839	16629	Japygoidea	49853	\N	\N	\N	\N	Japygoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25840	16629	Campodeoidea	49835	\N	\N	\N	\N	Campodeoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25841	16628	Tridactylophagus	49886	\N	\N	\N	\N	Tridactylophagus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25842	16628	Stichotrema	49883	\N	\N	\N	\N	Stichotrema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25843	16628	Myrmecolax	49880	\N	\N	\N	\N	Myrmecolax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25844	16628	Halictophagus	49876	\N	\N	\N	\N	Halictophagus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25845	16628	Corioxenos	49874	\N	\N	\N	\N	Corioxenos	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25846	16628	Blissoxenos	49872	\N	\N	\N	\N	Blissoxenos	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25847	16627	Thysanura	65176	\N	\N	\N	\N	Thysanura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25848	16627	Pterygota X	64327	\N	\N	\N	\N	Pterygota X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25849	16627	Pterygota	53866	\N	\N	\N	\N	Pterygota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25850	16627	Nemopalpus	52837	\N	\N	\N	\N	Nemopalpus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25851	16627	Monocondylia	52709	\N	\N	\N	\N	Monocondylia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25852	16627	Insecta X	52061	\N	\N	\N	\N	Insecta X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25853	16626	Sinentomata	65619	\N	\N	\N	\N	Sinentomata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25854	16626	Eosentomata	65612	\N	\N	\N	\N	Eosentomata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25855	16626	Acerentomon	65610	\N	\N	\N	\N	Acerentomon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25856	16626	Acerentomata	65597	\N	\N	\N	\N	Acerentomata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25857	16634	Pleurostigmophora	65667	\N	\N	\N	\N	Pleurostigmophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25858	16634	Notostigmophora	65628	\N	\N	\N	\N	Notostigmophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25859	25857	Himantarium	65626	\N	\N	\N	\N	Himantarium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25860	16633	Thyropisthus	65983	\N	\N	\N	\N	Thyropisthus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25861	16633	Penicillata	65975	\N	\N	\N	\N	Penicillata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25862	16633	Megaphyllum	65973	\N	\N	\N	\N	Megaphyllum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25863	16633	Helminthomorpha	65845	\N	\N	\N	\N	Helminthomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25864	16633	Glomeris	65843	\N	\N	\N	\N	Glomeris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25865	16633	Diplopoda X	65841	\N	\N	\N	\N	Diplopoda X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25866	16633	Atopetholus	65839	\N	\N	\N	\N	Atopetholus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25867	16632	Pauropodidae	65989	\N	\N	\N	\N	Pauropodidae<Pauropoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25868	16632	Incertae Sedis Pauropoda	65986	\N	\N	\N	\N	Incertae Sedis Pauropoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25869	16631	Symphylella	65999	\N	\N	\N	\N	Symphylella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25870	16631	Scutigerella	65997	\N	\N	\N	\N	Scutigerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25871	16631	Hanseniella	65995	\N	\N	\N	\N	Hanseniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25872	16635	Craniida	66004	\N	\N	\N	\N	Craniida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25873	16636	Lingulida	66014	\N	\N	\N	\N	Lingulida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25874	16637	Phoronopsis harmeri	66029	\N	\N	\N	\N	Phoronopsis harmeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25875	16637	Phoronopsis californica	66028	\N	\N	\N	\N	Phoronopsis californica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25876	16639	Environmental Rhynchonelliformea 1 sp.	66032	\N	\N	\N	\N	Environmental Rhynchonelliformea 1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25877	16638	Thecideida	66127	\N	\N	\N	\N	Thecideida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25878	16638	Terebratulidina	66061	\N	\N	\N	\N	Terebratulidina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25879	16638	Rhynchonellida	66037	\N	\N	\N	\N	Rhynchonellida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25880	16638	Incertae Sedis Terebratulida	66034	\N	\N	\N	\N	Incertae Sedis Terebratulida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25881	16640	Gelatinella	66150	\N	\N	\N	\N	Gelatinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25882	16640	Cristatella	66148	\N	\N	\N	\N	Cristatella<Bryozoa XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25883	16640	Crisidia	66146	\N	\N	\N	\N	Crisidia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25884	16640	Bryozoa XXX	66144	\N	\N	\N	\N	Bryozoa XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25885	16642	Neocheilostomatina	66186	\N	\N	\N	\N	Neocheilostomatina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25886	16642	Malacostegina	66168	\N	\N	\N	\N	Malacostegina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25887	16642	Inovicellina	66165	\N	\N	\N	\N	Inovicellina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25888	16642	Anasca	66154	\N	\N	\N	\N	Anasca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25889	16641	Walkeriidae	66327	\N	\N	\N	\N	Walkeriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25890	16641	Vesiculariidae	66322	\N	\N	\N	\N	Vesiculariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25891	16641	Triticellidae	66318	\N	\N	\N	\N	Triticellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25892	16641	Paludicellidae	66315	\N	\N	\N	\N	Paludicellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25893	16641	Nolellidae	66312	\N	\N	\N	\N	Nolellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25894	16641	Flustrellidridae	66307	\N	\N	\N	\N	Flustrellidridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25895	16641	Alcyonidiidae	66301	\N	\N	\N	\N	Alcyonidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25896	16646	Cristatella	66332	\N	\N	\N	\N	Cristatella<Cristatellidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25897	16645	Lophopus	66339	\N	\N	\N	\N	Lophopus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25898	16645	Fredericella	66337	\N	\N	\N	\N	Fredericella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25899	16645	Asajirella	66335	\N	\N	\N	\N	Asajirella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25900	16644	Pectinatella	66342	\N	\N	\N	\N	Pectinatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25901	16643	Stephanella	66359	\N	\N	\N	\N	Stephanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25902	16643	Plumatella	66347	\N	\N	\N	\N	Plumatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25903	16643	Hyalinella	66345	\N	\N	\N	\N	Hyalinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25904	16648	Tretocycloeciidae	66410	\N	\N	\N	\N	Tretocycloeciidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25905	16648	Plagioeciidae	66407	\N	\N	\N	\N	Plagioeciidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25906	16648	Lichenoporidae	66400	\N	\N	\N	\N	Lichenoporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25907	16648	Horneridae	66395	\N	\N	\N	\N	Horneridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25908	16648	Heteroporidae	66392	\N	\N	\N	\N	Heteroporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25909	16648	Frondiporidae	66389	\N	\N	\N	\N	Frondiporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25910	16648	Diastoporidae	66384	\N	\N	\N	\N	Diastoporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25911	16648	Densiporidae	66381	\N	\N	\N	\N	Densiporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25912	16648	Crisiidae	66371	\N	\N	\N	\N	Crisiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25913	16648	Cinctiporidae	66368	\N	\N	\N	\N	Cinctiporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25914	16648	Annectocymidae	66363	\N	\N	\N	\N	Annectocymidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25915	16647	Tubuliporidae	66414	\N	\N	\N	\N	Tubuliporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25916	16651	Serratosagitta	66428	\N	\N	\N	\N	Serratosagitta<Aphragmophora X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25917	16651	Aphragmophora XX	66426	\N	\N	\N	\N	Aphragmophora XX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25918	12859	Sagittidae	66434	\N	\N	\N	\N	Sagittidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25919	12859	Pterosagittidae	66431	\N	\N	\N	\N	Pterosagittidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25920	16649	Krohnittidae	66452	\N	\N	\N	\N	Krohnittidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25921	16652	Xenokrohnia	66457	\N	\N	\N	\N	Xenokrohnia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25922	16654	Eukrohnia	66461	\N	\N	\N	\N	Eukrohnia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25923	16653	Spadella	66468	\N	\N	\N	\N	Spadella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25924	16653	Paraspadella	66466	\N	\N	\N	\N	Paraspadella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25925	16655	Branchiostoma	66475	\N	\N	\N	\N	Branchiostoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25926	16658	Craniata X sp.	66534	\N	\N	\N	\N	Craniata X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25927	16657	Myxiniformes	66651	\N	\N	\N	\N	Myxiniformes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25928	16656	Gnathostomata	87191	\N	\N	\N	\N	Gnathostomata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25929	16656	Hyperoartia	67283	\N	\N	\N	\N	Hyperoartia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25930	85123	Fritillariidae	87045	\N	\N	\N	\N	Fritillariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25931	85123	Appendicularia X	86793	\N	\N	\N	\N	Appendicularia X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25932	85123	Oikopleuridae	67603	\N	\N	\N	\N	Oikopleuridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25933	16660	Stolonica	67768	\N	\N	\N	\N	Stolonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25934	16660	Stolidobranchia	67694	\N	\N	\N	\N	Stolidobranchia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25935	16660	Saccharomyces	67692	\N	\N	\N	\N	Saccharomyces<Ascidiacea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25936	16660	Polyandrocarpa	67690	\N	\N	\N	\N	Polyandrocarpa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25937	16660	Homo	67686	\N	\N	\N	\N	Homo<Ascidiacea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25938	16660	Eugyra	67684	\N	\N	\N	\N	Eugyra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25939	16660	Enterogona	67616	\N	\N	\N	\N	Enterogona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25940	16660	Dendrodoa	67613	\N	\N	\N	\N	Dendrodoa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25941	16660	Bostrichobranchus	67611	\N	\N	\N	\N	Bostrichobranchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25942	16659	Salpida	67783	\N	\N	\N	\N	Salpida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25943	16659	Pyrosomatida	67775	\N	\N	\N	\N	Pyrosomatida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25944	16659	Doliolida	67771	\N	\N	\N	\N	Doliolida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25945	16664	Environmental Anthozoa 1	67818	\N	\N	\N	\N	Environmental Anthozoa 1<Environmental Anthozoa 1<Anthozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25946	16663	Zoantharia	68525	\N	\N	\N	\N	Zoantharia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25947	16663	Scleractinia	68125	\N	\N	\N	\N	Scleractinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25948	16663	Corallimorpharia	68102	\N	\N	\N	\N	Corallimorpharia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25949	16663	Ceriantharia	68095	\N	\N	\N	\N	Ceriantharia<Hexacorallia	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25950	16663	Antipatharia	68054	\N	\N	\N	\N	Antipatharia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25951	16663	Actiniaria	67822	\N	\N	\N	\N	Actiniaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25952	16662	Telestacea	68758	\N	\N	\N	\N	Telestacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25953	16662	Pennatulacea	68737	\N	\N	\N	\N	Pennatulacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25954	16662	Helioporacea	68733	\N	\N	\N	\N	Helioporacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25955	16662	Alcyonacea	68571	\N	\N	\N	\N	Alcyonacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25956	16666	Trichogorgia	68802	\N	\N	\N	\N	Trichogorgia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25957	16666	Titanideum	68800	\N	\N	\N	\N	Titanideum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25958	16666	Swiftia	68798	\N	\N	\N	\N	Swiftia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25959	16666	Stephanogorgia	68796	\N	\N	\N	\N	Stephanogorgia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25960	16666	Rhodaniridogorgia	68793	\N	\N	\N	\N	Rhodaniridogorgia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25961	16666	Pleurogorgia	68791	\N	\N	\N	\N	Pleurogorgia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25962	16666	Phanopathes	68789	\N	\N	\N	\N	Phanopathes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25963	16666	Nynantheae	68787	\N	\N	\N	\N	Nynantheae<Anthozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25964	16666	Isidoides	68785	\N	\N	\N	\N	Isidoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25965	16666	Hormathiidae	68783	\N	\N	\N	\N	Hormathiidae<Anthozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25966	16666	Helicogorgia	68781	\N	\N	\N	\N	Helicogorgia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25967	16666	Funiculina	68779	\N	\N	\N	\N	Funiculina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25968	16666	Didemnum	68777	\N	\N	\N	\N	Didemnum<Anthozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25969	16666	Bartholomea	68775	\N	\N	\N	\N	Bartholomea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25970	16666	Balanus	68773	\N	\N	\N	\N	Balanus<Anthozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25971	16666	Anthozoa X	68771	\N	\N	\N	\N	Anthozoa X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25972	16666	Anthothoe	68769	\N	\N	\N	\N	Anthothoe	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25973	16666	Acanella	68767	\N	\N	\N	\N	Acanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25974	16665	Cnidaria XXX	68805	\N	\N	\N	\N	Cnidaria XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25975	16668	Tripedaliidae	68834	\N	\N	\N	\N	Tripedaliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25976	16668	Tamoyidae	68830	\N	\N	\N	\N	Tamoyidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25977	16668	Carybdeidae	68819	\N	\N	\N	\N	Carybdeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25978	16668	Carukiidae	68812	\N	\N	\N	\N	Carukiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25979	16668	Alatinidae	68809	\N	\N	\N	\N	Alatinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25980	16667	Chiropsalmidae	68846	\N	\N	\N	\N	Chiropsalmidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25981	16667	Chirodropidae	68840	\N	\N	\N	\N	Chirodropidae<Chirodropida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25982	16682	Branchiocerianthus imperator	68852	\N	\N	\N	\N	Branchiocerianthus imperator	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25983	16681	Clausophyid sp.	68854	\N	\N	\N	\N	Clausophyid sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25984	16680	Cnidaria sp.	68856	\N	\N	\N	\N	Cnidaria sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25985	16679	Environmental Hydrozoa 1	68858	\N	\N	\N	\N	Environmental Hydrozoa 1<Environmental Hydrozoa 1<Hydrozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25986	16678	Halammohydra sp.	68862	\N	\N	\N	\N	Halammohydra sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25987	16677	Hataia parva	68864	\N	\N	\N	\N	Hataia parva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25988	16676	Helgicirrha malayensis	68867	\N	\N	\N	\N	Helgicirrha malayensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25989	16676	Helgicirrha brevistyla	68866	\N	\N	\N	\N	Helgicirrha brevistyla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25990	16675	Siphonophorae	69363	\N	\N	\N	\N	Siphonophorae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25991	16675	Leptothecata	69153	\N	\N	\N	\N	Leptothecata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25992	16675	Anthoathecata	68869	\N	\N	\N	\N	Anthoathecata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25993	16674	Hydrozoa X sp.	69469	\N	\N	\N	\N	Hydrozoa X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25994	16673	marine metagenome	69471	\N	\N	\N	\N	marine metagenome<marine<Hydrozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
25995	16672	Physonect sp.	69473	\N	\N	\N	\N	Physonect sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25996	16671	Sympagohydra tuuli	69475	\N	\N	\N	\N	Sympagohydra tuuli	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25997	16670	Limnomedusae	69477	\N	\N	\N	\N	Limnomedusae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25998	16669	Trachymedusae	69514	\N	\N	\N	\N	Trachymedusae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
25999	16669	Narcomedusae	69497	\N	\N	\N	\N	Narcomedusae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26000	16685	Malacovalvulida	69541	\N	\N	\N	\N	Malacovalvulida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26001	16684	Tetraspora	69979	\N	\N	\N	\N	Tetraspora<Myxosporea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26002	16684	Sphaeractinomyxon	69977	\N	\N	\N	\N	Sphaeractinomyxon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26003	16684	Soricimyxum	69975	\N	\N	\N	\N	Soricimyxum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26004	16684	proliferative	69973	\N	\N	\N	\N	proliferative	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26005	16684	Myxosporea X	69971	\N	\N	\N	\N	Myxosporea X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26006	16684	Myxosporea	69969	\N	\N	\N	\N	Myxosporea<Myxosporea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26007	16684	Myxosporea incertae sedis	69966	\N	\N	\N	\N	Myxosporea incertae sedis<Myxosporea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26008	16684	Multivalvulida	69907	\N	\N	\N	\N	Multivalvulida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26009	16684	Leptotheca	69905	\N	\N	\N	\N	Leptotheca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26010	16684	Hungactinomyxon	69891	\N	\N	\N	\N	Hungactinomyxon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26011	16684	Hoferellus	69889	\N	\N	\N	\N	Hoferellus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26012	16684	Hennegoides	69887	\N	\N	\N	\N	Hennegoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26013	16684	Guyenotia	69885	\N	\N	\N	\N	Guyenotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26014	16684	Enteromyxum	69881	\N	\N	\N	\N	Enteromyxum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26015	16684	Echinactinomyxon	69878	\N	\N	\N	\N	Echinactinomyxon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26016	16684	Cytodiscus	69876	\N	\N	\N	\N	Cytodiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26017	16684	Bivalvulida	69570	\N	\N	\N	\N	Bivalvulida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26018	16684	Bipteria	69568	\N	\N	\N	\N	Bipteria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26019	16684	Actinomyxida	69551	\N	\N	\N	\N	Actinomyxida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26020	16684	Acauda	69549	\N	\N	\N	\N	Acauda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26021	16683	Synactinomyxon	69901	\N	\N	\N	\N	Synactinomyxon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26022	16683	Incertae Sedis Myxosporea	69897	\N	\N	\N	\N	Incertae Sedis Myxosporea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26023	16683	Endocapsa	69894	\N	\N	\N	\N	Endocapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26024	16690	Periphyllidae	70005	\N	\N	\N	\N	Periphyllidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26025	16690	Paraphyllinidae	70002	\N	\N	\N	\N	Paraphyllinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26026	16690	Nausithoidae	69997	\N	\N	\N	\N	Nausithoidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26027	16690	Linuchidae	69993	\N	\N	\N	\N	Linuchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26028	16690	Atorellidae	69988	\N	\N	\N	\N	Atorellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26029	16690	Atollidae	69983	\N	\N	\N	\N	Atollidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26030	16689	unclassified Rhizostomeae	70060	\N	\N	\N	\N	unclassified Rhizostomeae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26031	16689	Thysanostomatidae	70057	\N	\N	\N	\N	Thysanostomatidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26032	16689	Rhizostomatidae	70046	\N	\N	\N	\N	Rhizostomatidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26033	16689	Mastigiidae	70039	\N	\N	\N	\N	Mastigiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26034	16689	Lychnorhizidae	70034	\N	\N	\N	\N	Lychnorhizidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26035	16689	Lobonematidae	70031	\N	\N	\N	\N	Lobonematidae<Rhizostomeae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26036	16689	Cepheidae	70026	\N	\N	\N	\N	Cepheidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26037	16689	Catostylidae	70016	\N	\N	\N	\N	Catostylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26038	16689	Cassiopeidae	70009	\N	\N	\N	\N	Cassiopeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26039	16688	Scyphozoa X sp.	70063	\N	\N	\N	\N	Scyphozoa X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26040	16687	Ulmaridae	70089	\N	\N	\N	\N	Ulmaridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26041	16687	Pelagiidae	70077	\N	\N	\N	\N	Pelagiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26042	16687	Drymonematidae	70072	\N	\N	\N	\N	Drymonematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26043	16687	Cyaneidae	70065	\N	\N	\N	\N	Cyaneidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26044	16686	Lucernariidae	70106	\N	\N	\N	\N	Lucernariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26045	16686	Depastridae	70103	\N	\N	\N	\N	Depastridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26046	16686	Cleistocarpidae	70100	\N	\N	\N	\N	Cleistocarpidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26047	16691	Lampocteis	70122	\N	\N	\N	\N	Lampocteis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26048	16691	Ctenophora XXX	70119	\N	\N	\N	\N	Ctenophora XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26049	16691	Ctenophora	70117	\N	\N	\N	\N	Ctenophora<Ctenophora XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26050	16695	Beroidae	70126	\N	\N	\N	\N	Beroidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26051	16694	Cestidae	70134	\N	\N	\N	\N	Cestidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26052	16693	Ocyropsidae	70151	\N	\N	\N	\N	Ocyropsidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26053	16693	Leucotheidae	70148	\N	\N	\N	\N	Leucotheidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26054	16693	Environmental Lobata 1	70145	\N	\N	\N	\N	Environmental Lobata 1<Lobata	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26055	16693	Bolinopsidae	70140	\N	\N	\N	\N	Bolinopsidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26056	16692	Thalassocalycidae	70157	\N	\N	\N	\N	Thalassocalycidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26057	16698	Pleurobrachiidae	70176	\N	\N	\N	\N	Pleurobrachiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26058	16698	Mertensiidae	70169	\N	\N	\N	\N	Mertensiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26059	16698	Haeckeliidae	70165	\N	\N	\N	\N	Haeckeliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26060	16698	Euplokamidae	70162	\N	\N	\N	\N	Euplokamidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26061	16697	Environmental Typhlocoela 1	70184	\N	\N	\N	\N	Environmental Typhlocoela 1<Environmental Typhlocoela 1<Typhlocoela	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26062	16696	Coeloplanidae	70188	\N	\N	\N	\N	Coeloplanidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26063	16699	Symbion	70199	\N	\N	\N	\N	Symbion<Symbion<Symbion<Cycliophora	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26064	16702	Guillecrinidae	70222	\N	\N	\N	\N	Guillecrinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26065	16702	Comasteridae	70219	\N	\N	\N	\N	Comasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26066	16702	Bathycrinidae	70214	\N	\N	\N	\N	Bathycrinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26067	16702	Antedonoidea	70210	\N	\N	\N	\N	Antedonoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26068	16702	Antedonidae	70207	\N	\N	\N	\N	Antedonidae<Comatulida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26069	16701	Sclerocrinidae	70229	\N	\N	\N	\N	Sclerocrinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26070	16701	Holopodidae	70226	\N	\N	\N	\N	Holopodidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26071	16700	Isselicrinidae	70233	\N	\N	\N	\N	Isselicrinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26072	16709	Asteroidea	70242	\N	\N	\N	\N	Asteroidea<Asteroidea<Asteroidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26073	16708	Brisingidae	70246	\N	\N	\N	\N	Brisingidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26074	16707	Stichasteridae	70275	\N	\N	\N	\N	Stichasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26075	16707	Heliasteridae	70271	\N	\N	\N	\N	Heliasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26076	16707	Asteriidae	70250	\N	\N	\N	\N	Asteriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26077	16706	Pseudarchasteridae	70294	\N	\N	\N	\N	Pseudarchasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26078	16706	Luidiidae	70289	\N	\N	\N	\N	Luidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26079	16706	Astropectinidae	70281	\N	\N	\N	\N	Astropectinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26080	16705	Echinasteridae	70298	\N	\N	\N	\N	Echinasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26081	16704	Solasteridae	70357	\N	\N	\N	\N	Solasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26082	16704	Poraniidae	70354	\N	\N	\N	\N	Poraniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26083	16704	Ophidiasteridae	70347	\N	\N	\N	\N	Ophidiasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26084	16704	Odontasteridae	70336	\N	\N	\N	\N	Odontasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26085	16704	Goniasteridae	70333	\N	\N	\N	\N	Goniasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26086	16704	Ganeriidae	70330	\N	\N	\N	\N	Ganeriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26087	16704	Asteropseidae	70327	\N	\N	\N	\N	Asteropseidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26088	16704	Asterinidae	70313	\N	\N	\N	\N	Asterinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26089	16704	Archasteridae	70309	\N	\N	\N	\N	Archasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26090	16704	Acanthasteridae	70306	\N	\N	\N	\N	Acanthasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26091	16703	Pterasteridae	70364	\N	\N	\N	\N	Pterasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26092	16710	Xyloplax	70515	\N	\N	\N	\N	Xyloplax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26093	16710	Urasterias	70513	\N	\N	\N	\N	Urasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26094	16710	Trichaster	70510	\N	\N	\N	\N	Trichaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26095	16710	Tarsaster	70508	\N	\N	\N	\N	Tarsaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26096	16710	Stylasterias	70506	\N	\N	\N	\N	Stylasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26097	16710	Sthenocephalus	70504	\N	\N	\N	\N	Sthenocephalus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26098	16710	Stephanasterias	70502	\N	\N	\N	\N	Stephanasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26099	26191	Squamophis	70500	\N	\N	\N	\N	Squamophis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26100	16710	Pycnopodia	70498	\N	\N	\N	\N	Pycnopodia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26101	16710	Psalidaster	70496	\N	\N	\N	\N	Psalidaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26102	16710	Promachocrinus	70494	\N	\N	\N	\N	Promachocrinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26103	16710	Phanogenia	70492	\N	\N	\N	\N	Phanogenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26104	16710	Pedicellaster	70490	\N	\N	\N	\N	Pedicellaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26105	16710	Oxycomanthus	70487	\N	\N	\N	\N	Oxycomanthus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26106	16710	Orthasterias	70485	\N	\N	\N	\N	Orthasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26107	16710	Ophiomoeris	70483	\N	\N	\N	\N	Ophiomoeris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26108	16710	Ophiocrene	70481	\N	\N	\N	\N	Ophiocrene	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26109	88764	Ophiocreas	70476	\N	\N	\N	\N	Ophiocreas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26110	16710	Ophiocomina	70474	\N	\N	\N	\N	Ophiocomina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26111	16710	Odinella	70472	\N	\N	\N	\N	Odinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26112	16710	Notasterias	70470	\N	\N	\N	\N	Notasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26113	16710	Marthasterias	70468	\N	\N	\N	\N	Marthasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26114	16710	Liparometra	70466	\N	\N	\N	\N	Liparometra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26115	16710	Lethasterias	70464	\N	\N	\N	\N	Lethasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26116	16710	Leptasterias	70458	\N	\N	\N	\N	Leptasterias	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26117	16710	Labidiaster	70456	\N	\N	\N	\N	Labidiaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26118	16710	Himerometra	70453	\N	\N	\N	\N	Himerometra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26119	26191	Euryale	70451	\N	\N	\N	\N	Euryale<Euryalidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26120	16710	Echinodermata XXX	70449	\N	\N	\N	\N	Echinodermata XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26121	16710	Coronaster	70447	\N	\N	\N	\N	Coronaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26122	88734	Comanthus	70445	\N	\N	\N	\N	Comanthus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26123	16710	Comanthina	70443	\N	\N	\N	\N	Comanthina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26124	16710	Colobometra	70441	\N	\N	\N	\N	Colobometra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26125	16710	Clarkcomanthus	70438	\N	\N	\N	\N	Clarkcomanthus<Echinodermata XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26126	16710	Capillaster	70436	\N	\N	\N	\N	Capillaster<Echinodermata XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26127	16710	Astrothrombus	70432	\N	\N	\N	\N	Astrothrombus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26128	16710	Astrothorax	70429	\N	\N	\N	\N	Astrothorax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26129	16710	Astrothamnus	70427	\N	\N	\N	\N	Astrothamnus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26130	16710	Astrosierra	70425	\N	\N	\N	\N	Astrosierra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26131	16710	Astrophyton	70423	\N	\N	\N	\N	Astrophyton	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26132	16710	Astrometis	70421	\N	\N	\N	\N	Astrometis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26133	16710	Astrohamma	70419	\N	\N	\N	\N	Astrohamma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26134	16710	Astrogymnotes	70417	\N	\N	\N	\N	Astrogymnotes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26135	16710	Astroglymma	70415	\N	\N	\N	\N	Astroglymma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26136	16710	Astrodia	70413	\N	\N	\N	\N	Astrodia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26137	16710	Astrodendrum	70410	\N	\N	\N	\N	Astrodendrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26138	16710	Astrocrius	70408	\N	\N	\N	\N	Astrocrius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26139	16710	Astroclon	70406	\N	\N	\N	\N	Astroclon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26140	26190	Astrocladus	70403	\N	\N	\N	\N	Astrocladus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26141	16710	Astrochele	70401	\N	\N	\N	\N	Astrochele	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26142	16710	Astrocharis	70399	\N	\N	\N	\N	Astrocharis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26143	26191	Astroceras	70393	\N	\N	\N	\N	Astroceras	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26144	16710	Astrobrachion	70391	\N	\N	\N	\N	Astrobrachion<Echinodermata XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26145	26190	Astroboa	70387	\N	\N	\N	\N	Astroboa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26146	16710	Asteroporpa	70383	\N	\N	\N	\N	Asteroporpa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26147	26191	Asteromorpha	70381	\N	\N	\N	\N	Asteromorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26148	26199	Amphiura	70378	\N	\N	\N	\N	Amphiura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26149	26199	Acrocnida	70376	\N	\N	\N	\N	Acrocnida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26150	88741	Acaudina	70374	\N	\N	\N	\N	Acaudina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26151	16725	Arbaciidae	70523	\N	\N	\N	\N	Arbaciidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26152	16725	Arbaciida	70519	\N	\N	\N	\N	Arbaciida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26153	16724	Aspidodiadematidae	70527	\N	\N	\N	\N	Aspidodiadematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26154	16723	Trigonocidaridae	70578	\N	\N	\N	\N	Trigonocidaridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26155	16723	Toxopneustidae	70569	\N	\N	\N	\N	Toxopneustidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26156	16723	Temnopleuridae	70543	\N	\N	\N	\N	Temnopleuridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26157	16723	Strongylocentrotidae	70539	\N	\N	\N	\N	Strongylocentrotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26158	16723	Parechinidae	70534	\N	\N	\N	\N	Parechinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26159	16723	Echinometridae	70531	\N	\N	\N	\N	Echinometridae<Camarodonta	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26160	16722	Echinometridae	70582	\N	\N	\N	\N	Echinometridae<Camarotonda	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26161	16721	Cassidulidae	70586	\N	\N	\N	\N	Cassidulidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26162	16720	Cidaridae	70590	\N	\N	\N	\N	Cidaridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26163	16719	Scutellidea	70612	\N	\N	\N	\N	Scutellidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26164	16719	Mellitidae	70609	\N	\N	\N	\N	Mellitidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26165	16719	Laganidae	70606	\N	\N	\N	\N	Laganidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26166	16719	Echinocyamidae	70603	\N	\N	\N	\N	Echinocyamidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26167	16719	Clypeasteridae	70600	\N	\N	\N	\N	Clypeasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26168	16718	Diadematidae	70616	\N	\N	\N	\N	Diadematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26169	16717	Echinolampadidae	70623	\N	\N	\N	\N	Echinolampadidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26170	16716	Echinoneidae	70631	\N	\N	\N	\N	Echinoneidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26171	16715	Echinothuriidae	70635	\N	\N	\N	\N	Echinothuriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26172	16714	Plexechinidae	70641	\N	\N	\N	\N	Plexechinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26173	16713	Pedinidae	70645	\N	\N	\N	\N	Pedinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26174	16712	Spatangidae	70666	\N	\N	\N	\N	Spatangidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26175	16712	Schizasteridae	70663	\N	\N	\N	\N	Schizasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26176	16712	Paleopneustina incertae sedis B	70660	\N	\N	\N	\N	Paleopneustina incertae sedis B	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26177	16712	Paleopneustidea	70657	\N	\N	\N	\N	Paleopneustidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26178	16712	Loveniidae	70654	\N	\N	\N	\N	Loveniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26179	16712	Brissidae	70649	\N	\N	\N	\N	Brissidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26180	16711	Stomopneustidae	70670	\N	\N	\N	\N	Stomopneustidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26181	16729	Synaptidae	70680	\N	\N	\N	\N	Synaptidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26182	16729	Chiridotidae	70675	\N	\N	\N	\N	Chiridotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26183	16728	Synallactidae	70705	\N	\N	\N	\N	Synallactidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26184	16728	Stichopodidae	70700	\N	\N	\N	\N	Stichopodidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26185	16728	Holothuriidae	70687	\N	\N	\N	\N	Holothuriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26186	16727	Sclerodactylidae	70726	\N	\N	\N	\N	Sclerodactylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26187	16727	Phyllophoridae	70721	\N	\N	\N	\N	Phyllophoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26188	16727	Cucumariidae	70709	\N	\N	\N	\N	Cucumariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26189	16726	Psychropotidae	70730	\N	\N	\N	\N	Psychropotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26190	16731	Gorgonocephalidae	70742	\N	\N	\N	\N	Gorgonocephalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26191	16731	Euryalidae	70739	\N	\N	\N	\N	Euryalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26192	16731	Asteronychidae	70735	\N	\N	\N	\N	Asteronychidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26193	16730	Ophiotrichidae	70776	\N	\N	\N	\N	Ophiotrichidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26194	16730	Ophiomyxidae	70769	\N	\N	\N	\N	Ophiomyxidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26195	16730	Ophiolepididae	70766	\N	\N	\N	\N	Ophiolepididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26196	16730	Ophiodermatidae	70758	\N	\N	\N	\N	Ophiodermatidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26197	16730	Ophiocomidae	70755	\N	\N	\N	\N	Ophiocomidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26198	16730	Ophiactidae	70752	\N	\N	\N	\N	Ophiactidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26199	16730	Amphiuridae	70749	\N	\N	\N	\N	Amphiuridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26200	16732	Barentsia hildegardae	70785	\N	\N	\N	\N	Barentsia hildegardae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26201	16732	Barentsia gracilis	70784	\N	\N	\N	\N	Barentsia gracilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26202	16732	Barentsia discreta	70783	\N	\N	\N	\N	Barentsia discreta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26203	16732	Barentsia benedeni	70782	\N	\N	\N	\N	Barentsia benedeni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26204	16734	Loxomitra tetraorganon	70789	\N	\N	\N	\N	Loxomitra tetraorganon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26205	16734	Loxomitra mizugamaensis	70788	\N	\N	\N	\N	Loxomitra mizugamaensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26206	16733	Loxosomella vivipara	70799	\N	\N	\N	\N	Loxosomella vivipara	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26207	16733	Loxosomella varians	70798	\N	\N	\N	\N	Loxosomella varians	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26208	16733	Loxosomella vancouverensis	70797	\N	\N	\N	\N	Loxosomella vancouverensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26209	16733	Loxosomella stomatophora	70796	\N	\N	\N	\N	Loxosomella stomatophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26210	16733	Loxosomella sp.	70795	\N	\N	\N	\N	Loxosomella sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26211	16733	Loxosomella plakorticola	70794	\N	\N	\N	\N	Loxosomella plakorticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26212	16733	Loxosomella parguerensis	70793	\N	\N	\N	\N	Loxosomella parguerensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26213	16733	Loxosomella murmanica	70792	\N	\N	\N	\N	Loxosomella murmanica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26214	16733	Loxosomella harmeri	70791	\N	\N	\N	\N	Loxosomella harmeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26215	16736	Loxosomatoides sirindhornae	70802	\N	\N	\N	\N	Loxosomatoides sirindhornae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26216	16735	Pedicellina cernua	70804	\N	\N	\N	\N	Pedicellina cernua	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26217	16738	Neodasyidae	70811	\N	\N	\N	\N	Neodasyidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26218	16737	Xenotrichulidae	70883	\N	\N	\N	\N	Xenotrichulidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26219	16737	Dasydytidae	70872	\N	\N	\N	\N	Dasydytidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26220	16737	Chaetonotidae	70817	\N	\N	\N	\N	Chaetonotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26221	16740	Stylochaeta	70901	\N	\N	\N	\N	Stylochaeta<Gastrotricha XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26222	16740	Gastrotricha XXX	70899	\N	\N	\N	\N	Gastrotricha XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26223	16748	Paradasys	70905	\N	\N	\N	\N	Paradasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26224	16747	Xenodasys	70914	\N	\N	\N	\N	Xenodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26225	16747	Dactylopodola	70908	\N	\N	\N	\N	Dactylopodola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26226	16746	Redudasys	70918	\N	\N	\N	\N	Redudasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26227	16745	Pleurodasys	70934	\N	\N	\N	\N	Pleurodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26228	16745	Mesodasys	70929	\N	\N	\N	\N	Mesodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26229	16745	Lepidodasys	70926	\N	\N	\N	\N	Lepidodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26230	16745	Dolichodasys	70924	\N	\N	\N	\N	Dolichodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26231	16745	Cephalodasys	70921	\N	\N	\N	\N	Cephalodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26232	16744	Urodasys	70941	\N	\N	\N	\N	Urodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26233	16744	Macrodasys	70937	\N	\N	\N	\N	Macrodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26234	16743	Megadasys	70946	\N	\N	\N	\N	Megadasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26235	16743	Crasiella	70944	\N	\N	\N	\N	Crasiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26236	16742	Thaumastoderma	70978	\N	\N	\N	\N	Thaumastoderma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26237	16742	Tetranchyroderma	70968	\N	\N	\N	\N	Tetranchyroderma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26238	16742	Ptychostomella	70965	\N	\N	\N	\N	Ptychostomella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26239	16742	Pseudostomella	70963	\N	\N	\N	\N	Pseudostomella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26240	16742	Platydasys	70961	\N	\N	\N	\N	Platydasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26241	16742	Oregodasys	70957	\N	\N	\N	\N	Oregodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26242	16742	Diplodasys	70953	\N	\N	\N	\N	Diplodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26243	16742	Acanthodasys	70950	\N	\N	\N	\N	Acanthodasys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26244	16741	Turbanella	70986	\N	\N	\N	\N	Turbanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26245	16741	Paraturbanella	70982	\N	\N	\N	\N	Paraturbanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26246	16755	Austrognathia	70997	\N	\N	\N	\N	Austrognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26247	16755	Austrognatharia	70994	\N	\N	\N	\N	Austrognatharia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26248	16754	Gnathostomula	71003	\N	\N	\N	\N	Gnathostomula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26249	16754	Chirognathia	71001	\N	\N	\N	\N	Chirognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26250	16753	Tenuignathia	71014	\N	\N	\N	\N	Tenuignathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26251	16753	Mesognatharia	71012	\N	\N	\N	\N	Mesognatharia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26252	16753	Labidognathia	71010	\N	\N	\N	\N	Labidognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26253	16752	Valvognathia	71019	\N	\N	\N	\N	Valvognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26254	16752	Onychognathia	71017	\N	\N	\N	\N	Onychognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26255	16751	Problognathia	71022	\N	\N	\N	\N	Problognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26256	16750	Cosmognathia	71025	\N	\N	\N	\N	Cosmognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26257	16749	Rastrognathia	71029	\N	\N	\N	\N	Rastrognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26258	16756	Haplognathia	71033	\N	\N	\N	\N	Haplognathia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26259	16763	Environmental Enteropneusta 1	71043	\N	\N	\N	\N	Environmental Enteropneusta 1<Environmental Enteropneusta 1	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26260	16762	Stereobalanus	71057	\N	\N	\N	\N	Stereobalanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26261	16762	Saccoglossus	71053	\N	\N	\N	\N	Saccoglossus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26262	16762	Protoglossus	71051	\N	\N	\N	\N	Protoglossus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26263	16762	Meioglossus	71049	\N	\N	\N	\N	Meioglossus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26264	16762	Harrimania	71046	\N	\N	\N	\N	Harrimania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26265	16761	Tergivelum	71062	\N	\N	\N	\N	Tergivelum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26266	16761	Enteropneusta	71060	\N	\N	\N	\N	Enteropneusta<Incertae Sedis Enteropneusta	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26267	16760	Ptychodera	71074	\N	\N	\N	\N	Ptychodera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26268	16760	Incertae Sedis Ptychoderidae	71071	\N	\N	\N	\N	Incertae Sedis Ptychoderidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26269	16760	Glossobalanus	71068	\N	\N	\N	\N	Glossobalanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26270	16760	Balanoglossus	71066	\N	\N	\N	\N	Balanoglossus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26271	16759	Saxipendium	71079	\N	\N	\N	\N	Saxipendium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26272	16758	Glandiceps	71083	\N	\N	\N	\N	Glandiceps	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26273	16757	Enteropneusta sp. extrawide-lipped	71086	\N	\N	\N	\N	Enteropneusta sp. extrawide-lipped	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26274	16764	Enteropneusta	71089	\N	\N	\N	\N	Enteropneusta<Hemichordata XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26275	16765	Cephalodiscidae	71093	\N	\N	\N	\N	Cephalodiscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26276	16770	Antygomonas	71102	\N	\N	\N	\N	Antygomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26277	16769	Condyloderes	71107	\N	\N	\N	\N	Condyloderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26278	16769	Campyloderes	71105	\N	\N	\N	\N	Campyloderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26279	16768	Dracoderes	71110	\N	\N	\N	\N	Dracoderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26280	16767	Echinoderes	71115	\N	\N	\N	\N	Echinoderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26281	16767	Cephalorhyncha	71113	\N	\N	\N	\N	Cephalorhyncha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26282	16766	Zelinkaderes	71124	\N	\N	\N	\N	Zelinkaderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26283	16773	Environmental Homalorhagida 1	71128	\N	\N	\N	\N	Environmental Homalorhagida 1<Environmental Homalorhagida 1	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26284	16772	Paracentrophyes	71131	\N	\N	\N	\N	Paracentrophyes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26285	16771	Pycnophyes	71136	\N	\N	\N	\N	Pycnophyes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26286	16771	Kinorhynchus	71134	\N	\N	\N	\N	Kinorhynchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26287	16769	Centroderes	71144	\N	\N	\N	\N	Centroderes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26288	16776	Nanaloricus	71149	\N	\N	\N	\N	Nanaloricus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26289	16775	Pliciloricus	71152	\N	\N	\N	\N	Pliciloricus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26290	16777	Rhopalura ophiocomae	71157	\N	\N	\N	\N	Rhopalura ophiocomae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26291	16778	Dicyemidae	71160	\N	\N	\N	\N	Dicyemidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26292	16779	Variisporina	71214	\N	\N	\N	\N	Variisporina<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26293	16779	unclassified-Parvicapsulidae	71212	\N	\N	\N	\N	unclassified-Parvicapsulidae<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26294	16779	Tricellaria	71210	\N	\N	\N	\N	Tricellaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26295	16779	Selatium	71208	\N	\N	\N	\N	Selatium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26296	26071	Saracrinus	71206	\N	\N	\N	\N	Saracrinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26297	16779	Raiarctus	71204	\N	\N	\N	\N	Raiarctus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26298	16779	Pseudoxenos	71202	\N	\N	\N	\N	Pseudoxenos	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26299	16779	Prodiamesa	71200	\N	\N	\N	\N	Prodiamesa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26300	16779	Potamocoris	71198	\N	\N	\N	\N	Potamocoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26301	16779	Phascolosoma	71196	\N	\N	\N	\N	Phascolosoma<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26302	16779	Paraxenos	71192	\N	\N	\N	\N	Paraxenos	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26303	16779	Orzeliscus	71190	\N	\N	\N	\N	Orzeliscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26304	16779	Opecoelidae	71188	\N	\N	\N	\N	Opecoelidae<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26305	16779	Nierstraszella	71186	\N	\N	\N	\N	Nierstraszella<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26306	16779	Nanosesarma	71184	\N	\N	\N	\N	Nanosesarma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26307	16779	Metazoa XXXX	71182	\N	\N	\N	\N	Metazoa XXXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26308	16779	Maoridiamesa	71180	\N	\N	\N	\N	Maoridiamesa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26309	16779	Lychnocolax	71178	\N	\N	\N	\N	Lychnocolax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26310	16779	Loxosoma	71176	\N	\N	\N	\N	Loxosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26311	16779	Leucosphaera	71174	\N	\N	\N	\N	Leucosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26312	16779	Elliptio	71172	\N	\N	\N	\N	Elliptio<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26313	16779	Caberea	71170	\N	\N	\N	\N	Caberea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26314	16779	Alcyonidium	71168	\N	\N	\N	\N	Alcyonidium<Metazoa XXX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26315	16780	Limnognathia	71219	\N	\N	\N	\N	Limnognathia<Limnognathia<Limnognathia<Micrognathozoa	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26316	16790	Euciroa	71229	\N	\N	\N	\N	Euciroa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26317	16790	Entodesma	71227	\N	\N	\N	\N	Entodesma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26318	16790	Brechites	71225	\N	\N	\N	\N	Brechites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26319	26387	Anadara	71232	\N	\N	\N	\N	Anadara	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26320	16788	Troendleina	71241	\N	\N	\N	\N	Troendleina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26321	16788	Stewartia	71239	\N	\N	\N	\N	Stewartia<Bivalvia X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26322	16788	Notomyrtea	71237	\N	\N	\N	\N	Notomyrtea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26323	16788	Bretskya	71235	\N	\N	\N	\N	Bretskya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26324	16787	Wallucina	71315	\N	\N	\N	\N	Wallucina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26325	16787	Unknown	71313	\N	\N	\N	\N	Unknown<Heteroconchia	\N	2019-10-21 12:44:33	\N	\N	\N	A	P
26326	16787	Tivela	71311	\N	\N	\N	\N	Tivela	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26327	16787	Teredo	71309	\N	\N	\N	\N	Teredo	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26328	16787	Solecurtus	71307	\N	\N	\N	\N	Solecurtus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26329	16787	Radiolucina	71304	\N	\N	\N	\N	Radiolucina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26330	16787	Pseudolucinisca	71302	\N	\N	\N	\N	Pseudolucinisca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26331	16787	Protothaca	71300	\N	\N	\N	\N	Protothaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26332	16787	Parvilucina	71296	\N	\N	\N	\N	Parvilucina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26333	16787	Paphies	71293	\N	\N	\N	\N	Paphies	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26334	16787	Myrtea	71290	\N	\N	\N	\N	Myrtea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26335	16787	Moerella	71288	\N	\N	\N	\N	Moerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26336	16787	Lucinisca	71284	\N	\N	\N	\N	Lucinisca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26337	16787	Lucinidae	71282	\N	\N	\N	\N	Lucinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26338	16787	Lucinella	71280	\N	\N	\N	\N	Lucinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26339	16787	Lucina	71275	\N	\N	\N	\N	Lucina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26340	16787	Loripes	71272	\N	\N	\N	\N	Loripes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26341	16787	Lepidolucina	71270	\N	\N	\N	\N	Lepidolucina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26342	16787	Indoaustriella	71266	\N	\N	\N	\N	Indoaustriella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26343	16787	Heteroconchia X	71264	\N	\N	\N	\N	Heteroconchia X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26344	16787	Gloverina	71262	\N	\N	\N	\N	Gloverina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26345	16787	Glossus	71260	\N	\N	\N	\N	Glossus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26346	16787	Funafutia	71258	\N	\N	\N	\N	Funafutia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26347	16787	Epicodakia	71256	\N	\N	\N	\N	Epicodakia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26348	16787	Divaricella	71254	\N	\N	\N	\N	Divaricella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26349	16787	Divalinga	71251	\N	\N	\N	\N	Divalinga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26350	16787	Chavania	71248	\N	\N	\N	\N	Chavania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26351	16787	Cavilinga	71246	\N	\N	\N	\N	Cavilinga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26352	16787	Austrovenus	71244	\N	\N	\N	\N	Austrovenus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26353	16786	Verticordioidea	71797	\N	\N	\N	\N	Verticordioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26354	16786	Veneroida	71464	\N	\N	\N	\N	Veneroida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26355	16786	Thracioidea	71452	\N	\N	\N	\N	Thracioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26356	16786	Solenoidea	71445	\N	\N	\N	\N	Solenoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26357	16786	Poromyoidea	71437	\N	\N	\N	\N	Poromyoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26358	16786	Pandoroidea	71425	\N	\N	\N	\N	Pandoroidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26359	16786	Myoida	71369	\N	\N	\N	\N	Myoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26360	16786	Myochomoidea	71366	\N	\N	\N	\N	Myochomoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26361	16786	Myochamoidea	71360	\N	\N	\N	\N	Myochamoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26362	16786	Lucinoida	71352	\N	\N	\N	\N	Lucinoida<Heterodonta	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26363	16786	Hiatelloidea	71344	\N	\N	\N	\N	Hiatelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26364	16786	Cuspidarioidea	71333	\N	\N	\N	\N	Cuspidarioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26365	16786	Crassatelloidea	71326	\N	\N	\N	\N	Crassatelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26366	16786	Clavagelloidea	71321	\N	\N	\N	\N	Clavagelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26367	16786	Carditoidea	71318	\N	\N	\N	\N	Carditoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26368	16785	Lucinoida X	71815	\N	\N	\N	\N	Lucinoida X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26369	16785	Leptaxinus	71813	\N	\N	\N	\N	Leptaxinus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26370	16785	Dulcina	71810	\N	\N	\N	\N	Dulcina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26371	16785	Axinulus	71808	\N	\N	\N	\N	Axinulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26372	16785	Adontorhina	71806	\N	\N	\N	\N	Adontorhina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26373	16784	Unionoida	71825	\N	\N	\N	\N	Unionoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26374	16784	Trigonioida	71820	\N	\N	\N	\N	Trigonioida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26375	16784	Palaeoheterodonta X	71818	\N	\N	\N	\N	Palaeoheterodonta X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26376	16783	Palliolum	71858	\N	\N	\N	\N	Palliolum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26377	16783	Mizuhopecten	71856	\N	\N	\N	\N	Mizuhopecten	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26378	16783	Delectopecten	71854	\N	\N	\N	\N	Delectopecten	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26379	16782	Solemyoida	71882	\N	\N	\N	\N	Solemyoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26380	16782	Scaleoleda	71880	\N	\N	\N	\N	Scaleoleda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26381	16782	Nuculoida	71863	\N	\N	\N	\N	Nuculoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26382	16781	Pterioida	72100	\N	\N	\N	\N	Pterioida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26383	16781	Pectinoidea	72056	\N	\N	\N	\N	Pectinoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26384	16781	Ostreoida	72039	\N	\N	\N	\N	Ostreoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26385	16781	Mytiloida	71930	\N	\N	\N	\N	Mytiloida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26386	16781	Limoida	71916	\N	\N	\N	\N	Limoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26387	16781	Arcoida	71892	\N	\N	\N	\N	Arcoida<Pteriomorphia	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26388	16791	Scutopus	72179	\N	\N	\N	\N	Scutopus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26389	16791	Chaetoderma	72175	\N	\N	\N	\N	Chaetoderma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26390	16794	Mesonychoteuthis	72183	\N	\N	\N	\N	Mesonychoteuthis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26391	16793	Octopodiformes	72344	\N	\N	\N	\N	Octopodiformes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26392	16793	Decapodiformes	72186	\N	\N	\N	\N	Decapodiformes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26393	16792	Nautilida	72373	\N	\N	\N	\N	Nautilida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26394	16803	Zeacumantus	72827	\N	\N	\N	\N	Zeacumantus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26395	16803	Tympanotonus	72825	\N	\N	\N	\N	Tympanotonus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26396	16803	Thiara	72823	\N	\N	\N	\N	Thiara	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26397	16803	Thatcheria	72821	\N	\N	\N	\N	Thatcheria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26398	16803	Terebralia	72817	\N	\N	\N	\N	Terebralia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26399	16803	Telescopium	72815	\N	\N	\N	\N	Telescopium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26400	16803	Sorbeoconcha	72807	\N	\N	\N	\N	Sorbeoconcha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26401	16803	Pyrazus	72805	\N	\N	\N	\N	Pyrazus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26402	16803	Potamides	72803	\N	\N	\N	\N	Potamides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26403	16803	Peasiella	72800	\N	\N	\N	\N	Peasiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26404	16803	Modulus	72798	\N	\N	\N	\N	Modulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26405	16803	Mitra	72796	\N	\N	\N	\N	Mitra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26406	16803	Mainwaringia	72793	\N	\N	\N	\N	Mainwaringia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26407	16803	Lampanella	72791	\N	\N	\N	\N	Lampanella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26408	16803	Laevilitorina	72789	\N	\N	\N	\N	Laevilitorina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26409	16803	Lacuna	72787	\N	\N	\N	\N	Lacuna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26410	16803	Hypsogastropoda	72451	\N	\N	\N	\N	Hypsogastropoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26411	16803	Cremnoconchus	72449	\N	\N	\N	\N	Cremnoconchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26412	16803	Clypeomorus	72447	\N	\N	\N	\N	Clypeomorus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26413	16803	Cerithium	72443	\N	\N	\N	\N	Cerithium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26414	16803	Cerithidea	72429	\N	\N	\N	\N	Cerithidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26415	16803	Cenchritis	72427	\N	\N	\N	\N	Cenchritis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26416	16803	Caenogastropoda X	72425	\N	\N	\N	\N	Caenogastropoda X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26417	16803	Bembicium	72423	\N	\N	\N	\N	Bembicium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26418	16803	Batillaria	72421	\N	\N	\N	\N	Batillaria<Caenogastropoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26419	16803	Austrolittorina	72415	\N	\N	\N	\N	Austrolittorina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26420	16803	Architaenioglossa	72386	\N	\N	\N	\N	Architaenioglossa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26421	16803	Afrolittorina	72381	\N	\N	\N	\N	Afrolittorina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26422	16802	Cocculinoidea	72830	\N	\N	\N	\N	Cocculinoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26423	16801	Coccopigya	72838	\N	\N	\N	\N	Coccopigya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26424	16800	Notocrater	72845	\N	\N	\N	\N	Notocrater	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26425	16800	Mikadotrochus	72843	\N	\N	\N	\N	Mikadotrochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26426	16800	Caymanabyssia	72841	\N	\N	\N	\N	Caymanabyssia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26427	90515	Gymnosomata	87025	\N	\N	\N	\N	Gymnosomata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26428	90516	Achatinidae	87000	\N	\N	\N	\N	Achatinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26429	90516	Veronicellidae	86999	\N	\N	\N	\N	Veronicellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26430	90516	Glacidorbidae	86998	\N	\N	\N	\N	Glacidorbidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26431	90515	Umbraculidae	86997	\N	\N	\N	\N	Umbraculidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26432	90515	Tylodinidae	86996	\N	\N	\N	\N	Tylodinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26433	90516	Trimusculidae	86995	\N	\N	\N	\N	Trimusculidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26434	91706	Tethydidae	86994	\N	\N	\N	\N	Tethydidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26435	90516	Smeagolidae	86993	\N	\N	\N	\N	Smeagolidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26436	90516	Siphonariidae	86992	\N	\N	\N	\N	Siphonariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26437	90515	Scaphandridae	86991	\N	\N	\N	\N	Scaphandridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26438	90516	Pseudunelidae	86990	\N	\N	\N	\N	Pseudunelidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26439	91707	Pleurobranchaeidae	86988	\N	\N	\N	\N	Pleurobranchaeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26440	90516	Platyhedylidae	86987	\N	\N	\N	\N	Platyhedylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26441	91706	Phyllidiidae	86986	\N	\N	\N	\N	Phyllidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26442	90515	Philinoglossidae	86985	\N	\N	\N	\N	Philinoglossidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26443	90515	Runcinidae	86984	\N	\N	\N	\N	Runcinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26444	90515	Philinidae	86983	\N	\N	\N	\N	Philinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26445	90516	Parhedylidae	86982	\N	\N	\N	\N	Parhedylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26446	90516	Oxynoidae	86981	\N	\N	\N	\N	Oxynoidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26447	91706	Onchidorididae	86980	\N	\N	\N	\N	Onchidorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26448	91706	Notaeolidiidae	86979	\N	\N	\N	\N	Notaeolidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26449	16799	Murchisonellidae	86978	\N	\N	\N	\N	Murchisonellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26450	90516	Hedylopsidae	86977	\N	\N	\N	\N	Hedylopsidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26451	91706	Goniodorididae	86976	\N	\N	\N	\N	Goniodorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26452	91706	Eubranchidae	86975	\N	\N	\N	\N	Eubranchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26453	90515	Cylichnidae	86974	\N	\N	\N	\N	Cylichnidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26454	91706	Calycidorididae	86973	\N	\N	\N	\N	Calycidorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26455	91706	Proctonotidae	86972	\N	\N	\N	\N	Proctonotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26456	90516	Otinidae	86971	\N	\N	\N	\N	Otinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26457	91706	Tritoniidae	86970	\N	\N	\N	\N	Tritoniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26458	91706	Polyceridae	86969	\N	\N	\N	\N	Polyceridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26459	90516	Hygromiidae	86968	\N	\N	\N	\N	Hygromiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26460	90516	Juliidae	86967	\N	\N	\N	\N	Juliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26461	90516	Lymnaeoidea	86966	\N	\N	\N	\N	Lymnaeoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26462	90516	Plakobranchidae	86965	\N	\N	\N	\N	Plakobranchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26463	90516	Discidae	86964	\N	\N	\N	\N	Discidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26464	91706	Dironidae	86963	\N	\N	\N	\N	Dironidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26465	91706	Discodoridae	86962	\N	\N	\N	\N	Discodoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26466	90515	Ilbiidae	86961	\N	\N	\N	\N	Ilbiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26467	91704	Desmopteridae	86960	\N	\N	\N	\N	Desmopteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26468	90516	Limacidae	86959	\N	\N	\N	\N	Limacidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26469	91706	Dendronotidae	86958	\N	\N	\N	\N	Dendronotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26470	91706	Dendrodorididae	86957	\N	\N	\N	\N	Dendrodorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26471	90516	Caliphyllidae	86956	\N	\N	\N	\N	Caliphyllidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26472	91706	Tergipedidae	86955	\N	\N	\N	\N	Tergipedidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26473	90516	Costasiellidae	86954	\N	\N	\N	\N	Costasiellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26474	90516	Cochlicopidae	86953	\N	\N	\N	\N	Cochlicopidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26475	91704	Cliidae	86952	\N	\N	\N	\N	Cliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26476	91706	Chromodorididae	86951	\N	\N	\N	\N	Chromodorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26477	90516	Chilinidae	86950	\N	\N	\N	\N	Chilinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26478	91706	Charcotiidae	86949	\N	\N	\N	\N	Charcotiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26479	90516	Helicidae	86948	\N	\N	\N	\N	Helicidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26480	91704	Cavoliniidae	86947	\N	\N	\N	\N	Cavoliniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26481	91706	Facelinidae	86946	\N	\N	\N	\N	Facelinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26482	91706	Flabellinidae	86945	\N	\N	\N	\N	Flabellinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26483	90516	Limapontiidae	86944	\N	\N	\N	\N	Limapontiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26484	91706	Cadlinidae	86943	\N	\N	\N	\N	Cadlinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26485	90516	Boselliidae	86942	\N	\N	\N	\N	Boselliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26486	91706	Bornellidae	86941	\N	\N	\N	\N	Bornellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26487	91706	Bathydorididae	86940	\N	\N	\N	\N	Bathydorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26488	91707	Pleurobranchidae	86939	\N	\N	\N	\N	Pleurobranchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26489	90516	Athoracophoridae	86938	\N	\N	\N	\N	Athoracophoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26490	90515	Haminoeidae	86937	\N	\N	\N	\N	Haminoeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26491	90516	Asperspinidae	86936	\N	\N	\N	\N	Asperspinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26492	90516	Volvatellidae	86935	\N	\N	\N	\N	Volvatellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26493	91706	Akiodorididae	86934	\N	\N	\N	\N	Akiodorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26494	91706	Arminidae	86933	\N	\N	\N	\N	Arminidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26495	91706	Dotidae	86932	\N	\N	\N	\N	Dotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26496	90516	Arionidae	86931	\N	\N	\N	\N	Arionidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26497	90516	Hermaeidae	86930	\N	\N	\N	\N	Hermaeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26498	91706	Dorididae	86929	\N	\N	\N	\N	Dorididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26499	90516	Clausiliidae	86928	\N	\N	\N	\N	Clausiliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26500	90516	Lymnaeidae	86927	\N	\N	\N	\N	Lymnaeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26501	90515	Akeridae	86926	\N	\N	\N	\N	Akeridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26502	90516	Aitengidae	86925	\N	\N	\N	\N	Aitengidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26503	91706	Aeolidiidae	86924	\N	\N	\N	\N	Aeolidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26504	90515	Bullidae	86923	\N	\N	\N	\N	Bullidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26505	90516	Bradybaenidae	86922	\N	\N	\N	\N	Bradybaenidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26506	90516	Acroloxidae	86921	\N	\N	\N	\N	Acroloxidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26507	90516	Acochlidiidae	86920	\N	\N	\N	\N	Acochlidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26508	90515	Rhizoridae	86919	\N	\N	\N	\N	Rhizoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26509	90516	Succineidae	86918	\N	\N	\N	\N	Succineidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26510	90515	Gastropteridae	86917	\N	\N	\N	\N	Gastropteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26511	90515	Retusidae	86916	\N	\N	\N	\N	Retusidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26512	90516	Physidae	86915	\N	\N	\N	\N	Physidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26513	90516	Onchidiidae	86914	\N	\N	\N	\N	Onchidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26514	90516	Ellobiidae	86913	\N	\N	\N	\N	Ellobiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26515	90516	Latiidae	86912	\N	\N	\N	\N	Latiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26516	26527	Aplustridae	86911	\N	\N	\N	\N	Aplustridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26517	90516	Pyramidellidae	86910	\N	\N	\N	\N	Pyramidellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26518	90515	Diaphanidae	86909	\N	\N	\N	\N	Diaphanidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26519	90515	Aplysiidae	86908	\N	\N	\N	\N	Aplysiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26520	26527	Bullinidae	86907	\N	\N	\N	\N	Bullinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26521	90516	Planorbidae	86906	\N	\N	\N	\N	Planorbidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26522	90516	Amphibolidae	86905	\N	\N	\N	\N	Amphibolidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26523	90515	Aglajidae	86904	\N	\N	\N	\N	Aglajidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26524	91704	Limacinidae	86903	\N	\N	\N	\N	Limacinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26525	91704	Creseidae	86902	\N	\N	\N	\N	Creseidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26526	91704	Cuvierinidae	86901	\N	\N	\N	\N	Cuvierinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26527	16799	LowerHeterobranchia	73485	\N	\N	\N	\N	LowerHeterobranchia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26528	16798	Cycloneritimorpha	73550	\N	\N	\N	\N	Cycloneritimorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26529	26476	Verconia	73607	\N	\N	\N	\N	Verconia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26530	26476	Tyrinna	73605	\N	\N	\N	\N	Tyrinna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26531	26476	Thorunna	73603	\N	\N	\N	\N	Thorunna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26532	26476	Risbecia	73601	\N	\N	\N	\N	Risbecia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26533	26476	Pectenodoris	73599	\N	\N	\N	\N	Pectenodoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26534	26476	Noumea	73597	\N	\N	\N	\N	Noumea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26535	26476	Mexichromis	73594	\N	\N	\N	\N	Mexichromis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26536	26476	Goniobranchus	73591	\N	\N	\N	\N	Goniobranchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26537	26476	Glossodoris	73587	\N	\N	\N	\N	Glossodoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26538	26476	Diversidoris	73585	\N	\N	\N	\N	Diversidoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26539	26476	Digidentis	73583	\N	\N	\N	\N	Digidentis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26540	26476	Ceratosoma	73580	\N	\N	\N	\N	Ceratosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26541	91706	Cadlinella	73578	\N	\N	\N	\N	Cadlinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26542	26476	Ardeadoris	73576	\N	\N	\N	\N	Ardeadoris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26543	16796	Yayoiacmea	73668	\N	\N	\N	\N	Yayoiacmea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26544	16796	Scutellastra	73666	\N	\N	\N	\N	Scutellastra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26545	16796	Patelloidea	73657	\N	\N	\N	\N	Patelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26546	16796	Patellogastropoda X	73655	\N	\N	\N	\N	Patellogastropoda X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26547	16796	Lottioidea	73618	\N	\N	\N	\N	Lottioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26548	16796	Lepeta	73616	\N	\N	\N	\N	Lepeta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26549	16796	Erginus	73614	\N	\N	\N	\N	Erginus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26550	16796	Cryptobranchia	73612	\N	\N	\N	\N	Cryptobranchia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26551	16796	Bathyacmaea	73610	\N	\N	\N	\N	Bathyacmaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26552	16795	Vetigastropoda X	74013	\N	\N	\N	\N	Vetigastropoda X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26553	16795	Trochus	74010	\N	\N	\N	\N	Trochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26554	16795	Trochoidea	73893	\N	\N	\N	\N	Trochoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26555	16795	Thalotia	73891	\N	\N	\N	\N	Thalotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26556	16795	Tectus	73886	\N	\N	\N	\N	Tectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26557	16795	Synaptocochlea	73884	\N	\N	\N	\N	Synaptocochlea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26558	16795	Symmetromphalus	73881	\N	\N	\N	\N	Symmetromphalus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26559	16795	Symmetriapelta	73879	\N	\N	\N	\N	Symmetriapelta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26560	16795	Spectamen	73877	\N	\N	\N	\N	Spectamen	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26561	16795	Shinkailepas	73875	\N	\N	\N	\N	Shinkailepas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26562	16795	Seguenzioidea	73870	\N	\N	\N	\N	Seguenzioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26563	16795	Pseudorimula	73868	\N	\N	\N	\N	Pseudorimula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26564	16795	Prothalotia	73866	\N	\N	\N	\N	Prothalotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26565	16795	Prisogaster	73864	\N	\N	\N	\N	Prisogaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26566	16795	Pleurotomarioidea	73847	\N	\N	\N	\N	Pleurotomarioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26567	16795	Phasianotrochus	73845	\N	\N	\N	\N	Phasianotrochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26568	16795	Phasianella	73841	\N	\N	\N	\N	Phasianella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26569	16795	Olgasolaris	73838	\N	\N	\N	\N	Olgasolaris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26570	16795	Notogibbula	73836	\N	\N	\N	\N	Notogibbula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26571	16795	Neomphaloidea	73820	\N	\N	\N	\N	Neomphaloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26572	16795	Munditiella	73818	\N	\N	\N	\N	Munditiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26573	16795	Monilea	73816	\N	\N	\N	\N	Monilea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26574	16795	Microgaza	73813	\N	\N	\N	\N	Microgaza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26575	16795	Lischkeia	73811	\N	\N	\N	\N	Lischkeia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26576	16795	Leptocollonia	73809	\N	\N	\N	\N	Leptocollonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26577	16795	Lepetodriloidea	73797	\N	\N	\N	\N	Lepetodriloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26578	16795	Lepetelloidea	73789	\N	\N	\N	\N	Lepetelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26579	16795	Isanda	73787	\N	\N	\N	\N	Isanda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26580	16795	Iheyaspira	73785	\N	\N	\N	\N	Iheyaspira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26581	16795	Hirtopelta	73783	\N	\N	\N	\N	Hirtopelta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26582	16795	Herpetopoma	73781	\N	\N	\N	\N	Herpetopoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26583	16795	Haliotoidea	73769	\N	\N	\N	\N	Haliotoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26584	16795	Guildfordia	73766	\N	\N	\N	\N	Guildfordia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26585	16795	Granata	73764	\N	\N	\N	\N	Granata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26586	16795	Ginebis	73761	\N	\N	\N	\N	Ginebis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26587	16795	Gabrielona	73759	\N	\N	\N	\N	Gabrielona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26588	16795	Fumocapulus	73757	\N	\N	\N	\N	Fumocapulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26589	16795	Fissurelloidea	73710	\N	\N	\N	\N	Fissurelloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26590	16795	Eurytrochus	73708	\N	\N	\N	\N	Eurytrochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26591	16795	Euchelus	73706	\N	\N	\N	\N	Euchelus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26592	16795	Ethaliella	73704	\N	\N	\N	\N	Ethaliella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26593	16795	Ethalia	73702	\N	\N	\N	\N	Ethalia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26594	16795	Cookia	73700	\N	\N	\N	\N	Cookia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26595	16795	Collonista	73697	\N	\N	\N	\N	Collonista	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26596	16795	Clanculus	73694	\N	\N	\N	\N	Clanculus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26597	16795	Cinysca	73692	\N	\N	\N	\N	Cinysca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26598	16795	Broderipia	73690	\N	\N	\N	\N	Broderipia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26599	16795	Bothropoma	73688	\N	\N	\N	\N	Bothropoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26600	16795	Bolma	73683	\N	\N	\N	\N	Bolma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26601	16795	Bellastraea	73681	\N	\N	\N	\N	Bellastraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26602	16795	Austrocochlea	73679	\N	\N	\N	\N	Austrocochlea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26603	16795	Astraea	73677	\N	\N	\N	\N	Astraea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26604	16795	Arene	73675	\N	\N	\N	\N	Arene	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26605	16795	Angaria	73671	\N	\N	\N	\N	Angaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26606	16804	Veleropilina	74019	\N	\N	\N	\N	Veleropilina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26607	16804	Laevipilina	74017	\N	\N	\N	\N	Laevipilina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26608	16806	Lepidopleurida	74093	\N	\N	\N	\N	Lepidopleurida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26609	16806	Chitonida	74023	\N	\N	\N	\N	Chitonida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26610	16805	Placiphorella	74137	\N	\N	\N	\N	Placiphorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26611	16809	Rhabdidae	74155	\N	\N	\N	\N	Rhabdidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26612	16809	Dentaliidae	74141	\N	\N	\N	\N	Dentaliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26613	16808	Siphonodentaliidae	74175	\N	\N	\N	\N	Siphonodentaliidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26614	16808	Pulsellidae	74172	\N	\N	\N	\N	Pulsellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26615	16808	Gadilidae	74166	\N	\N	\N	\N	Gadilidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26616	16808	Entalinidae	74161	\N	\N	\N	\N	Entalinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26617	26364	Cardiomya	74179	\N	\N	\N	\N	Cardiomya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26618	16811	Simrothiella	74187	\N	\N	\N	\N	Simrothiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26619	16811	Helicoradomenia	74185	\N	\N	\N	\N	Helicoradomenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26620	16811	Epimenia	74183	\N	\N	\N	\N	Epimenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26621	16810	Wirenia	74192	\N	\N	\N	\N	Wirenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26622	16810	Micromenia	74190	\N	\N	\N	\N	Micromenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26623	51394	Buddenbrockia X	74197	\N	\N	\N	\N	Buddenbrockia X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26624	16812	Myxosporea	74200	\N	\N	\N	\N	Myxosporea<Myxosporea XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26625	16858	Plectoidea	74301	\N	\N	\N	\N	Plectoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26626	16858	Leptolaimoidea	74272	\N	\N	\N	\N	Leptolaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26627	16858	Haliplectoidea	74265	\N	\N	\N	\N	Haliplectoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26628	16858	Environmental Araeolaimida 1	74262	\N	\N	\N	\N	Environmental Araeolaimida 1<Araeolaimida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26629	16858	Cylindrolaimidae	74258	\N	\N	\N	\N	Cylindrolaimidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26630	16858	Axonolaimoidea	74246	\N	\N	\N	\N	Axonolaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26631	16857	Seuratoidea	74426	\N	\N	\N	\N	Seuratoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26632	16857	Heterakoidea	74416	\N	\N	\N	\N	Heterakoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26633	16857	Cosmocercoidea	74406	\N	\N	\N	\N	Cosmocercoidea<Ascaridida<Chromadorea<Nematoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26634	16857	Ascaridoidea	74334	\N	\N	\N	\N	Ascaridoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26635	16856	Vittatidera	74586	\N	\N	\N	\N	Vittatidera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26636	16856	Tylenchidae	74584	\N	\N	\N	\N	Tylenchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26637	16856	Trypanoxyuris	74582	\N	\N	\N	\N	Trypanoxyuris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26638	16856	Tricoma	74580	\N	\N	\N	\N	Tricoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26639	16856	Terschellingia	74578	\N	\N	\N	\N	Terschellingia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26640	16856	Teratodiplogaster	74576	\N	\N	\N	\N	Teratodiplogaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26641	16856	Spiruroidea	74574	\N	\N	\N	\N	Spiruroidea<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26642	16856	Spiruridae	74572	\N	\N	\N	\N	Spiruridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26643	16856	Spilophorella	74570	\N	\N	\N	\N	Spilophorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26644	26760	Sphaeronema	74568	\N	\N	\N	\N	Sphaeronema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26645	16856	Sphaerolaimus	74565	\N	\N	\N	\N	Sphaerolaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26646	26734	Spauligodon	74557	\N	\N	\N	\N	Spauligodon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26647	16856	Siconema	74555	\N	\N	\N	\N	Siconema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26648	16856	Setosabatieria	74553	\N	\N	\N	\N	Setosabatieria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26649	16856	Scottnema	74551	\N	\N	\N	\N	Scottnema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26650	16856	Schistosoma	74549	\N	\N	\N	\N	Schistosoma<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26651	16856	Sauertylenchus	74547	\N	\N	\N	\N	Sauertylenchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26652	16856	Rhabditophanes	74545	\N	\N	\N	\N	Rhabditophanes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26653	16856	Rhabditinae	74543	\N	\N	\N	\N	Rhabditinae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26654	16856	Rhabditidae	74541	\N	\N	\N	\N	Rhabditidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26655	16856	Ptycholaimellus	74539	\N	\N	\N	\N	Ptycholaimellus<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26656	16856	Pseudodiplogasterid	74537	\N	\N	\N	\N	Pseudodiplogasterid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26657	16856	Procephalobus	74535	\N	\N	\N	\N	Procephalobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26658	16856	Pierrickia	74533	\N	\N	\N	\N	Pierrickia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26659	16856	Perodira	74531	\N	\N	\N	\N	Perodira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26660	16856	Parodontophora	74529	\N	\N	\N	\N	Parodontophora<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26661	16856	Paratricoma	74527	\N	\N	\N	\N	Paratricoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26662	16856	Parastrongyloides	74525	\N	\N	\N	\N	Parastrongyloides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26663	16856	Parasitodiplogaster	74523	\N	\N	\N	\N	Parasitodiplogaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26664	16856	Parapharyngodon	74521	\N	\N	\N	\N	Parapharyngodon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26665	16856	Paralinhomoeus	74519	\N	\N	\N	\N	Paralinhomoeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26666	16856	Paracamallanus	74517	\N	\N	\N	\N	Paracamallanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26667	16856	Nudora	74514	\N	\N	\N	\N	Nudora<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26668	16856	Neochromadora	74511	\N	\N	\N	\N	Neochromadora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26669	16856	Multicaecum	74509	\N	\N	\N	\N	Multicaecum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26670	16856	Monoposthia	74507	\N	\N	\N	\N	Monoposthia<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26671	16856	Molgolaimus	74505	\N	\N	\N	\N	Molgolaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26672	16856	Loofia	74503	\N	\N	\N	\N	Loofia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26673	16856	Litomosoides	74501	\N	\N	\N	\N	Litomosoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26674	16856	Labeonema	74499	\N	\N	\N	\N	Labeonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26675	88296	Isolaimium	74497	\N	\N	\N	\N	Isolaimium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26676	16856	Hoplolaimus	74495	\N	\N	\N	\N	Hoplolaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26677	16856	Heterorhabditidoides	74492	\N	\N	\N	\N	Heterorhabditidoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26678	16856	Halichoanolaimus	74490	\N	\N	\N	\N	Halichoanolaimus<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26679	16856	Greeffiella	74488	\N	\N	\N	\N	Greeffiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26680	16856	Eutylenchus	74486	\N	\N	\N	\N	Eutylenchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26681	16856	Drosophila	74482	\N	\N	\N	\N	Drosophila<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26682	16856	Dorylaimopsis	74480	\N	\N	\N	\N	Dorylaimopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26683	16856	Diplogasterid	74478	\N	\N	\N	\N	Diplogasterid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26684	16856	Dichromadora	74476	\N	\N	\N	\N	Dichromadora<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26685	16856	Desmoscolex	74474	\N	\N	\N	\N	Desmoscolex<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26686	16856	Desmolaimus	74471	\N	\N	\N	\N	Desmolaimus<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26687	16856	Cyatholaimidae	74469	\N	\N	\N	\N	Cyatholaimidae<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26688	16856	Cyartonema	74467	\N	\N	\N	\N	Cyartonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26689	16856	Creagrocercus	74465	\N	\N	\N	\N	Creagrocercus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26690	16856	Comesomatidae	74463	\N	\N	\N	\N	Comesomatidae<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26691	16856	Clavinema	74461	\N	\N	\N	\N	Clavinema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26692	16856	Chromadorita	74459	\N	\N	\N	\N	Chromadorita<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26693	16856	Chromadorina	74457	\N	\N	\N	\N	Chromadorina<Chromadorea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26694	16856	Chromadorid	74455	\N	\N	\N	\N	Chromadorid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26695	16856	Chromadorea X sp.	74454	\N	\N	\N	\N	Chromadorea X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26696	16856	Chromadora	74451	\N	\N	\N	\N	Chromadora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26697	16856	Caloosia	74449	\N	\N	\N	\N	Caloosia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26698	16856	Calomicrolaimus	74446	\N	\N	\N	\N	Calomicrolaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26699	16856	Cactodera	74444	\N	\N	\N	\N	Cactodera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26700	16856	Baujardia	74442	\N	\N	\N	\N	Baujardia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26701	16856	Atrochromadora	74440	\N	\N	\N	\N	Atrochromadora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26702	16856	Allantonematidae	74438	\N	\N	\N	\N	Allantonematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26703	16855	Tarvaiidae	74648	\N	\N	\N	\N	Tarvaiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26704	16855	Selachinematidae	74643	\N	\N	\N	\N	Selachinematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26705	16855	Incertae Sedis Chromadorida	74640	\N	\N	\N	\N	Incertae Sedis Chromadorida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26706	16855	Environmental Chromadorida 4	74637	\N	\N	\N	\N	Environmental Chromadorida 4<Chromadorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26707	16855	Environmental Chromadorida 3	74634	\N	\N	\N	\N	Environmental Chromadorida 3<Chromadorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26708	16855	Cyatholaimidae	74614	\N	\N	\N	\N	Cyatholaimidae<Chromadorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26709	16855	Chromadoridae	74597	\N	\N	\N	\N	Chromadoridae<Chromadorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26710	16855	Choanolaimidae	74594	\N	\N	\N	\N	Choanolaimidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26711	16855	Ceramonematidae	74589	\N	\N	\N	\N	Ceramonematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26712	16854	Richtersioidea	74707	\N	\N	\N	\N	Richtersioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26713	16854	Monoposthiidae	74702	\N	\N	\N	\N	Monoposthiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26714	16854	Epsilonematidae	74698	\N	\N	\N	\N	Epsilonematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26715	16854	Environmental Desmodorida 1	74695	\N	\N	\N	\N	Environmental Desmodorida 1<Desmodorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26716	16854	Draconematidae	74683	\N	\N	\N	\N	Draconematidae<Desmodorida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26717	16854	Desmodoridae	74652	\N	\N	\N	\N	Desmodoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26718	16853	Desmoscolecidae	74712	\N	\N	\N	\N	Desmoscolecidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26719	16852	Tylopharyngidae	74771	\N	\N	\N	\N	Tylopharyngidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26720	16852	Neodiplogasteridae	74746	\N	\N	\N	\N	Neodiplogasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26721	16852	Diplogasteroididae	74742	\N	\N	\N	\N	Diplogasteroididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26722	16852	Diplogasteridae	74720	\N	\N	\N	\N	Diplogasteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26723	16852	Cylindrocorporidae	74716	\N	\N	\N	\N	Cylindrocorporidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26724	16851	Environmental Chromadorea 8	74775	\N	\N	\N	\N	Environmental Chromadorea 8<Incertae Sedis Chromadorea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26725	16850	Xyalidae	74826	\N	\N	\N	\N	Xyalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26726	16850	Siphonolaimoidea	74823	\N	\N	\N	\N	Siphonolaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26727	16850	Monhysteridae	74798	\N	\N	\N	\N	Monhysteridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26728	16850	Linhomoeidae	74794	\N	\N	\N	\N	Linhomoeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26729	16850	Environmental Monhysterida 5	74791	\N	\N	\N	\N	Environmental Monhysterida 5<Monhysterida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26730	16850	Environmental Monhysterida 4	74788	\N	\N	\N	\N	Environmental Monhysterida 4<Monhysterida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26731	16850	Environmental Monhysterida 2	74785	\N	\N	\N	\N	Environmental Monhysterida 2<Monhysterida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26732	16850	Comesomatidae	74779	\N	\N	\N	\N	Comesomatidae<Monhysterida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26733	16849	Thelastomatoidea	74867	\N	\N	\N	\N	Thelastomatoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26734	16849	Oxyuroidea	74842	\N	\N	\N	\N	Oxyuroidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26735	16848	Teratocephaloidea	75287	\N	\N	\N	\N	Teratocephaloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26736	16848	Strongylida	75162	\N	\N	\N	\N	Strongylida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26737	16848	Rhabditoidea	75038	\N	\N	\N	\N	Rhabditoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26738	16848	Panagrolaimoidea	74959	\N	\N	\N	\N	Panagrolaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26739	16848	Myolaimoidea	74956	\N	\N	\N	\N	Myolaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26740	16848	Incertae Sedis Rhabditida	74951	\N	\N	\N	\N	Incertae Sedis Rhabditida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26741	16848	Environmental Rhabditida 6	74948	\N	\N	\N	\N	Environmental Rhabditida 6<Rhabditida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26742	16848	Environmental Rhabditida 5	74945	\N	\N	\N	\N	Environmental Rhabditida 5<Rhabditida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26743	16848	Environmental Rhabditida 4	74942	\N	\N	\N	\N	Environmental Rhabditida 4<Rhabditida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26744	16848	Environmental Rhabditida 3	74939	\N	\N	\N	\N	Environmental Rhabditida 3<Rhabditida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26745	16848	Environmental Rhabditida 1	74936	\N	\N	\N	\N	Environmental Rhabditida 1<Rhabditida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26746	16848	Drilonematoidea	74926	\N	\N	\N	\N	Drilonematoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26747	16848	Cephaloboidea	74881	\N	\N	\N	\N	Cephaloboidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26748	16848	Bunonematoidea	74875	\N	\N	\N	\N	Bunonematoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26749	16847	Thelazioidea	75493	\N	\N	\N	\N	Thelazioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26750	16847	Spiruroidea	75464	\N	\N	\N	\N	Spiruroidea<Spirurida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26751	16847	Skrjabillanoidea	75461	\N	\N	\N	\N	Skrjabillanoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26752	16847	Physalopteroidea	75450	\N	\N	\N	\N	Physalopteroidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26753	16847	Habronematoidea	75441	\N	\N	\N	\N	Habronematoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26754	16847	Gnathostomatoidea	75428	\N	\N	\N	\N	Gnathostomatoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26755	16847	Filarioidea	75400	\N	\N	\N	\N	Filarioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26756	16847	Dracunculoidea	75327	\N	\N	\N	\N	Dracunculoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26757	16847	Diplotriaenoidea	75324	\N	\N	\N	\N	Diplotriaenoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26758	16847	Camallanoidea	75304	\N	\N	\N	\N	Camallanoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26759	16847	Acuarioidea	75297	\N	\N	\N	\N	Acuarioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26760	16846	Tylenchina	75646	\N	\N	\N	\N	Tylenchina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26761	16846	Hexatylina	75622	\N	\N	\N	\N	Hexatylina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26762	16846	Environmental Tylenchida 8	75619	\N	\N	\N	\N	Environmental Tylenchida 8<Tylenchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26763	16846	Environmental Tylenchida 7	75616	\N	\N	\N	\N	Environmental Tylenchida 7<Tylenchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26764	16846	Environmental Tylenchida 6	75613	\N	\N	\N	\N	Environmental Tylenchida 6<Tylenchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26765	16846	Environmental Tylenchida 1	75610	\N	\N	\N	\N	Environmental Tylenchida 1<Tylenchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26766	16846	Environmental Tylenchida 11	75607	\N	\N	\N	\N	Environmental Tylenchida 11<Tylenchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26767	16846	Aphelenchina	75503	\N	\N	\N	\N	Aphelenchina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26768	16869	Soboliphymatidae	75898	\N	\N	\N	\N	Soboliphymatidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26769	16868	Nygolaimina	76133	\N	\N	\N	\N	Nygolaimina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26770	16868	Incertae Sedis Dorylaimida	76130	\N	\N	\N	\N	Incertae Sedis Dorylaimida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26771	16868	Environmental Dorylaimida 3	76127	\N	\N	\N	\N	Environmental Dorylaimida 3<Dorylaimida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26772	16868	Environmental Dorylaimida 2	76124	\N	\N	\N	\N	Environmental Dorylaimida 2<Dorylaimida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26773	16868	Dorylaimina	75902	\N	\N	\N	\N	Dorylaimina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26774	16867	Viscosia	76184	\N	\N	\N	\N	Viscosia<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26775	16867	Trichocephalida	76182	\N	\N	\N	\N	Trichocephalida<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26776	16867	Solididens	76180	\N	\N	\N	\N	Solididens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26777	16867	Rhabdocoma	76178	\N	\N	\N	\N	Rhabdocoma<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26778	16867	Parodontophora	76176	\N	\N	\N	\N	Parodontophora<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26779	16867	Pareurystomina	76174	\N	\N	\N	\N	Pareurystomina<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26780	16867	Oxystominidae	76172	\N	\N	\N	\N	Oxystominidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26781	16867	Oncholaimus	76170	\N	\N	\N	\N	Oncholaimus<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26782	16867	Miconchus	76168	\N	\N	\N	\N	Miconchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26783	16867	Metaporcelaimus	76166	\N	\N	\N	\N	Metaporcelaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26784	16867	Longidorella	76164	\N	\N	\N	\N	Longidorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26785	16867	Funaria	76162	\N	\N	\N	\N	Funaria<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26786	16867	Enoplea X sp.	76161	\N	\N	\N	\N	Enoplea X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26787	16867	Diphtherophora	76159	\N	\N	\N	\N	Diphtherophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26788	16867	Chronogaster	76157	\N	\N	\N	\N	Chronogaster<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26789	16867	Campydora	76155	\N	\N	\N	\N	Campydora<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26790	16867	Calyptronema	76152	\N	\N	\N	\N	Calyptronema<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26791	16867	Bathyodontus	76150	\N	\N	\N	\N	Bathyodontus<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26792	16867	Bathyeurystomina	76148	\N	\N	\N	\N	Bathyeurystomina<Enoplea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26793	26769	Aquatides	76146	\N	\N	\N	\N	Aquatides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26794	16867	Aporcelaimus	76144	\N	\N	\N	\N	Aporcelaimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26795	16866	Tripyloidoidea	76333	\N	\N	\N	\N	Tripyloidoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26796	16866	Tripyloidea	76304	\N	\N	\N	\N	Tripyloidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26797	16866	Triplonchida	76301	\N	\N	\N	\N	Triplonchida<Enoplida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26798	16866	Oxystominoidea	76280	\N	\N	\N	\N	Oxystominoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26799	16866	Oncholaimoidea	76265	\N	\N	\N	\N	Oncholaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26800	16866	Ironoidea	76253	\N	\N	\N	\N	Ironoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26801	16866	Environmental Enoplida 2	76250	\N	\N	\N	\N	Environmental Enoplida 2<Enoplida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26802	16866	Environmental Enoplida 1	76247	\N	\N	\N	\N	Environmental Enoplida 1<Enoplida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26803	16866	Enoploidea	76202	\N	\N	\N	\N	Enoploidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26804	16866	Cryptonchidae	76198	\N	\N	\N	\N	Cryptonchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26805	16866	Capillariidae	76194	\N	\N	\N	\N	Capillariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26806	16866	Campydoridae	76191	\N	\N	\N	\N	Campydoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26807	16866	Anticomidae	76188	\N	\N	\N	\N	Anticomidae<Enoplida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26808	16865	Environmental Enoplea 2	76340	\N	\N	\N	\N	Environmental Enoplea 2<Environmental Enoplea 2<Enoplea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26809	16864	Mermithoidea	76347	\N	\N	\N	\N	Mermithoidea<Mermithida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26810	16864	Environmental Mermithida 1	76344	\N	\N	\N	\N	Environmental Mermithida 1<Mermithida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26811	16863	Mononchina	76387	\N	\N	\N	\N	Mononchina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26812	16863	Environmental Mononchida 3	76384	\N	\N	\N	\N	Environmental Mononchida 3<Mononchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26813	16863	Bathyodontina	76381	\N	\N	\N	\N	Bathyodontina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26814	16862	Muspiceidae	76416	\N	\N	\N	\N	Muspiceidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26815	16861	Trefusiidae	76420	\N	\N	\N	\N	Trefusiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26816	16860	Trichuridae	76436	\N	\N	\N	\N	Trichuridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26817	16860	Trichinellidae	76425	\N	\N	\N	\N	Trichinellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26818	16859	Environmental Triplonchida 3	76483	\N	\N	\N	\N	Environmental Triplonchida 3<Triplonchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26819	16859	Environmental Triplonchida 1	76478	\N	\N	\N	\N	Environmental Triplonchida 1<Triplonchida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26820	16859	Diphtherophorina	76446	\N	\N	\N	\N	Diphtherophorina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26821	16870	Nematoda XXX	76490	\N	\N	\N	\N	Nematoda XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26822	16870	Dioctophyme	76488	\N	\N	\N	\N	Dioctophyme	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26823	16872	Chordodoidea	76495	\N	\N	\N	\N	Chordodoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26824	16871	Gordioidea	76513	\N	\N	\N	\N	Gordioidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26825	16873	Nectonematidae	76525	\N	\N	\N	\N	Nectonematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26826	16875	Valenciniidae	76560	\N	\N	\N	\N	Valenciniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26827	16875	Lineidae	76543	\N	\N	\N	\N	Lineidae<Heteronemertea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26828	16875	Incertae Sedis Heteronemertea	76540	\N	\N	\N	\N	Incertae Sedis Heteronemertea<Heteronemertea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26829	16875	Cerebratulidae	76534	\N	\N	\N	\N	Cerebratulidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26830	16875	Baseodiscidae	76531	\N	\N	\N	\N	Baseodiscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26831	16874	Tubulanidae	76586	\N	\N	\N	\N	Tubulanidae<Paleonemertea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26832	16874	Incertae Sedis Paleonemertea	76581	\N	\N	\N	\N	Incertae Sedis Paleonemertea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26833	16874	Hubrechtidae	76577	\N	\N	\N	\N	Hubrechtidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26834	16874	Environmental Paleonemertea 1	76574	\N	\N	\N	\N	Environmental Paleonemertea 1<Paleonemertea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26835	16874	Cephalothricidae	76568	\N	\N	\N	\N	Cephalothricidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26836	16874	Carinomidae	76564	\N	\N	\N	\N	Carinomidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26837	16877	Bdellonemertea	76603	\N	\N	\N	\N	Bdellonemertea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26838	16876	Polystilifera	76686	\N	\N	\N	\N	Polystilifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26839	16876	Monostilifera	76613	\N	\N	\N	\N	Monostilifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26840	16876	Incertae Sedis Hoplonemertea	76610	\N	\N	\N	\N	Incertae Sedis Hoplonemertea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26841	16876	Environmental Hoplonemertea 1	76607	\N	\N	\N	\N	Environmental Hoplonemertea 1<Hoplonemertea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26842	16879	Diplomma serpentina	76699	\N	\N	\N	\N	Diplomma serpentina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26843	16879	Diplomma polyophthalma	76698	\N	\N	\N	\N	Diplomma polyophthalma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26844	16878	Pseudomicrura afzelii	76701	\N	\N	\N	\N	Pseudomicrura afzelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26845	16880	Nemertea XXX	76710	\N	\N	\N	\N	Nemertea XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26846	16880	Nemertean	76708	\N	\N	\N	\N	Nemertean	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26847	16880	Lineidae	76706	\N	\N	\N	\N	Lineidae<Nemertea XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26848	16880	Antiponemertes	76704	\N	\N	\N	\N	Antiponemertes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26849	16881	Ooperipatellus	76715	\N	\N	\N	\N	Ooperipatellus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26850	16882	Peripatus sp.	76719	\N	\N	\N	\N	Peripatus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26851	16889	Euperipatoides leuckartii	76722	\N	\N	\N	\N	Euperipatoides leuckartii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26852	16888	Metaperipatus inae	76724	\N	\N	\N	\N	Metaperipatus inae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26853	16887	Ooperipatus silvanus	76729	\N	\N	\N	\N	Ooperipatus silvanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26854	16887	Ooperipatus nebulosus	76728	\N	\N	\N	\N	Ooperipatus nebulosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26855	16887	Ooperipatus caesius	76727	\N	\N	\N	\N	Ooperipatus caesius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26856	16887	Ooperipatus birrgus	76726	\N	\N	\N	\N	Ooperipatus birrgus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26857	16886	Opisthopatus cinctipes	76731	\N	\N	\N	\N	Opisthopatus cinctipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26858	16885	Peripatoides sp.	76734	\N	\N	\N	\N	Peripatoides sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26859	16885	Peripatoides novaezealandiae	76733	\N	\N	\N	\N	Peripatoides novaezealandiae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26860	16884	Peripatopsis stelliporata	76741	\N	\N	\N	\N	Peripatopsis stelliporata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26861	16884	Peripatopsis sedgwicki	76740	\N	\N	\N	\N	Peripatopsis sedgwicki	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26862	16884	Peripatopsis moseleyi	76739	\N	\N	\N	\N	Peripatopsis moseleyi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26863	16884	Peripatopsis clavigera	76738	\N	\N	\N	\N	Peripatopsis clavigera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26864	16884	Peripatopsis capensis	76737	\N	\N	\N	\N	Peripatopsis capensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26865	16884	Peripatopsis balfouri	76736	\N	\N	\N	\N	Peripatopsis balfouri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26866	16883	Planipapillus vittatus	76748	\N	\N	\N	\N	Planipapillus vittatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26867	16883	Planipapillus tectus	76747	\N	\N	\N	\N	Planipapillus tectus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26868	16883	Planipapillus impacris	76746	\N	\N	\N	\N	Planipapillus impacris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26869	16883	Planipapillus cyclus	76745	\N	\N	\N	\N	Planipapillus cyclus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26870	16883	Planipapillus berti	76744	\N	\N	\N	\N	Planipapillus berti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26871	16883	Planipapillus annae	76743	\N	\N	\N	\N	Planipapillus annae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26872	16899	Trichoplax sp.	76764	\N	\N	\N	\N	Trichoplax sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26873	16899	Trichoplax adhaerens	76763	\N	\N	\N	\N	Trichoplax adhaerens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26874	16902	Paracatenula	76772	\N	\N	\N	\N	Paracatenula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26875	16902	Catenula	76768	\N	\N	\N	\N	Catenula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26876	16901	Catenulida X sp.	76780	\N	\N	\N	\N	Catenulida X sp.<Catenulida X<Catenulida<Platyhelminthes	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26877	16900	Stenostomum	76784	\N	\N	\N	\N	Stenostomum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26878	16900	Rhynchoscolex	76782	\N	\N	\N	\N	Rhynchoscolex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26879	16904	Schizocoerus	76810	\N	\N	\N	\N	Schizocoerus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26880	16904	Gyrocotylidea	76805	\N	\N	\N	\N	Gyrocotylidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26881	16904	Amphilinidea	76798	\N	\N	\N	\N	Amphilinidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26882	16903	Vittirhynchus	77320	\N	\N	\N	\N	Vittirhynchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26883	16903	Trypanorhyncha	77187	\N	\N	\N	\N	Trypanorhyncha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26884	16903	Trygonicola	77185	\N	\N	\N	\N	Trygonicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26885	16903	Tetraphyllidea	77137	\N	\N	\N	\N	Tetraphyllidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26886	16903	Tetrabothriidea	77132	\N	\N	\N	\N	Tetrabothriidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26887	16903	Spathebothriidea	77123	\N	\N	\N	\N	Spathebothriidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26888	16903	Scalithrium	77121	\N	\N	\N	\N	Scalithrium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26889	16903	Rhinebothriinae	77119	\N	\N	\N	\N	Rhinebothriinae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26890	16903	Rhinebothriidea	77097	\N	\N	\N	\N	Rhinebothriidea<Eucestoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26891	16903	Pseudophyllidea	77047	\N	\N	\N	\N	Pseudophyllidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26892	16903	Pseudogrillotia	77045	\N	\N	\N	\N	Pseudogrillotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26893	16903	Proteocephalidea	77016	\N	\N	\N	\N	Proteocephalidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26894	16903	Nippotaeniidea	77010	\N	\N	\N	\N	Nippotaeniidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26895	16903	Monobothrium	77008	\N	\N	\N	\N	Monobothrium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26896	16903	Microsomacanthus	77006	\N	\N	\N	\N	Microsomacanthus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26897	16903	Lyruterina	77004	\N	\N	\N	\N	Lyruterina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26898	16903	Litobothriidea	77000	\N	\N	\N	\N	Litobothriidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26899	16903	Lecanicephalidea	76991	\N	\N	\N	\N	Lecanicephalidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26900	16903	Lanfrediella	76989	\N	\N	\N	\N	Lanfrediella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26901	16903	Incertae Sedis Eucestoda	76986	\N	\N	\N	\N	Incertae Sedis Eucestoda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26902	16903	Haplobothriidea	76983	\N	\N	\N	\N	Haplobothriidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26903	16903	Glanitaenia	76981	\N	\N	\N	\N	Glanitaenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26904	16903	Fuhrmannetta	76979	\N	\N	\N	\N	Fuhrmannetta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26905	16903	Fimbriaria	76977	\N	\N	\N	\N	Fimbriaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26906	16903	Eucestoda X	76975	\N	\N	\N	\N	Eucestoda X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26907	16903	Diphyllobothriidea	76950	\N	\N	\N	\N	Diphyllobothriidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26908	16903	Diphyllidea	76938	\N	\N	\N	\N	Diphyllidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26909	16903	Cyclophyllidea	76864	\N	\N	\N	\N	Cyclophyllidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26910	16903	Choanotaenia	76862	\N	\N	\N	\N	Choanotaenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26911	16903	Chimaerarhynchus	76860	\N	\N	\N	\N	Chimaerarhynchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26912	16903	Cathetocephalidea	76855	\N	\N	\N	\N	Cathetocephalidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26913	16903	Caryophyllidea	76817	\N	\N	\N	\N	Caryophyllidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26914	16903	Balanotaenia	76815	\N	\N	\N	\N	Balanotaenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26915	16903	Andrya	76813	\N	\N	\N	\N	Andrya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26916	16906	Udonellidae	77654	\N	\N	\N	\N	Udonellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26917	16906	Tetraonchidae	77651	\N	\N	\N	\N	Tetraonchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26918	16906	Sundanonchidae	77648	\N	\N	\N	\N	Sundanonchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26919	16906	Sciadicleithrum	77646	\N	\N	\N	\N	Sciadicleithrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26920	16906	Pseudomurraytrematidae	77643	\N	\N	\N	\N	Pseudomurraytrematidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26921	16906	Pseudodactylogyridae	77635	\N	\N	\N	\N	Pseudodactylogyridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26922	16906	Protogyrodactylus	77632	\N	\N	\N	\N	Protogyrodactylus<Monopisthocotylea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26923	16906	Ooegyrodactylidae	77629	\N	\N	\N	\N	Ooegyrodactylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26924	16906	Neobenedenia	77627	\N	\N	\N	\N	Neobenedenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26925	16906	Monopisthocotylea X	77625	\N	\N	\N	\N	Monopisthocotylea X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26926	16906	Monocotylidae	77618	\N	\N	\N	\N	Monocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26927	16906	Microbothriidae	77615	\N	\N	\N	\N	Microbothriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26928	16906	Incertae Sedis Monopisthocotylea	77612	\N	\N	\N	\N	Incertae Sedis Monopisthocotylea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26929	16906	Hexabothriidae	77609	\N	\N	\N	\N	Hexabothriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26930	16906	Gyrodactylidae	77574	\N	\N	\N	\N	Gyrodactylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26931	16906	Diplectanidae	77528	\N	\N	\N	\N	Diplectanidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26932	16906	Dactylogyridae	77457	\N	\N	\N	\N	Dactylogyridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26933	16906	Cichlidogyridae	77429	\N	\N	\N	\N	Cichlidogyridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26934	16906	Capsalidae	77421	\N	\N	\N	\N	Capsalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26935	16906	Anoplodiscidae	77418	\N	\N	\N	\N	Anoplodiscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26936	16906	Ancyrocephalidae	77352	\N	\N	\N	\N	Ancyrocephalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26937	16906	Ancylodiscoididae	77326	\N	\N	\N	\N	Ancylodiscoididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26938	16906	Allobenedenia	77324	\N	\N	\N	\N	Allobenedenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26939	16905	Sphyranuridae	77784	\N	\N	\N	\N	Sphyranuridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26940	16905	Polystomatidae	77721	\N	\N	\N	\N	Polystomatidae<Polyopisthocotylea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26941	16905	Plectanocotylidae	77718	\N	\N	\N	\N	Plectanocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26942	16905	Neothoracocotylidae	77713	\N	\N	\N	\N	Neothoracocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26943	16905	Microcotylidae	77699	\N	\N	\N	\N	Microcotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26944	16905	Mazocraeidae	77694	\N	\N	\N	\N	Mazocraeidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26945	16905	Gotocotylidae	77690	\N	\N	\N	\N	Gotocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26946	16905	Gastrocotylidae	77687	\N	\N	\N	\N	Gastrocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26947	16905	Discocotylidae	77684	\N	\N	\N	\N	Discocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26948	16905	Diplozoidae	77681	\N	\N	\N	\N	Diplozoidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26949	16905	Diclidophoridae	77668	\N	\N	\N	\N	Diclidophoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26950	16905	Axinidae	77665	\N	\N	\N	\N	Axinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26951	16905	Allodiscocotylidae	77662	\N	\N	\N	\N	Allodiscocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26952	16914	Environmental Rhabditophora 1	77789	\N	\N	\N	\N	Environmental Rhabditophora 1<Environmental Rhabditophora 1<Rhabditophora	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26953	16913	Prorhynchidae	77793	\N	\N	\N	\N	Prorhynchidae<Lecithoepitheliata	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26954	16912	Macrostomorpha X	77831	\N	\N	\N	\N	Macrostomorpha X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26955	16912	Macrostomida	77803	\N	\N	\N	\N	Macrostomida<Macrostomorpha<Rhabditophora<Platyhelminthes	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26956	16912	Haplopharyngida	77800	\N	\N	\N	\N	Haplopharyngida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26957	16911	Urastomidae	77834	\N	\N	\N	\N	Urastomidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26958	16910	Stylochoplana	77867	\N	\N	\N	\N	Stylochoplana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26959	16910	Pseudostylochus	77865	\N	\N	\N	\N	Pseudostylochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26960	16910	Polycladida X	77863	\N	\N	\N	\N	Polycladida X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26961	16910	Maritigrella	77861	\N	\N	\N	\N	Maritigrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26962	16910	Cotylea	77852	\N	\N	\N	\N	Cotylea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26963	16910	Acotylea	77841	\N	\N	\N	\N	Acotylea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26964	16909	Separata	77892	\N	\N	\N	\N	Separata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26965	16909	Proporata	77870	\N	\N	\N	\N	Proporata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26966	16908	Typhloplanoida	78142	\N	\N	\N	\N	Typhloplanoida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26967	26970	Thylacorhynchus	78140	\N	\N	\N	\N	Thylacorhynchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26968	16908	Rhabdocoela X	78138	\N	\N	\N	\N	Rhabdocoela X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26969	16908	Neodalyellida	77992	\N	\N	\N	\N	Neodalyellida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26970	16908	Kalyptorhynchia	77957	\N	\N	\N	\N	Kalyptorhynchia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26971	16908	Dalyellioida	77918	\N	\N	\N	\N	Dalyellioida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26972	16908	Ciliopharyngiella	77916	\N	\N	\N	\N	Ciliopharyngiella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26973	16907	Uterioporus	78311	\N	\N	\N	\N	Uterioporus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26974	16907	Tricladida	78223	\N	\N	\N	\N	Tricladida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26975	16907	Proseriata	78165	\N	\N	\N	\N	Proseriata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26976	16907	Peraclistus	78163	\N	\N	\N	\N	Peraclistus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26977	16907	Novibipalium	78161	\N	\N	\N	\N	Novibipalium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26978	16907	Minona	78159	\N	\N	\N	\N	Minona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26979	16907	Crenobia	78157	\N	\N	\N	\N	Crenobia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26980	16907	Bothrioplanida	78154	\N	\N	\N	\N	Bothrioplanida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26981	16916	Rugogastridae	78330	\N	\N	\N	\N	Rugogastridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26982	16916	Multicalycidae	78327	\N	\N	\N	\N	Multicalycidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26983	16916	Aspidogastridae	78315	\N	\N	\N	\N	Aspidogastridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26984	16915	Tandanicolidae	78986	\N	\N	\N	\N	Tandanicolidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26985	16915	Synthesium	78983	\N	\N	\N	\N	Synthesium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26986	16915	Strigeidida	78841	\N	\N	\N	\N	Strigeidida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26987	16915	Stellantchasmus	78839	\N	\N	\N	\N	Stellantchasmus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26988	16915	Spirorchid	78837	\N	\N	\N	\N	Spirorchid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26989	16915	Spirorchidae	78835	\N	\N	\N	\N	Spirorchidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26990	16915	Skoulekia	78833	\N	\N	\N	\N	Skoulekia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26991	16915	Sanguinicolid	78831	\N	\N	\N	\N	Sanguinicolid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26992	16915	Rhabdiopoeus	78829	\N	\N	\N	\N	Rhabdiopoeus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26993	16915	Ragaia	78827	\N	\N	\N	\N	Ragaia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26994	16915	Prosthogonimus	78825	\N	\N	\N	\N	Prosthogonimus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26995	16915	Procerovum	78822	\N	\N	\N	\N	Procerovum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26996	16915	Polylekithum	78820	\N	\N	\N	\N	Polylekithum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26997	16915	Plagiorchiida	78639	\N	\N	\N	\N	Plagiorchiida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
26998	16915	Paramphistomidae	78637	\N	\N	\N	\N	Paramphistomidae<Digenea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
26999	16915	Paradeontacylix	78635	\N	\N	\N	\N	Paradeontacylix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27000	16915	Opisthorchis	78633	\N	\N	\N	\N	Opisthorchis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27001	16915	Opisthorchiida	78565	\N	\N	\N	\N	Opisthorchiida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27002	16915	Notocotylidae	78563	\N	\N	\N	\N	Notocotylidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27003	16915	Macrovestibulum	78561	\N	\N	\N	\N	Macrovestibulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27004	16915	Macrobilharzia	78559	\N	\N	\N	\N	Macrobilharzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27005	16915	Lepidapedon	78556	\N	\N	\N	\N	Lepidapedon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27006	16915	Lecithophyllum	78554	\N	\N	\N	\N	Lecithophyllum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27007	16915	Lecithobotrys	78552	\N	\N	\N	\N	Lecithobotrys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27008	16915	Koseiria	78550	\N	\N	\N	\N	Koseiria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27009	16915	Hysterolecithoides	78548	\N	\N	\N	\N	Hysterolecithoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27010	16915	Heterophyopsis	78546	\N	\N	\N	\N	Heterophyopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27011	16915	Hapalotrema	78544	\N	\N	\N	\N	Hapalotrema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27012	16915	Gymnophalloides	78542	\N	\N	\N	\N	Gymnophalloides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27013	16915	Griphobilharzia	78540	\N	\N	\N	\N	Griphobilharzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27014	16915	Fellodistomum	78538	\N	\N	\N	\N	Fellodistomum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27015	16915	Faustulidae	78531	\N	\N	\N	\N	Faustulidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27016	16915	Environmental Digenea 1	78527	\N	\N	\N	\N	Environmental Digenea 1<Digenea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27017	16915	Echinostomida	78421	\N	\N	\N	\N	Echinostomida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27018	16915	Diplostomoidea	78419	\N	\N	\N	\N	Diplostomoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27019	16915	Digenea incertae sedis	78415	\N	\N	\N	\N	Digenea incertae sedis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27020	16915	Crepidostomum	78413	\N	\N	\N	\N	Crepidostomum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27021	16915	Concinnum	78411	\N	\N	\N	\N	Concinnum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27022	16915	Clinostomid	78409	\N	\N	\N	\N	Clinostomid	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27023	16915	Campula	78407	\N	\N	\N	\N	Campula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27024	16915	Bunodera	78405	\N	\N	\N	\N	Bunodera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27025	16915	Brachylaimoidea	78399	\N	\N	\N	\N	Brachylaimoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27026	16915	Bivitellobilharzia	78397	\N	\N	\N	\N	Bivitellobilharzia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27027	16915	Azygiida	78338	\N	\N	\N	\N	Azygiida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27028	16915	Avian	78336	\N	\N	\N	\N	Avian	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27029	16915	Acipensericola	78334	\N	\N	\N	\N	Acipensericola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27030	16918	Catenulida X	78991	\N	\N	\N	\N	Catenulida X<Catenulida<Turbellaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27031	26970	Schizorhynchus	78994	\N	\N	\N	\N	Schizorhynchus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27032	16920	Lithonida	79053	\N	\N	\N	\N	Lithonida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27033	16920	Leucosolenida	79004	\N	\N	\N	\N	Leucosolenida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27034	16920	Baerida	78999	\N	\N	\N	\N	Baerida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27035	16919	Murrayonida	79084	\N	\N	\N	\N	Murrayonida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27036	16919	Clathrinida	79059	\N	\N	\N	\N	Clathrinida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27037	16945	Acanthochaetetes wellsi	79091	\N	\N	\N	\N	Acanthochaetetes wellsi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27038	16944	Agelas	79093	\N	\N	\N	\N	Agelas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27039	16943	Geodia	79102	\N	\N	\N	\N	Geodia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27040	16942	Axos cliftoni	79107	\N	\N	\N	\N	Axos cliftoni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27041	16941	Clathria reinwardti	79109	\N	\N	\N	\N	Clathria reinwardti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27042	16940	Crambe crambe	79111	\N	\N	\N	\N	Crambe crambe	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27043	16939	Vaceletia	79113	\N	\N	\N	\N	Vaceletia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27044	16938	Demospongiae X sp.	79116	\N	\N	\N	\N	Demospongiae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27045	16937	Pleraplysilla	79124	\N	\N	\N	\N	Pleraplysilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27046	16937	Igernella	79122	\N	\N	\N	\N	Igernella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27047	16937	Halisarca	79120	\N	\N	\N	\N	Halisarca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27048	16937	Aplysilla	79118	\N	\N	\N	\N	Aplysilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27049	16936	Spongia	79145	\N	\N	\N	\N	Spongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27050	16936	Smenospongia	79143	\N	\N	\N	\N	Smenospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27051	16936	Sarcotragus	79141	\N	\N	\N	\N	Sarcotragus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27052	16936	Lamellodysidea	79139	\N	\N	\N	\N	Lamellodysidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27053	16936	Ircinia	79135	\N	\N	\N	\N	Ircinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27054	16936	Hyattella	79133	\N	\N	\N	\N	Hyattella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27055	16936	Hippospongia	79130	\N	\N	\N	\N	Hippospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27056	16936	Dysidea	79127	\N	\N	\N	\N	Dysidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27057	16935	Discodermia sp.	79148	\N	\N	\N	\N	Discodermia sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27058	16934	Environmental Ceractinomorpha 1	79150	\N	\N	\N	\N	Environmental Ceractinomorpha 1<Environmental Ceractinomorpha 1	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27059	16933	Environmental Demospongiae 1	79153	\N	\N	\N	\N	Environmental Demospongiae 1<Environmental Demospongiae 1<Demospongiae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27060	16932	Environmental Tetractinomorpha 1	79157	\N	\N	\N	\N	Environmental Tetractinomorpha 1<Environmental Tetractinomorpha 1	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27061	90709	Trachycladus	79189	\N	\N	\N	\N	Trachycladus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27062	90713	Tethya	79186	\N	\N	\N	\N	Tethya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27063	16931	Suberitidae	79183	\N	\N	\N	\N	Suberitidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27064	16931	Suberites	79180	\N	\N	\N	\N	Suberites<Hadromerida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27065	90711	Spheciospongia	79178	\N	\N	\N	\N	Spheciospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27066	90718	Rhizaxinella	79176	\N	\N	\N	\N	Rhizaxinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27067	90718	Pseudosuberites	79174	\N	\N	\N	\N	Pseudosuberites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27068	16944	Prosuberites	79172	\N	\N	\N	\N	Prosuberites<Agelasida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27069	90716	Polymastia	79170	\N	\N	\N	\N	Polymastia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27070	90711	Placospongia	79168	\N	\N	\N	\N	Placospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27071	90711	Diplastrella	79166	\N	\N	\N	\N	Diplastrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27072	88642	Chondrosia	79163	\N	\N	\N	\N	Chondrosia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27073	88643	Chondrilla	79160	\N	\N	\N	\N	Chondrilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27074	16930	Topsentia	79244	\N	\N	\N	\N	Topsentia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27075	16930	Spongosorites	79242	\N	\N	\N	\N	Spongosorites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27076	16930	Scopalina	79240	\N	\N	\N	\N	Scopalina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27077	16930	Reniochalina	79238	\N	\N	\N	\N	Reniochalina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27078	16930	Ptilocaulis	79234	\N	\N	\N	\N	Ptilocaulis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27079	16930	Phycopsis	79232	\N	\N	\N	\N	Phycopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27080	16930	Phakellia	79229	\N	\N	\N	\N	Phakellia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27081	16930	Myrmekioderma	79227	\N	\N	\N	\N	Myrmekioderma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27082	16930	Hymeniacidon	79223	\N	\N	\N	\N	Hymeniacidon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27083	16930	Halichondria	79220	\N	\N	\N	\N	Halichondria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27084	16930	Dragmacidon	79216	\N	\N	\N	\N	Dragmacidon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27085	16930	Didiscus	79214	\N	\N	\N	\N	Didiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27086	16930	Dictyonella	79211	\N	\N	\N	\N	Dictyonella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27087	16930	Cymbastela	79209	\N	\N	\N	\N	Cymbastela	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27088	16930	Axinella	79196	\N	\N	\N	\N	Axinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27089	16930	Acanthella	79192	\N	\N	\N	\N	Acanthella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27090	16929	Xestospongia	79316	\N	\N	\N	\N	Xestospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27091	16929	Trochospongilla	79313	\N	\N	\N	\N	Trochospongilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27092	16929	Swartschewskia	79311	\N	\N	\N	\N	Swartschewskia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27093	16929	Spongilla	79307	\N	\N	\N	\N	Spongilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27094	16929	Siphonochalina	79305	\N	\N	\N	\N	Siphonochalina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27095	16929	Petrosia	79303	\N	\N	\N	\N	Petrosia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27096	16929	Pachydictyum	79300	\N	\N	\N	\N	Pachydictyum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27097	16929	Oceanapia	79298	\N	\N	\N	\N	Oceanapia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27098	16929	Nudospongilla	79296	\N	\N	\N	\N	Nudospongilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27099	16929	Niphates	79294	\N	\N	\N	\N	Niphates	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27100	16929	Metaniidae	79291	\N	\N	\N	\N	Metaniidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27101	16929	Haliclona	79284	\N	\N	\N	\N	Haliclona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27102	16929	Eunapius	79280	\N	\N	\N	\N	Eunapius	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27103	16929	Ephydatia	79274	\N	\N	\N	\N	Ephydatia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27104	16929	Echinospongilla	79272	\N	\N	\N	\N	Echinospongilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27105	16929	Dasychalina	79270	\N	\N	\N	\N	Dasychalina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27106	16929	Cribrochalina	79268	\N	\N	\N	\N	Cribrochalina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27107	16929	Corvomeyenia	79266	\N	\N	\N	\N	Corvomeyenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27108	16929	Chalinula	79264	\N	\N	\N	\N	Chalinula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27109	16929	Calyx	79261	\N	\N	\N	\N	Calyx	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27110	16929	Callyspongia	79258	\N	\N	\N	\N	Callyspongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27111	16929	Baikalospongia	79254	\N	\N	\N	\N	Baikalospongia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27112	16929	Amphimedon	79251	\N	\N	\N	\N	Amphimedon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27113	16929	Aka	79249	\N	\N	\N	\N	Aka	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27114	16929	Acanthostrongylophora	79247	\N	\N	\N	\N	Acanthostrongylophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27115	16928	Corallistes	79319	\N	\N	\N	\N	Corallistes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27116	16927	Lubomirskia baicalensis	79323	\N	\N	\N	\N	Lubomirskia baicalensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27117	16927	Lubomirskia abietina	79322	\N	\N	\N	\N	Lubomirskia abietina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27118	16926	Tedania	79354	\N	\N	\N	\N	Tedania	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27119	16926	Poecilosclerida sp.	79353	\N	\N	\N	\N	Poecilosclerida sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27120	16926	Phorbas	79351	\N	\N	\N	\N	Phorbas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27121	16926	Negombata	79348	\N	\N	\N	\N	Negombata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27122	16926	Mycale	79343	\N	\N	\N	\N	Mycale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27123	16926	Microciona	79341	\N	\N	\N	\N	Microciona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27124	16926	Iotrochota	79339	\N	\N	\N	\N	Iotrochota	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27125	16926	Eurypon	79337	\N	\N	\N	\N	Eurypon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27126	16926	Ectyoplasia	79335	\N	\N	\N	\N	Ectyoplasia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27127	16926	Desmapsamma	79333	\N	\N	\N	\N	Desmapsamma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27128	16926	Crella	79331	\N	\N	\N	\N	Crella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27129	16926	Celtodoryx	79329	\N	\N	\N	\N	Celtodoryx	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27130	16926	Biemna	79327	\N	\N	\N	\N	Biemna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27131	16926	Axechina	79325	\N	\N	\N	\N	Axechina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27132	16925	Tetilla	79366	\N	\N	\N	\N	Tetilla	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27133	16925	Craniella	79364	\N	\N	\N	\N	Craniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27134	16925	Cinachyrella	79359	\N	\N	\N	\N	Cinachyrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27135	16925	Aciculites	79357	\N	\N	\N	\N	Aciculites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27136	16924	Theonella sp.	79369	\N	\N	\N	\N	Theonella sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27137	16923	Timea sp.	79371	\N	\N	\N	\N	Timea sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27138	16922	Verongula	79388	\N	\N	\N	\N	Verongula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27139	16922	Hexadella	79386	\N	\N	\N	\N	Hexadella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27140	16922	Aplysina	79375	\N	\N	\N	\N	Aplysina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27141	16922	Aiolochroia	79373	\N	\N	\N	\N	Aiolochroia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27142	16921	Vetulina stalactites	79391	\N	\N	\N	\N	Vetulina stalactites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27143	16947	Amphidiscosida	79394	\N	\N	\N	\N	Amphidiscosida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27144	16946	Lyssacinosida	79420	\N	\N	\N	\N	Lyssacinosida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27145	16946	Hexactinosida	79402	\N	\N	\N	\N	Hexactinosida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27146	16948	Pseudocorticium	79492	\N	\N	\N	\N	Pseudocorticium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27147	16948	Plakortis	79488	\N	\N	\N	\N	Plakortis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27148	16948	Plakinastrella	79485	\N	\N	\N	\N	Plakinastrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27149	16948	Plakina	79480	\N	\N	\N	\N	Plakina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27150	16948	Oscarella	79473	\N	\N	\N	\N	Oscarella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27151	16948	Corticium	79470	\N	\N	\N	\N	Corticium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27152	16949	Psilocalyx	79505	\N	\N	\N	\N	Psilocalyx	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27153	16949	Margaritella	79503	\N	\N	\N	\N	Margaritella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27154	16949	Lonchiphora	79501	\N	\N	\N	\N	Lonchiphora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27155	16949	Hexactinella	79499	\N	\N	\N	\N	Hexactinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27156	16949	Aspidoscopulia	79496	\N	\N	\N	\N	Aspidoscopulia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27157	16952	Halicryptus spinulosus	79510	\N	\N	\N	\N	Halicryptus spinulosus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27158	16951	Priapulopsis bicaudatus	79512	\N	\N	\N	\N	Priapulopsis bicaudatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27159	16950	Priapulus caudatus	79514	\N	\N	\N	\N	Priapulus caudatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27160	16953	Priapulida XXX	79517	\N	\N	\N	\N	Priapulida XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27161	16955	Meiopriapulus sp.	79522	\N	\N	\N	\N	Meiopriapulus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27162	16955	Meiopriapulus fijiensis	79521	\N	\N	\N	\N	Meiopriapulus fijiensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27163	16954	Tubiluchus troglodytes	79526	\N	\N	\N	\N	Tubiluchus troglodytes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27164	16954	Tubiluchus sp.	79525	\N	\N	\N	\N	Tubiluchus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27165	16954	Tubiluchus corallicola	79524	\N	\N	\N	\N	Tubiluchus corallicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27166	16960	Adinetidae	79530	\N	\N	\N	\N	Adinetidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27167	16959	Environmental Bdelloidea 1	79534	\N	\N	\N	\N	Environmental Bdelloidea 1<Environmental Bdelloidea 1<Bdelloidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27168	16958	Philodinavus	79538	\N	\N	\N	\N	Philodinavus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27169	16957	Philodinidae	79541	\N	\N	\N	\N	Philodinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27170	16956	Rotaria	79558	\N	\N	\N	\N	Rotaria<Rotaria<Bdelloidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27171	16963	Testudinellidae	79583	\N	\N	\N	\N	Testudinellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27172	16963	Flosculariidae	79573	\N	\N	\N	\N	Flosculariidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27173	16963	Filinidae	79570	\N	\N	\N	\N	Filinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27174	16963	Conochilidae	79566	\N	\N	\N	\N	Conochilidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27175	16962	Trichotriidae	79673	\N	\N	\N	\N	Trichotriidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27176	16962	Trichocercidae	79668	\N	\N	\N	\N	Trichocercidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27177	16962	Synchaetidae	79662	\N	\N	\N	\N	Synchaetidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27178	16962	Scaridiidae	79659	\N	\N	\N	\N	Scaridiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27179	16962	Proalidae	79654	\N	\N	\N	\N	Proalidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27180	16962	Notommatidae	79643	\N	\N	\N	\N	Notommatidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27181	16962	Microcodonidae	79640	\N	\N	\N	\N	Microcodonidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27182	16962	Lindiidae	79636	\N	\N	\N	\N	Lindiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27183	16962	Lepadellidae	79632	\N	\N	\N	\N	Lepadellidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27184	16962	Lecanidae	79627	\N	\N	\N	\N	Lecanidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27185	16962	Gastropidae	79624	\N	\N	\N	\N	Gastropidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27186	16962	Epiphanidae	79621	\N	\N	\N	\N	Epiphanidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27187	16962	Environmental Ploimida 1	79618	\N	\N	\N	\N	Environmental Ploimida 1<Ploimida	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27188	16962	Dicranophoridae	79612	\N	\N	\N	\N	Dicranophoridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27189	16962	Brachionidae	79592	\N	\N	\N	\N	Brachionidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27190	16962	Asplanchnidae	79587	\N	\N	\N	\N	Asplanchnidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27191	16964	Trichotria	79680	\N	\N	\N	\N	Trichotria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27192	16964	Rotifera XXX	79678	\N	\N	\N	\N	Rotifera XXX	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27193	16965	Seison sp.	79685	\N	\N	\N	\N	Seison sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27194	16965	Seison nebaliae	79684	\N	\N	\N	\N	Seison nebaliae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27195	16966	Sipunculidea	79724	\N	\N	\N	\N	Sipunculidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27196	16966	Phascolosomatidea	79692	\N	\N	\N	\N	Phascolosomatidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27197	16966	Incertae Sedis Sipuncula	79689	\N	\N	\N	\N	Incertae Sedis Sipuncula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27198	16968	Milnesiidae	79767	\N	\N	\N	\N	Milnesiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27199	16967	Macrobiotidae	79817	\N	\N	\N	\N	Macrobiotidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27200	16967	Hypsibiidae	79784	\N	\N	\N	\N	Hypsibiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27201	16967	Eohypsibiidae	79781	\N	\N	\N	\N	Eohypsibiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27202	16967	Environmental Parachela 9	79778	\N	\N	\N	\N	Environmental Parachela 9<Parachela	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27203	16967	Environmental Parachela 7	79775	\N	\N	\N	\N	Environmental Parachela 7<Parachela	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27204	16967	Calohypsibiidae	79772	\N	\N	\N	\N	Calohypsibiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27205	16970	Batillipedidae	85500	\N	\N	\N	\N	Batillipedidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27206	16970	Halechiniscidae	79844	\N	\N	\N	\N	Halechiniscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27207	16969	Echiniscoididae	79886	\N	\N	\N	\N	Echiniscoididae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27208	16969	Echiniscidae	79851	\N	\N	\N	\N	Echiniscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27209	16971	Tardigrada XXX	79903	\N	\N	\N	\N	Tardigrada XXX<Tardigrada XX<Tardigrada X<Tardigrada	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27210	16971	Tardigrada XxX	79901	\N	\N	\N	\N	Tardigrada XxX<Tardigrada XX<Tardigrada X<Tardigrada	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27211	16971	Tardigrada xXX	79899	\N	\N	\N	\N	Tardigrada xXX<Tardigrada XX<Tardigrada X<Tardigrada	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27212	16971	Tardigrada	79897	\N	\N	\N	\N	Tardigrada<Tardigrada XX	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27213	16971	Oreella	79895	\N	\N	\N	\N	Oreella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27214	16971	Mopsechiniscus	79893	\N	\N	\N	\N	Mopsechiniscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27215	16971	Antechiniscus	79891	\N	\N	\N	\N	Antechiniscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27216	16974	Opisthokonta XXXXX sp.	79921	\N	\N	\N	\N	Opisthokonta XXXXX sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27217	17002	Goniomonas 2 pacifica	80340	\N	\N	\N	\N	Goniomonas 2 pacifica<Goniomonas 2<Goniomonas 2	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27218	17002	Goniomonas 2 avonlea	80339	\N	\N	\N	\N	Goniomonas 2 avonlea<Goniomonas 2<Goniomonas 2	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27219	17010	Diacronema vlkianum	80444	\N	\N	\N	\N	Diacronema vlkianum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27220	17010	Diacronema sp.	80443	\N	\N	\N	\N	Diacronema sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27221	17010	Diacronema lutheri	80442	\N	\N	\N	\N	Diacronema lutheri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27222	17009	Exanthemachrysis sp.	80448	\N	\N	\N	\N	Exanthemachrysis sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27223	17009	Exanthemachrysis gayraliae	80447	\N	\N	\N	\N	Exanthemachrysis gayraliae<Exanthemachrysis	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27224	17009	Exanthemachrysis cf gayraliae	80446	\N	\N	\N	\N	Exanthemachrysis cf gayraliae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27225	17008	Pavlova viridis	80460	\N	\N	\N	\N	Pavlova viridis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27226	17008	Pavlova virescens	80459	\N	\N	\N	\N	Pavlova virescens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27227	17008	Pavlova sp. CCMP459	80458	\N	\N	\N	\N	Pavlova sp. CCMP459	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27228	17008	Pavlova sp.	80457	\N	\N	\N	\N	Pavlova sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27229	17008	Pavlova pseudogranifera	80456	\N	\N	\N	\N	Pavlova pseudogranifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27230	17008	Pavlova pinguis	80455	\N	\N	\N	\N	Pavlova pinguis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27231	17008	Pavlova noctivaga	80454	\N	\N	\N	\N	Pavlova noctivaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27232	17008	Pavlova lutheri	80453	\N	\N	\N	\N	Pavlova lutheri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27233	17008	Pavlova gyrans	80452	\N	\N	\N	\N	Pavlova gyrans<Pavlova	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27234	17008	Pavlova granifera	80451	\N	\N	\N	\N	Pavlova granifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27235	17008	Pavlova ennorea	80450	\N	\N	\N	\N	Pavlova ennorea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27236	17007	Rebecca sp.	80463	\N	\N	\N	\N	Rebecca sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27237	17007	Rebecca salina	80462	\N	\N	\N	\N	Rebecca salina<Rebecca	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27238	17006	Undescribed hapto-sp-CCMP2436	80465	\N	\N	\N	\N	Undescribed hapto-sp-CCMP2436	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27239	17014	Calcidiscus sp.	85688	\N	\N	\N	\N	Calcidiscus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27240	17014	Calcidiscus quadriperforatus	80473	\N	\N	\N	\N	Calcidiscus quadriperforatus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27241	17014	Calcidiscus leptoporus	80472	\N	\N	\N	\N	Calcidiscus leptoporus<Calcidiscus	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27242	17013	Oolithotus fragilis	80475	\N	\N	\N	\N	Oolithotus fragilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27243	17012	Umbilicosphaera sibogae	80478	\N	\N	\N	\N	Umbilicosphaera sibogae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27244	17012	Umbilicosphaera hulburtiana	80477	\N	\N	\N	\N	Umbilicosphaera hulburtiana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27245	17016	Calyptrosphaera sphaeroidea	80483	\N	\N	\N	\N	Calyptrosphaera sphaeroidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27246	17016	Calyptrosphaera sp.	80482	\N	\N	\N	\N	Calyptrosphaera sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27247	17016	Calyptrosphaera radiata	80481	\N	\N	\N	\N	Calyptrosphaera radiata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27248	17015	Helladosphaera sp.	80485	\N	\N	\N	\N	Helladosphaera sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27249	17018	Coccolithus pelagicus ssp braarudi, Strain PLY182g	80490	\N	\N	\N	\N	Coccolithus pelagicus ssp braarudi, Strain PLY182g	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27250	17018	Coccolithus pelagicus	80489	\N	\N	\N	\N	Coccolithus pelagicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27251	17018	Coccolithus braarudii	80488	\N	\N	\N	\N	Coccolithus braarudii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27252	17017	Cruciplacolithus sp.	85689	\N	\N	\N	\N	Cruciplacolithus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27253	17017	Cruciplacolithus neohelis	80492	\N	\N	\N	\N	Cruciplacolithus neohelis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27254	17019	Holococcolithophorid sp.	80496	\N	\N	\N	\N	Holococcolithophorid sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27255	17024	Hymenomonas globosa	80500	\N	\N	\N	\N	Hymenomonas globosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27256	17024	Hymenomonas coronata	80499	\N	\N	\N	\N	Hymenomonas coronata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27257	17023	Isochrysis like sp.	80502	\N	\N	\N	\N	Isochrysis like sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27258	17022	Jomonlithus littoralis	80504	\N	\N	\N	\N	Jomonlithus littoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27259	17021	Ochrosphaera verrucosa	80508	\N	\N	\N	\N	Ochrosphaera verrucosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27260	17021	Ochrosphaera sp.	80507	\N	\N	\N	\N	Ochrosphaera sp.<Ochrosphaera<Hymenomonadaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27261	17021	Ochrosphaera neapolitana	80506	\N	\N	\N	\N	Ochrosphaera neapolitana<Ochrosphaera	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27262	17026	Pleurochrysidaceae X sp.	80511	\N	\N	\N	\N	Pleurochrysidaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27263	17025	Pleurochrysis sp.	80521	\N	\N	\N	\N	Pleurochrysis sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27264	17025	Pleurochrysis scherffelii	80520	\N	\N	\N	\N	Pleurochrysis scherffelii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27265	17025	Pleurochrysis roscoffensis	80519	\N	\N	\N	\N	Pleurochrysis roscoffensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27266	17025	Pleurochrysis pseudoroscoffensis	80518	\N	\N	\N	\N	Pleurochrysis pseudoroscoffensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27267	17025	Pleurochrysis placolithoides	80517	\N	\N	\N	\N	Pleurochrysis placolithoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27268	17025	Pleurochrysis gayraliae	80516	\N	\N	\N	\N	Pleurochrysis gayraliae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27269	17025	Pleurochrysis elongata	80515	\N	\N	\N	\N	Pleurochrysis elongata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27270	17025	Pleurochrysis dentata	80514	\N	\N	\N	\N	Pleurochrysis dentata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27271	17025	Pleurochrysis carterae	80513	\N	\N	\N	\N	Pleurochrysis carterae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27272	17027	Reticulosphaera socialis	80524	\N	\N	\N	\N	Reticulosphaera socialis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27273	17035	Chrysotila sp.	80529	\N	\N	\N	\N	Chrysotila sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27274	17035	Chrysotila lamellosa	80528	\N	\N	\N	\N	Chrysotila lamellosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27275	17034	Dicrateria sp.	80531	\N	\N	\N	\N	Dicrateria sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27276	17033	Haptophyceae sp.	80533	\N	\N	\N	\N	Haptophyceae sp.<Haptophyceae<Isochrysidaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27277	17032	Isochrysidaceae X sp.	80535	\N	\N	\N	\N	Isochrysidaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27278	17031	Isochrysis nuda	85691	\N	\N	\N	\N	Isochrysis nuda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27279	17031	Isochrysis gaditana	85690	\N	\N	\N	\N	Isochrysis gaditana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27280	17031	Isochrysis sp. CCMP1324	80541	\N	\N	\N	\N	Isochrysis sp. CCMP1324	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27281	17031	Isochrysis sp CCMP1244	80540	\N	\N	\N	\N	Isochrysis sp CCMP1244<Isochrysis	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27282	17031	Isochrysis sp.	80539	\N	\N	\N	\N	Isochrysis sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27283	17031	Isochrysis litoralis	80538	\N	\N	\N	\N	Isochrysis litoralis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27284	17031	Isochrysis galbana	80537	\N	\N	\N	\N	Isochrysis galbana	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27285	17029	Pseudoisochrysis paradoxa	80544	\N	\N	\N	\N	Pseudoisochrysis paradoxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27286	17041	Coccoid haptophyte sp.	80549	\N	\N	\N	\N	Coccoid haptophyte sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27287	17040	Emiliania sp.	80556	\N	\N	\N	\N	Emiliania sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27288	17040	Emiliania huxleyi PLY M219	80555	\N	\N	\N	\N	Emiliania huxleyi PLY M219	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27289	17040	Emiliania huxleyi CCMP370	80554	\N	\N	\N	\N	Emiliania huxleyi CCMP370	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27290	17040	Emiliania huxleyi 379	80553	\N	\N	\N	\N	Emiliania huxleyi 379	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27291	17040	Emiliania huxleyi 374	80552	\N	\N	\N	\N	Emiliania huxleyi 374	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27292	17040	Emiliania huxleyi	80551	\N	\N	\N	\N	Emiliania huxleyi<Emiliania	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27293	17039	Emiliania Gephyrocapsa sp.	80558	\N	\N	\N	\N	Emiliania Gephyrocapsa sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27294	17038	Gephyrocapsa sp.	80562	\N	\N	\N	\N	Gephyrocapsa sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27295	17038	Gephyrocapsa oceanica, Strain RCC1303	80561	\N	\N	\N	\N	Gephyrocapsa oceanica, Strain RCC1303	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27296	17038	Gephyrocapsa oceanica	80560	\N	\N	\N	\N	Gephyrocapsa oceanica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27297	17037	Noelaerhabdaceae X sp.	80564	\N	\N	\N	\N	Noelaerhabdaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27298	17044	Haptophyceae sp.	80568	\N	\N	\N	\N	Haptophyceae sp.<Haptophyceae<Phaeocystaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27299	17043	Phaeocystaceae X sp.	80570	\N	\N	\N	\N	Phaeocystaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27300	17042	Phaeocystis environmental5	86757	\N	\N	\N	\N	Phaeocystis environmental5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27301	17042	Phaeocystis environmental4	86756	\N	\N	\N	\N	Phaeocystis environmental4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27302	17042	Phaeocystis environmental3	86755	\N	\N	\N	\N	Phaeocystis environmental3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27303	17042	Phaeocystis environmental2	86754	\N	\N	\N	\N	Phaeocystis environmental2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27304	17042	Phaeocystis environmental1	86753	\N	\N	\N	\N	Phaeocystis environmental1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27305	17042	Phaeocystis rex	85692	\N	\N	\N	\N	Phaeocystis rex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27306	17042	Phaeocystis sp. CCMP2710	80578	\N	\N	\N	\N	Phaeocystis sp. CCMP2710	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27307	17042	Phaeocystis sp.	80577	\N	\N	\N	\N	Phaeocystis sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27308	17042	Phaeocystis pouchetii	80576	\N	\N	\N	\N	Phaeocystis pouchetii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27309	17042	Phaeocystis jahnii	80575	\N	\N	\N	\N	Phaeocystis jahnii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27310	17042	Phaeocystis globosa	80574	\N	\N	\N	\N	Phaeocystis globosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27311	17042	Phaeocystis cordata	80573	\N	\N	\N	\N	Phaeocystis cordata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27312	17042	Phaeocystis antarctica	80572	\N	\N	\N	\N	Phaeocystis antarctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27313	17047	Chrysoculter rhomboideus RCC1486	80588	\N	\N	\N	\N	Chrysoculter rhomboideus RCC1486	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27314	17047	Chrysoculter rhomboideus	80587	\N	\N	\N	\N	Chrysoculter rhomboideus<Chrysoculter<Chrysoculteraceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27315	17050	Chrysochromulinaceae X sp.	80594	\N	\N	\N	\N	Chrysochromulinaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27316	17049	Chrysochromulina elegans	85695	\N	\N	\N	\N	Chrysochromulina elegans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27317	17049	Chrysochromulina camella	85694	\N	\N	\N	\N	Chrysochromulina camella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27318	17049	Chrysochromulina apheles	85693	\N	\N	\N	\N	Chrysochromulina apheles	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27319	17049	Chrysochromulina X sp.	80620	\N	\N	\N	\N	Chrysochromulina X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27320	17049	Chrysochromulina throndsenii	80619	\N	\N	\N	\N	Chrysochromulina throndsenii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27321	17049	Chrysochromulina strobilus	80618	\N	\N	\N	\N	Chrysochromulina strobilus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27322	17049	Chrysochromulina sp. strain6	80617	\N	\N	\N	\N	Chrysochromulina sp. strain6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27323	17049	Chrysochromulina sp. strain35	80616	\N	\N	\N	\N	Chrysochromulina sp. strain35	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27324	17049	Chrysochromulina sp. strain23	80615	\N	\N	\N	\N	Chrysochromulina sp. strain23	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27325	17049	Chrysochromulina sp. strain18	80614	\N	\N	\N	\N	Chrysochromulina sp. strain18	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27326	17049	Chrysochromulina sp. strain17	80613	\N	\N	\N	\N	Chrysochromulina sp. strain17	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27327	17049	Chrysochromulina sp. strain13	80612	\N	\N	\N	\N	Chrysochromulina sp. strain13	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27328	17049	Chrysochromulina sp.	80611	\N	\N	\N	\N	Chrysochromulina sp.<Chrysochromulina	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27329	17049	Chrysochromulina simplex	80610	\N	\N	\N	\N	Chrysochromulina simplex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27330	17049	Chrysochromulina scutellum	80609	\N	\N	\N	\N	Chrysochromulina scutellum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27331	17049	Chrysochromulina rotalis UIO044	80608	\N	\N	\N	\N	Chrysochromulina rotalis UIO044	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27332	17049	Chrysochromulina rotalis	80607	\N	\N	\N	\N	Chrysochromulina rotalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27333	17049	Chrysochromulina polylepis	80606	\N	\N	\N	\N	Chrysochromulina polylepis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27334	17049	Chrysochromulina parva	80605	\N	\N	\N	\N	Chrysochromulina parva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27335	17049	Chrysochromulina parkeae	80604	\N	\N	\N	\N	Chrysochromulina parkeae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27336	17049	Chrysochromulina ni	80603	\N	\N	\N	\N	Chrysochromulina ni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27337	17049	Chrysochromulina leadbeateri	80602	\N	\N	\N	\N	Chrysochromulina leadbeateri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27338	17049	Chrysochromulina ericina CCMP281	80601	\N	\N	\N	\N	Chrysochromulina ericina CCMP281	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27339	17049	Chrysochromulina cymbium	80600	\N	\N	\N	\N	Chrysochromulina cymbium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27340	17049	Chrysochromulina campanulifera	80599	\N	\N	\N	\N	Chrysochromulina campanulifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27341	17049	Chrysochromulina brevifilum UTEX LB 985	80598	\N	\N	\N	\N	Chrysochromulina brevifilum UTEX LB 985	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27342	17049	Chrysochromulina birgeri	80597	\N	\N	\N	\N	Chrysochromulina birgeri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27343	17049	Chrysochromulina acantha	80596	\N	\N	\N	\N	Chrysochromulina acantha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27344	17059	Dicrateria inornata	80623	\N	\N	\N	\N	Dicrateria inornata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27345	17058	Haptolina sp.	80630	\N	\N	\N	\N	Haptolina sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27346	17058	Haptolina hirta	80629	\N	\N	\N	\N	Haptolina hirta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27347	17058	Haptolina herdlensis	80628	\N	\N	\N	\N	Haptolina herdlensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27348	17058	Haptolina fragaria	80627	\N	\N	\N	\N	Haptolina fragaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27349	17058	Haptolina ericina	80626	\N	\N	\N	\N	Haptolina ericina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27350	17058	Haptolina brevifila	80625	\N	\N	\N	\N	Haptolina brevifila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27351	17057	Imantonia sp.	80633	\N	\N	\N	\N	Imantonia sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27352	17057	Imantonia rotunda	80632	\N	\N	\N	\N	Imantonia rotunda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27353	17056	Platychrysis sp.	80635	\N	\N	\N	\N	Platychrysis sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27354	17055	Prorocentrum minimum	80637	\N	\N	\N	\N	Prorocentrum minimum<Prorocentrum<Prymnesiaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27355	17054	Prymensium sp.	80639	\N	\N	\N	\N	Prymensium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27356	17053	Prymnesiaceae X sp.	80641	\N	\N	\N	\N	Prymnesiaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27357	17052	Prymnesium patilliferum	85696	\N	\N	\N	\N	Prymnesium patilliferum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27358	17052	Prymnesium zebrinum	80660	\N	\N	\N	\N	Prymnesium zebrinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27359	17052	Prymnesium sp.	80659	\N	\N	\N	\N	Prymnesium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27360	17052	Prymnesium simplex	80658	\N	\N	\N	\N	Prymnesium simplex	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27361	17052	Prymnesium radiatum	80657	\N	\N	\N	\N	Prymnesium radiatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27362	17052	Prymnesium polylepis	80656	\N	\N	\N	\N	Prymnesium polylepis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27363	17052	Prymnesium pigrum	80655	\N	\N	\N	\N	Prymnesium pigrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27364	17052	Prymnesium pienaarii	80654	\N	\N	\N	\N	Prymnesium pienaarii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27365	17052	Prymnesium parvum f patellifera	80653	\N	\N	\N	\N	Prymnesium parvum f patellifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27366	17052	Prymnesium parvum	80652	\N	\N	\N	\N	Prymnesium parvum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27367	17052	Prymnesium palpebrale	80651	\N	\N	\N	\N	Prymnesium palpebrale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27368	17052	Prymnesium neolepis	80650	\N	\N	\N	\N	Prymnesium neolepis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27369	17052	Prymnesium nemamethecum	80649	\N	\N	\N	\N	Prymnesium nemamethecum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27370	17052	Prymnesium minus	80648	\N	\N	\N	\N	Prymnesium minus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27371	17052	Prymnesium kappa	80647	\N	\N	\N	\N	Prymnesium kappa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27372	17052	Prymnesium faveolatum	80646	\N	\N	\N	\N	Prymnesium faveolatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27373	17052	Prymnesium chiton	80645	\N	\N	\N	\N	Prymnesium chiton	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27374	17052	Prymnesium calathiferum	80644	\N	\N	\N	\N	Prymnesium calathiferum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27375	17052	Prymnesium annuliferum	80643	\N	\N	\N	\N	Prymnesium annuliferum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27376	17051	Pseudohaptolina arctica	80662	\N	\N	\N	\N	Pseudohaptolina arctica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27377	17062	Chrysocampanula spinifera	80665	\N	\N	\N	\N	Chrysocampanula spinifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27378	17060	Prymnesiophyceae XXX sp.	80668	\N	\N	\N	\N	Prymnesiophyceae XXX sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27379	17063	Braarudosphaera bigelowii	80672	\N	\N	\N	\N	Braarudosphaera bigelowii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27380	17068	Coronosphaera mediterranea	80680	\N	\N	\N	\N	Coronosphaera mediterranea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27381	17067	Syracosphaeraceae X sp.	80682	\N	\N	\N	\N	Syracosphaeraceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27382	17066	Syracosphaera pulchra	80684	\N	\N	\N	\N	Syracosphaera pulchra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27383	17070	Helicosphaera carteri	80690	\N	\N	\N	\N	Helicosphaera carteri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27384	17072	Scyphosphaera apsteinii	80693	\N	\N	\N	\N	Scyphosphaera apsteinii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27385	17073	Algirosphaera robusta	80696	\N	\N	\N	\N	Algirosphaera robusta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27386	17074	Ascetosporea U1 X1 sp.	80824	\N	\N	\N	\N	Ascetosporea U1 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27387	17075	Ascetosporea U2 X1 sp.	80827	\N	\N	\N	\N	Ascetosporea U2 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27388	17076	Ascetosporea U3 X1 sp. NewEndo	80831	\N	\N	\N	\N	Ascetosporea U3 X1 sp. NewEndo	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27389	17076	Ascetosporea U3 X1 sp.	80830	\N	\N	\N	\N	Ascetosporea U3 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27390	17077	Ascetosporea U4 X1 sp.	80834	\N	\N	\N	\N	Ascetosporea U4 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27391	17078	Ascetosporea U5 X1 sp. T8	80838	\N	\N	\N	\N	Ascetosporea U5 X1 sp. T8	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27392	17078	Ascetosporea U5 X1 sp.	80837	\N	\N	\N	\N	Ascetosporea U5 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27393	17083	Minchinia lineage	80936	\N	\N	\N	\N	Minchinia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27394	17083	Haplosporidium 4 lineage	80928	\N	\N	\N	\N	Haplosporidium 4 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27395	17083	Haplosporidium 3 lineage	80924	\N	\N	\N	\N	Haplosporidium 3 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27396	17083	Haplosporidium 2 lineage	80921	\N	\N	\N	\N	Haplosporidium 2 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27397	17083	Haplosporidium 1 lineage	80905	\N	\N	\N	\N	Haplosporidium 1 lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27398	17083	Haplosporidiidae U9	80902	\N	\N	\N	\N	Haplosporidiidae U9	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27399	17083	Haplosporidiidae U8	80899	\N	\N	\N	\N	Haplosporidiidae U8	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27400	17083	Haplosporidiidae U7	80896	\N	\N	\N	\N	Haplosporidiidae U7	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27401	17083	Haplosporidiidae U6	80891	\N	\N	\N	\N	Haplosporidiidae U6	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27402	17083	Haplosporidiidae U5	80886	\N	\N	\N	\N	Haplosporidiidae U5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27403	17083	Haplosporidiidae U4	80881	\N	\N	\N	\N	Haplosporidiidae U4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27404	17083	Haplosporidiidae U3	80876	\N	\N	\N	\N	Haplosporidiidae U3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27405	17083	Haplosporidiidae U2	80873	\N	\N	\N	\N	Haplosporidiidae U2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27406	17083	Haplosporidiidae U1	80870	\N	\N	\N	\N	Haplosporidiidae U1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27407	17083	Haplosporidiidae U15	80867	\N	\N	\N	\N	Haplosporidiidae U15	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27408	17083	Haplosporidiidae U14	80864	\N	\N	\N	\N	Haplosporidiidae U14	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27409	17083	Haplosporidiidae U13	80861	\N	\N	\N	\N	Haplosporidiidae U13	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27410	17083	Haplosporidiidae U12	80858	\N	\N	\N	\N	Haplosporidiidae U12	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27411	17083	Haplosporidiidae U11	80855	\N	\N	\N	\N	Haplosporidiidae U11	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27412	17083	Haplosporidiidae U10	80852	\N	\N	\N	\N	Haplosporidiidae U10	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27413	17083	Bonamia lineage	80841	\N	\N	\N	\N	Bonamia lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27414	17082	Haplosporidiida U1 X1	80944	\N	\N	\N	\N	Haplosporidiida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27415	17081	Haplosporidiida U2 X3	80951	\N	\N	\N	\N	Haplosporidiida U2 X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27416	17081	Haplosporidiida U2 X2	80949	\N	\N	\N	\N	Haplosporidiida U2 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27417	17081	Haplosporidiida U2 X1	80947	\N	\N	\N	\N	Haplosporidiida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27418	17080	Haplosporidiida U3 X1	80954	\N	\N	\N	\N	Haplosporidiida U3 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27419	17079	Urosporidium	80959	\N	\N	\N	\N	Urosporidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27420	17079	Urosporidiidae X1	80957	\N	\N	\N	\N	Urosporidiidae X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27421	17085	Mikrocytos sp.	80967	\N	\N	\N	\N	Mikrocytos sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27422	17085	Mikrocytos mimicus	80966	\N	\N	\N	\N	Mikrocytos mimicus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27423	17085	Mikrocytos mackini	80965	\N	\N	\N	\N	Mikrocytos mackini	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27424	17085	Mikrocytos boweri	80964	\N	\N	\N	\N	Mikrocytos boweri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27425	17084	Paramikrocytos canceri	80969	\N	\N	\N	\N	Paramikrocytos canceri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27426	17091	Paradiniida X1 sp.	80972	\N	\N	\N	\N	Paradiniida X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27427	17090	Paradiniida X2 sp.	80974	\N	\N	\N	\N	Paradiniida X2 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27428	17089	Paradiniida X3 sp.	80976	\N	\N	\N	\N	Paradiniida X3 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27429	17088	Paradiniida X4 sp. T1	80979	\N	\N	\N	\N	Paradiniida X4 sp. T1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27430	17088	Paradiniida X4 sp.	80978	\N	\N	\N	\N	Paradiniida X4 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27431	17087	Paradiniida X5 sp. T2	80982	\N	\N	\N	\N	Paradiniida X5 sp. T2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27432	17087	Paradiniida X5 sp.	80981	\N	\N	\N	\N	Paradiniida X5 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27433	17086	Paradinium sp. T5	80986	\N	\N	\N	\N	Paradinium sp. T5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27434	17086	Paradinium sp.	80985	\N	\N	\N	\N	Paradinium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27435	17086	Paradinium poucheti	80984	\N	\N	\N	\N	Paradinium poucheti	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27436	17095	Marteilia refringens	80990	\N	\N	\N	\N	Marteilia refringens	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27437	17095	Marteilia burrensoni	80989	\N	\N	\N	\N	Marteilia burrensoni	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27438	17094	Marteilioides chungmuensis	80992	\N	\N	\N	\N	Marteilioides chungmuensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27439	17093	Paramyxida X1 sp.	80994	\N	\N	\N	\N	Paramyxida X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27440	17092	Paramyxida X2 sp.	80996	\N	\N	\N	\N	Paramyxida X2 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27441	17102	Gromia sphaerica	81014	\N	\N	\N	\N	Gromia sphaerica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27442	17102	Gromia oviformis	81013	\N	\N	\N	\N	Gromia oviformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27443	17107	Filoreta 1 sp. ZMM3208	81020	\N	\N	\N	\N	Filoreta 1 sp. ZMM3208	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27444	17107	Filoreta 1 sp.	81019	\N	\N	\N	\N	Filoreta 1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27445	17107	Filoreta 1 marina	81018	\N	\N	\N	\N	Filoreta 1 marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27446	17106	Filoreta 2 turcica	81023	\N	\N	\N	\N	Filoreta 2 turcica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27447	17106	Filoreta 2 japonica	81022	\N	\N	\N	\N	Filoreta 2 japonica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27448	17105	Filoreta 3 tenera	81025	\N	\N	\N	\N	Filoreta 3 tenera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27449	17104	Filoreta 4 sp. ZMM3203	81028	\N	\N	\N	\N	Filoreta 4 sp. ZMM3203	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27450	17104	Filoreta 4 sp.	81027	\N	\N	\N	\N	Filoreta 4 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27451	17103	Filoreta 5 sp. ZMM3212	81031	\N	\N	\N	\N	Filoreta 5 sp. ZMM3212	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27452	17103	Filoreta 5 sp.	81030	\N	\N	\N	\N	Filoreta 5 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27453	17115	Amorphochlora sp.	81038	\N	\N	\N	\N	Amorphochlora sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27454	17115	Amorphochlora amoeboformis	81037	\N	\N	\N	\N	Amorphochlora amoeboformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27455	17115	Amorphochlora amoebiformis	81036	\N	\N	\N	\N	Amorphochlora amoebiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27456	17114	Bigelowiella sp.	81043	\N	\N	\N	\N	Bigelowiella sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27457	17114	Bigelowiella natans CCMP1258.1	81042	\N	\N	\N	\N	Bigelowiella natans CCMP1258.1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27458	17114	Bigelowiella natans	81041	\N	\N	\N	\N	Bigelowiella natans<Bigelowiella	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27459	17114	Bigelowiella longifila	81040	\N	\N	\N	\N	Bigelowiella longifila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27460	17113	Lotharella amoebiformis	81046	\N	\N	\N	\N	Lotharella amoebiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27461	17113	Chlorarachnida X sp.	81045	\N	\N	\N	\N	Chlorarachnida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27462	17112	Chlorarachnion sp.	81050	\N	\N	\N	\N	Chlorarachnion sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27463	17112	Chlorarachnion reptans CCCM449	81049	\N	\N	\N	\N	Chlorarachnion reptans CCCM449	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27464	17112	Chlorarachnion reptans	81048	\N	\N	\N	\N	Chlorarachnion reptans<Chlorarachnion	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27465	17111	Gymnochlora stellata	81054	\N	\N	\N	\N	Gymnochlora stellata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27466	17111	Gymnochlora sp. CCMP2014	81053	\N	\N	\N	\N	Gymnochlora sp. CCMP2014	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27467	17111	Gymnochlora sp.	81052	\N	\N	\N	\N	Gymnochlora sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27468	17110	Lotharella vacuolata	81061	\N	\N	\N	\N	Lotharella vacuolata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27469	17110	Lotharella sp.	81060	\N	\N	\N	\N	Lotharella sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27470	17110	Lotharella reticulosa	81059	\N	\N	\N	\N	Lotharella reticulosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27471	17110	Lotharella oceanica	81058	\N	\N	\N	\N	Lotharella oceanica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27472	17110	Lotharella globosa	81057	\N	\N	\N	\N	Lotharella globosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27473	17110	Lotharella	81056	\N	\N	\N	\N	Lotharella<Lotharella	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27474	17109	Norrisiella sphaerica	81065	\N	\N	\N	\N	Norrisiella sphaerica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27475	17109	Norisiella sphaerica	81064	\N	\N	\N	\N	Norisiella sphaerica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27476	17109	Norisiella sp.	81063	\N	\N	\N	\N	Norisiella sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27477	17108	Partenskyella glossopodia	81067	\N	\N	\N	\N	Partenskyella glossopodia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27478	17116	LC104 clade X sp.	81070	\N	\N	\N	\N	LC104 clade X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27479	17118	Minorisa clade X sp.	81073	\N	\N	\N	\N	Minorisa clade X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27480	17117	Minorisa sp.	81076	\N	\N	\N	\N	Minorisa sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27481	17117	Minorisa minuta	81075	\N	\N	\N	\N	Minorisa minuta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27482	17119	NPK2 clade X sp.	81079	\N	\N	\N	\N	NPK2 clade X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27483	17120	Discomonas retusa	81083	\N	\N	\N	\N	Discomonas retusa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27484	17122	Discomonadida U1 X1 sp.	81086	\N	\N	\N	\N	Discomonadida U1 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27485	17121	Discomonadida U1 X2 sp.	81088	\N	\N	\N	\N	Discomonadida U1 X2 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27486	17134	CCA17 lineage X sp.	81122	\N	\N	\N	\N	CCA17 lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27487	17137	Hedriocystis	81127	\N	\N	\N	\N	Hedriocystis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27488	17137	Clathrulina	81125	\N	\N	\N	\N	Clathrulina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27489	17136	Desmothoracida U1 X1	81130	\N	\N	\N	\N	Desmothoracida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27490	17135	Desmothoracida U2 X1	81133	\N	\N	\N	\N	Desmothoracida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27491	17139	Gran-1a lineage X	81137	\N	\N	\N	\N	Gran-1a lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27492	17138	Gran-1b lineage X	81140	\N	\N	\N	\N	Gran-1b lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27493	17141	Gran-2a lineage X	81144	\N	\N	\N	\N	Gran-2a lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27494	17140	Gran-2b lineage X	81147	\N	\N	\N	\N	Gran-2b lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27495	17145	Gran-3a lineage X	81151	\N	\N	\N	\N	Gran-3a lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27496	17144	Gran-3b lineage X	81154	\N	\N	\N	\N	Gran-3b lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27497	17143	Gran-3c lineage X	81157	\N	\N	\N	\N	Gran-3c lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27498	17142	Gran-3d lineage X	81160	\N	\N	\N	\N	Gran-3d lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27499	17147	Gran-4a lineage X	81164	\N	\N	\N	\N	Gran-4a lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27500	17146	Gran-4b lineage X	81167	\N	\N	\N	\N	Gran-4b lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27501	17148	Gran-5 lineage X sp.	81171	\N	\N	\N	\N	Gran-5 lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27502	17149	Gran-6 lineage X sp.	81174	\N	\N	\N	\N	Gran-6 lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27503	17151	he2 lineage X sp.	81179	\N	\N	\N	\N	he2 lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27504	17155	Limnofila 1 sp.	81184	\N	\N	\N	\N	Limnofila 1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27505	17155	Limnofila 1 oxoniensis	81183	\N	\N	\N	\N	Limnofila 1 oxoniensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27506	17155	Limnofila 1 borokensis	81182	\N	\N	\N	\N	Limnofila 1 borokensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27507	17154	Limnofila 2 sp.	81187	\N	\N	\N	\N	Limnofila 2 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27508	17154	Limnofila 2 anglica	81186	\N	\N	\N	\N	Limnofila 2 anglica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27509	17153	Limnofila 3 sp.	81190	\N	\N	\N	\N	Limnofila 3 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27510	17153	Limnofila 3 longa	81189	\N	\N	\N	\N	Limnofila 3 longa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27511	17152	Limnofila lineage X sp.	81192	\N	\N	\N	\N	Limnofila lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27512	17157	Massisteria lineage X sp.	81195	\N	\N	\N	\N	Massisteria lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27513	17156	Massisteria sp.	81198	\N	\N	\N	\N	Massisteria sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27514	17156	Massisteria marina	81197	\N	\N	\N	\N	Massisteria marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27515	17158	Mesofila sp.	81202	\N	\N	\N	\N	Mesofila sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27516	17158	Mesofila limnetica	81201	\N	\N	\N	\N	Mesofila limnetica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27517	17159	Minimassisteria sp.	81206	\N	\N	\N	\N	Minimassisteria sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27518	17159	Minimassisteria diva	81205	\N	\N	\N	\N	Minimassisteria diva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27519	17160	Nanofila sp.	81209	\N	\N	\N	\N	Nanofila sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27520	17161	Reticulamoeba sp.	81214	\N	\N	\N	\N	Reticulamoeba sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27521	17161	Reticulamoeba minor	81213	\N	\N	\N	\N	Reticulamoeba minor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27522	17161	Reticulamoeba gemmipara	81212	\N	\N	\N	\N	Reticulamoeba gemmipara	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27523	17167	Pseudocorythion	81231	\N	\N	\N	\N	Pseudocorythion	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27524	17167	Cyphoderiidae X	81229	\N	\N	\N	\N	Cyphoderiidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27525	17167	Cyphoderia	81221	\N	\N	\N	\N	Cyphoderia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27526	17167	Corythionella	81218	\N	\N	\N	\N	Corythionella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27527	17166	Trachelocorythion	81257	\N	\N	\N	\N	Trachelocorythion	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27528	17166	Tracheleuglypha	81255	\N	\N	\N	\N	Tracheleuglypha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27529	17166	Sphenoderia	81249	\N	\N	\N	\N	Sphenoderia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27530	17166	Placocista	81246	\N	\N	\N	\N	Placocista	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27531	17166	Euglypha	81237	\N	\N	\N	\N	Euglypha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27532	17166	Assulina	81234	\N	\N	\N	\N	Assulina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27533	17165	Euglyphida X sp.	81260	\N	\N	\N	\N	Euglyphida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27534	17164	Ovulinata	81262	\N	\N	\N	\N	Ovulinata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27535	17163	Paulinella	81265	\N	\N	\N	\N	Paulinella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27536	17162	Trinema	81273	\N	\N	\N	\N	Trinema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27537	17162	Trinematidae X	81271	\N	\N	\N	\N	Trinematidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27538	17162	Corythion	81269	\N	\N	\N	\N	Corythion	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27539	17168	Novel-clade-3 X sp.	81278	\N	\N	\N	\N	Novel-clade-3 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27540	17169	Novel-clade-4b X sp.	81281	\N	\N	\N	\N	Novel-clade-4b X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27541	17170	Novel-clade-1b X sp.	81284	\N	\N	\N	\N	Novel-clade-1b X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27542	17173	Auranticordis quadriverberis	81287	\N	\N	\N	\N	Auranticordis quadriverberis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27543	17172	Marimonadida X sp.	81289	\N	\N	\N	\N	Marimonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27544	17171	Pseudopirsonia sp.	81292	\N	\N	\N	\N	Pseudopirsonia sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27545	17171	Pseudopirsonia mucosa	81291	\N	\N	\N	\N	Pseudopirsonia mucosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27546	17175	Spongomonadida X sp.	81295	\N	\N	\N	\N	Spongomonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27547	17174	Spongomonas sp.	81299	\N	\N	\N	\N	Spongomonas sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27548	17174	Spongomonas solitaria	81298	\N	\N	\N	\N	Spongomonas solitaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27549	17174	Spongomonas minima	81297	\N	\N	\N	\N	Spongomonas minima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27550	17181	Esquamula	81302	\N	\N	\N	\N	Esquamula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27551	17180	Peregrinia	81305	\N	\N	\N	\N	Peregrinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27552	17179	unclassified Thaumatomastigidae	81353	\N	\N	\N	\N	unclassified Thaumatomastigidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27553	17179	Thaumatospina	81348	\N	\N	\N	\N	Thaumatospina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27554	17179	Thaumatomonas	81332	\N	\N	\N	\N	Thaumatomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27555	17179	Thaumatomonadidae X4	81330	\N	\N	\N	\N	Thaumatomonadidae X4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27556	17179	Thaumatomonadidae X3	81328	\N	\N	\N	\N	Thaumatomonadidae X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27557	17179	Thaumatomonadidae X2	81326	\N	\N	\N	\N	Thaumatomonadidae X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27558	17179	Thaumatomonadidae X1	81324	\N	\N	\N	\N	Thaumatomonadidae X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27559	17179	Scutellomonas	81321	\N	\N	\N	\N	Scutellomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27560	17179	Reckertia	81317	\N	\N	\N	\N	Reckertia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27561	17179	Ovaloplaca	81314	\N	\N	\N	\N	Ovaloplaca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27562	17179	Allas	81309	\N	\N	\N	\N	Allas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27563	17178	Thaumatomonadida U1 X1	81356	\N	\N	\N	\N	Thaumatomonadida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27564	17177	Thaumatomonadida U2 X1	81359	\N	\N	\N	\N	Thaumatomonadida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27565	17176	Thaumatomonadida X sp.	81362	\N	\N	\N	\N	Thaumatomonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27566	17184	Clautriavia	81365	\N	\N	\N	\N	Clautriavia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27567	17183	Novel-clade-2 X	81368	\N	\N	\N	\N	Novel-clade-2 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27568	17182	Nudifilidae X	81373	\N	\N	\N	\N	Nudifilidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27569	17182	Nudifila	81371	\N	\N	\N	\N	Nudifila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27570	17191	Eocercomonas	81433	\N	\N	\N	\N	Eocercomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27571	17191	Cercomonas	81395	\N	\N	\N	\N	Cercomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27572	17191	Cercomonadidae X	81393	\N	\N	\N	\N	Cercomonadidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27573	17191	Cavernomonas	81390	\N	\N	\N	\N	Cavernomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27574	17190	Paracercomonas	81450	\N	\N	\N	\N	Paracercomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27575	17190	Paracercomonadidae X1	81448	\N	\N	\N	\N	Paracercomonadidae X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27576	17190	Nucleocercomonas	81446	\N	\N	\N	\N	Nucleocercomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27577	17190	Metabolomonas	81443	\N	\N	\N	\N	Metabolomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27578	17190	Brevimastigomonas	81441	\N	\N	\N	\N	Brevimastigomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27579	17202	Teretomonas	81489	\N	\N	\N	\N	Teretomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27580	17202	Group-Te	81487	\N	\N	\N	\N	Group-Te	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27581	17202	Allapsidae X	81485	\N	\N	\N	\N	Allapsidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27582	17202	Allapsa	81477	\N	\N	\N	\N	Allapsa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27583	17202	Allantion	81474	\N	\N	\N	\N	Allantion	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27584	17201	Bodomorpha	81493	\N	\N	\N	\N	Bodomorpha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27585	17200	Clade T X2	81500	\N	\N	\N	\N	Clade T X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27586	17200	Clade T X1	81498	\N	\N	\N	\N	Clade T X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27587	17199	Clade U X1	81503	\N	\N	\N	\N	Clade U X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27588	17198	Clade Y X	81506	\N	\N	\N	\N	Clade Y X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27589	17197	Clade Z X	81509	\N	\N	\N	\N	Clade Z X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27590	17196	Dujardinidae X	81514	\N	\N	\N	\N	Dujardinidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27591	17196	Dujardina	81512	\N	\N	\N	\N	Dujardina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27592	17195	Glissomonadida X sp.	81517	\N	\N	\N	\N	Glissomonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27593	17194	Proleptomonas	81519	\N	\N	\N	\N	Proleptomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27594	17193	Sandonidae X	81544	\N	\N	\N	\N	Sandonidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27595	17193	Sandona	81537	\N	\N	\N	\N	Sandona	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27596	17193	Neoheteromita	81531	\N	\N	\N	\N	Neoheteromita	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27597	17193	Mollimonas	81527	\N	\N	\N	\N	Mollimonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27598	17193	Flectomonas	81523	\N	\N	\N	\N	Flectomonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27599	17192	Viridiraptor	81551	\N	\N	\N	\N	Viridiraptor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27600	17192	Viridiraptoridae X	81549	\N	\N	\N	\N	Viridiraptoridae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27601	17192	Orciraptor	81547	\N	\N	\N	\N	Orciraptor	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27602	17205	Agitata	81556	\N	\N	\N	\N	Agitata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27603	17204	Aurigamonas	81560	\N	\N	\N	\N	Aurigamonas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27604	17203	Pansomonadida X sp.	81577	\N	\N	\N	\N	Pansomonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27605	17203	Pansomonadida X5	81575	\N	\N	\N	\N	Pansomonadida X5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27606	17203	Pansomonadida X4	81573	\N	\N	\N	\N	Pansomonadida X4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27607	17203	Pansomonadida X3b	81571	\N	\N	\N	\N	Pansomonadida X3b	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27608	17203	Pansomonadida X3a	81569	\N	\N	\N	\N	Pansomonadida X3a	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27609	17203	Pansomonadida X2b	81567	\N	\N	\N	\N	Pansomonadida X2b	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27610	17203	Pansomonadida X2a	81565	\N	\N	\N	\N	Pansomonadida X2a	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27611	17203	Pansomonadida X1	81563	\N	\N	\N	\N	Pansomonadida X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27612	17208	Cholamonas cyrtodiopsidis	81580	\N	\N	\N	\N	Cholamonas cyrtodiopsidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27613	17207	Helkesimastix marina	81582	\N	\N	\N	\N	Helkesimastix marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27614	17206	Sainouron acronematica	81584	\N	\N	\N	\N	Sainouron acronematica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27615	17216	Capsellina sp.	81590	\N	\N	\N	\N	Capsellina sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27616	17215	Cryomonadida X sp.	81592	\N	\N	\N	\N	Cryomonadida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27617	17214	Cryothecomonas sp.	81595	\N	\N	\N	\N	Cryothecomonas sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27618	17214	Cryothecomonas aestivalis	81594	\N	\N	\N	\N	Cryothecomonas aestivalis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27619	17213	Protaspa 1 sp.	81599	\N	\N	\N	\N	Protaspa 1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27620	17213	Protaspa 1 longipes	81598	\N	\N	\N	\N	Protaspa 1 longipes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27621	17213	Protaspa 1 grandis	81597	\N	\N	\N	\N	Protaspa 1 grandis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27622	17212	Protaspa 2 obliqua	81601	\N	\N	\N	\N	Protaspa 2 obliqua	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27623	17211	Rhogostoma 1 sp.	81605	\N	\N	\N	\N	Rhogostoma 1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27624	17211	Rhogostoma 1 minus	81604	\N	\N	\N	\N	Rhogostoma 1 minus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27625	17211	Rhogostoma 1 micra	81603	\N	\N	\N	\N	Rhogostoma 1 micra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27626	17210	Rhogostoma 2 schuessleri	81607	\N	\N	\N	\N	Rhogostoma 2 schuessleri	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27627	17220	Ebria lineage X2	81618	\N	\N	\N	\N	Ebria lineage X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27628	17220	Ebria lineage X1	81616	\N	\N	\N	\N	Ebria lineage X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27629	17220	Ebria	81613	\N	\N	\N	\N	Ebria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27630	17220	Botuliforma	81610	\N	\N	\N	\N	Botuliforma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27631	17219	Ebriida U1 X1	81621	\N	\N	\N	\N	Ebriida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27632	17218	Ebriida X sp.	81624	\N	\N	\N	\N	Ebriida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27633	17217	Tagiri1 lineage X	81626	\N	\N	\N	\N	Tagiri1 lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27634	17225	Mataza	81632	\N	\N	\N	\N	Mataza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27635	17225	Mataza-lineage X	81630	\N	\N	\N	\N	Mataza-lineage X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27636	17224	Matazida U1 X	81636	\N	\N	\N	\N	Matazida U1 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27637	17223	Matazida U2 X1	81639	\N	\N	\N	\N	Matazida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27638	17222	Matazida X sp.	81642	\N	\N	\N	\N	Matazida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27639	17221	MMETSP 0087 Strain D1	81645	\N	\N	\N	\N	MMETSP 0087 Strain D1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27640	17221	MMETSP 0086 Strain D1	81644	\N	\N	\N	\N	MMETSP 0086 Strain D1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27641	17230	Concharidae	81648	\N	\N	\N	\N	Concharidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27642	17229	Aulacanthidae	81652	\N	\N	\N	\N	Aulacanthidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27643	17228	Coelodendridae	81656	\N	\N	\N	\N	Coelodendridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27644	17227	Phaeogromida X	81669	\N	\N	\N	\N	Phaeogromida X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27645	17227	Medusettidae	81666	\N	\N	\N	\N	Medusettidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27646	17227	Challengeridae	81660	\N	\N	\N	\N	Challengeridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27647	17226	Aulosphaeridae	81672	\N	\N	\N	\N	Aulosphaeridae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27648	17234	Pseudodifflugia	81677	\N	\N	\N	\N	Pseudodifflugia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27649	17233	Tectofilosida U1 X1	81681	\N	\N	\N	\N	Tectofilosida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27650	17232	Tectofilosida U2 X1	81684	\N	\N	\N	\N	Tectofilosida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27651	17231	Tectofilosida X sp.	81687	\N	\N	\N	\N	Tectofilosida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27652	17235	Novel-Clade-4 X sp.	81690	\N	\N	\N	\N	Novel-Clade-4 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27653	17236	Thecofilosea U2 X1 sp.	81693	\N	\N	\N	\N	Thecofilosea U2 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27654	17238	Ventricleftida U1 X sp.	81699	\N	\N	\N	\N	Ventricleftida U1 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27655	17239	Ventricleftida U2 X sp.	81702	\N	\N	\N	\N	Ventricleftida U2 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27656	17240	Ventricleftida U3 X sp.	81705	\N	\N	\N	\N	Ventricleftida U3 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27657	17242	Ventrifissura sp.	81712	\N	\N	\N	\N	Ventrifissura sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27658	17242	Ventrifissura foliiformis	81711	\N	\N	\N	\N	Ventrifissura foliiformis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27659	17242	Ventrifissura artocarpoidea	81710	\N	\N	\N	\N	Ventrifissura artocarpoidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27660	17243	Verrucomonas sp.	81717	\N	\N	\N	\N	Verrucomonas sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27661	17243	Verrucomonas longifila	81716	\N	\N	\N	\N	Verrucomonas longifila	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27662	17243	Verrucomonas bifida	81715	\N	\N	\N	\N	Verrucomonas bifida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27663	17247	NC10 basal X sp.	81729	\N	\N	\N	\N	NC10 basal X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27664	17248	NC10 type1 X sp.	81732	\N	\N	\N	\N	NC10 type1 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27665	17249	NC10 type2 X sp.	81735	\N	\N	\N	\N	NC10 type2 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27666	17250	NClade 13 X1 sp. NCl13	81738	\N	\N	\N	\N	NClade 13 X1 sp. NCl13	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27667	17251	NClade 14 X1 sp.	81741	\N	\N	\N	\N	NClade 14 X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27668	17252	NClade 12A X sp.	81745	\N	\N	\N	\N	NClade 12A X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27669	17253	NClade 12B X sp.	81748	\N	\N	\N	\N	NClade 12B X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27670	17261	Acanthocolla solidissima	81763	\N	\N	\N	\N	Acanthocolla solidissima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27671	17261	Acanthocolla cruciata	81762	\N	\N	\N	\N	Acanthocolla cruciata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27672	17260	Phyllostaurus cuspidatus	81765	\N	\N	\N	\N	Phyllostaurus cuspidatus<Phyllostaurus<Acantharea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27673	17259	Staurolithium sp.	81767	\N	\N	\N	\N	Staurolithium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27674	17258	Trizona brandti	81769	\N	\N	\N	\N	Trizona brandti<Trizona<Acantharea X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27675	17263	Acantharia III X sp.	81772	\N	\N	\N	\N	Acantharia III X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27676	17264	Acantharia IV X sp.	81775	\N	\N	\N	\N	Acantharia IV X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27677	17265	Ac group I X sp.	81778	\N	\N	\N	\N	Ac group I X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27678	17266	Ac group II X sp.	81781	\N	\N	\N	\N	Ac group II X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27679	17269	Acanthochiasma sp.	81784	\N	\N	\N	\N	Acanthochiasma sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27680	17268	Acanthocyrta haeckeli	81786	\N	\N	\N	\N	Acanthocyrta haeckeli<Acanthocyrta<Ac group VI	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27681	17267	Ac group VI X sp.	81788	\N	\N	\N	\N	Ac group VI X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27682	17281	Tessaropelmidae E1E2	81802	\N	\N	\N	\N	Tessaropelmidae E1E2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27683	17281	Aspidomiidae E1E2	81795	\N	\N	\N	\N	Aspidomiidae E1E2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27684	17281	Acanthophracta E1E2	81791	\N	\N	\N	\N	Acanthophracta E1E2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27685	17280	Acanthophracta E3	81807	\N	\N	\N	\N	Acanthophracta E3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27686	17279	Hexalaspidae E4	81821	\N	\N	\N	\N	Hexalaspidae E4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27687	17279	Dorataspidae E4	81813	\N	\N	\N	\N	Dorataspidae E4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27688	17278	Lithopteridae F1	81825	\N	\N	\N	\N	Lithopteridae F1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27689	17277	Arthracanthida F2	81841	\N	\N	\N	\N	Arthracanthida F2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27690	17277	Amphilitidae F2	81831	\N	\N	\N	\N	Amphilitidae F2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27691	17276	Stauracanthidae F3	81876	\N	\N	\N	\N	Stauracanthidae F3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27692	17276	Acanthometridae F3	81849	\N	\N	\N	\N	Acanthometridae F3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27693	17275	Phyllostauridae F4	81898	\N	\N	\N	\N	Phyllostauridae F4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27694	17274	Arthra Symphy X sp.	81902	\N	\N	\N	\N	Arthra Symphy X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27695	17273	Litholophus sp.	81904	\N	\N	\N	\N	Litholophus sp.<Litholophus<Arthra Symphy	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27696	17272	Lychnaspis giltschi	81906	\N	\N	\N	\N	Lychnaspis giltschi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27697	17271	Phractopelta sarmentosa	81909	\N	\N	\N	\N	Phractopelta sarmentosa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27698	17271	Phractopelta dorataspis	81908	\N	\N	\N	\N	Phractopelta dorataspis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27699	17270	Phyllostaurus claparedi	81911	\N	\N	\N	\N	Phyllostaurus claparedi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27700	17292	Acanthocyrta haeckeli	81914	\N	\N	\N	\N	Acanthocyrta haeckeli<Acanthocyrta<Chaunacanthida C	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27701	17291	Acanthometron sp.	81916	\N	\N	\N	\N	Acanthometron sp.<Acanthometron<Chaunacanthida C	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27702	17290	Amphiacon denticulatus	81918	\N	\N	\N	\N	Amphiacon denticulatus<Amphiacon	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27703	17289	Chaunacanthida X sp.	81920	\N	\N	\N	\N	Chaunacanthida X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27704	17288	Symphyacanthida	81926	\N	\N	\N	\N	Symphyacanthida	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27705	17288	Lithopholus	81924	\N	\N	\N	\N	Lithopholus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27706	17288	Gigartacon C1	81922	\N	\N	\N	\N	Gigartacon C1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27707	17287	Stauracon	81929	\N	\N	\N	\N	Stauracon<Conaconidae C2	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27708	17286	Litholophus	81944	\N	\N	\N	\N	Litholophus<Conaconidae C3	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27709	17286	Litholophus C3	81942	\N	\N	\N	\N	Litholophus C3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27710	17286	Heteracon	81940	\N	\N	\N	\N	Heteracon<Conaconidae C3	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27711	17286	Gigartacon C3	81938	\N	\N	\N	\N	Gigartacon C3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27712	17286	Chaunacanthid C3	81936	\N	\N	\N	\N	Chaunacanthid C3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27713	17286	Amphiacon C3	81934	\N	\N	\N	\N	Amphiacon C3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27714	17286	Acanthocyrta	81932	\N	\N	\N	\N	Acanthocyrta<Conaconidae C3	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27715	17285	Gigartacon muelleri	81948	\N	\N	\N	\N	Gigartacon muelleri<Gigartacon	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27716	17285	Gigartacon fragilis	81947	\N	\N	\N	\N	Gigartacon fragilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27717	17284	Heteracon sp.	81951	\N	\N	\N	\N	Heteracon sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27718	17284	Heteracon biformis	81950	\N	\N	\N	\N	Heteracon biformis<Heteracon<Chaunacanthida C	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27719	17283	Litholophus sp.	81953	\N	\N	\N	\N	Litholophus sp.<Litholophus<Chaunacanthida C	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27720	17282	Stauracon pallidus	81955	\N	\N	\N	\N	Stauracon pallidus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27721	17295	Acanthochiasma	81958	\N	\N	\N	\N	Acanthochiasma<Acanthochiasmidae B2	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27722	17294	Phyllostaurus B1	81964	\N	\N	\N	\N	Phyllostaurus B1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27723	17294	Holacanthida B1 X	81961	\N	\N	\N	\N	Holacanthida B1 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27724	17293	Holacanthida B2 X	81969	\N	\N	\N	\N	Holacanthida B2 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27725	17293	Chaunacanthid B2	81967	\N	\N	\N	\N	Chaunacanthid B2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27726	17297	Trizona	81973	\N	\N	\N	\N	Trizona<Astrolithidae D1	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27727	17296	Staurolithium	81976	\N	\N	\N	\N	Staurolithium<Astrolithidae D2	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27728	17300	RadB group III X sp.	81986	\N	\N	\N	\N	RadB group III X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27729	17301	RadB group II X sp.	81989	\N	\N	\N	\N	RadB group II X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27730	17302	RadB group I X sp.	81992	\N	\N	\N	\N	RadB group I X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27731	17304	Larcopyle butschlii	81995	\N	\N	\N	\N	Larcopyle butschlii<Larcopyle<RadB group IV	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27732	17303	RadB group IV X sp.	81997	\N	\N	\N	\N	RadB group IV X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27733	17306	Sticholonche lineage X sp.	82000	\N	\N	\N	\N	Sticholonche lineage X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27734	17305	Sticholonche sp. JB-2011	82003	\N	\N	\N	\N	Sticholonche sp. JB-2011	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27735	17305	Sticholonche sp.	82002	\N	\N	\N	\N	Sticholonche sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27736	17310	Robertina	82010	\N	\N	\N	\N	Robertina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27737	17309	Rotaliida X	82257	\N	\N	\N	\N	Rotaliida X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27738	17309	R clade 3	82189	\N	\N	\N	\N	R clade 3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27739	17309	R clade 2	82100	\N	\N	\N	\N	R clade 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27740	17309	R clade 1	82058	\N	\N	\N	\N	R clade 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27741	17309	Globigerinacea	82013	\N	\N	\N	\N	Globigerinacea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27742	17308	Valvulina	82294	\N	\N	\N	\N	Valvulina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27743	17308	Trochammina	82291	\N	\N	\N	\N	Trochammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27744	17308	Textularia	82288	\N	\N	\N	\N	Textularia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27745	17308	Spirotextularia	82286	\N	\N	\N	\N	Spirotextularia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27746	17308	Spiroplectammina	82284	\N	\N	\N	\N	Spiroplectammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27747	17308	Siphoniferoides	82282	\N	\N	\N	\N	Siphoniferoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27748	17308	Reophax	82280	\N	\N	\N	\N	Reophax	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27749	17308	Liebusella	82278	\N	\N	\N	\N	Liebusella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27750	17308	Haplophragmoides	82276	\N	\N	\N	\N	Haplophragmoides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27751	17308	Eggerelloides	82274	\N	\N	\N	\N	Eggerelloides	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27752	17308	Eggerella	82272	\N	\N	\N	\N	Eggerella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27753	17308	Bigenerina	82270	\N	\N	\N	\N	Bigenerina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27754	17308	Arenoparrella	82268	\N	\N	\N	\N	Arenoparrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27755	17308	Ammotium	82266	\N	\N	\N	\N	Ammotium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27756	17308	Ammobaculites	82264	\N	\N	\N	\N	Ammobaculites	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27757	17328	Psammosphaera	82300	\N	\N	\N	\N	Psammosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27758	17328	M clade A X1	82298	\N	\N	\N	\N	M clade A X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27759	17327	Micrometula	82313	\N	\N	\N	\N	Micrometula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27760	17327	Bathysiphon 1	82303	\N	\N	\N	\N	Bathysiphon 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27761	17326	M clade B X3	82311	\N	\N	\N	\N	M clade B X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27762	17326	M clade B X2	82309	\N	\N	\N	\N	M clade B X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27763	17326	M clade B X1	82307	\N	\N	\N	\N	M clade B X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27764	17325	Toxisarcon	82355	\N	\N	\N	\N	Toxisarcon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27765	17325	Technitella	82353	\N	\N	\N	\N	Technitella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27766	17325	Syringammina	82350	\N	\N	\N	\N	Syringammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27767	17325	Shinkaiya	82348	\N	\N	\N	\N	Shinkaiya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27768	17325	Saccammina	82346	\N	\N	\N	\N	Saccammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27769	17325	Rhizammina	82343	\N	\N	\N	\N	Rhizammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27770	17325	Rhabdammina 1	82341	\N	\N	\N	\N	Rhabdammina 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27771	17325	M clade C X	82336	\N	\N	\N	\N	M clade C X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27772	17325	M clade C X3	82334	\N	\N	\N	\N	M clade C X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27773	17325	M clade C X2	82332	\N	\N	\N	\N	M clade C X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27774	17325	M clade C X1	82330	\N	\N	\N	\N	M clade C X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27775	17325	Marsipella	82328	\N	\N	\N	\N	Marsipella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27776	17325	Hippocrepinella 3	82326	\N	\N	\N	\N	Hippocrepinella 3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27777	17325	Hippocrepina	82324	\N	\N	\N	\N	Hippocrepina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27778	17325	Gloiogullmia	82321	\N	\N	\N	\N	Gloiogullmia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27779	17325	Cylindrogullmia	82319	\N	\N	\N	\N	Cylindrogullmia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27780	17325	Bathyallogromia	82317	\N	\N	\N	\N	Bathyallogromia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27781	17324	Conqueria	82339	\N	\N	\N	\N	Conqueria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27782	17323	Phainogullmia	82369	\N	\N	\N	\N	Phainogullmia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27783	17323	M clade D X	82367	\N	\N	\N	\N	M clade D X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27784	17323	M clade D X1	82365	\N	\N	\N	\N	M clade D X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27785	17323	Hippocrepinella 1	82362	\N	\N	\N	\N	Hippocrepinella 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27786	17323	Astrorhiza	82360	\N	\N	\N	\N	Astrorhiza	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27787	17322	Vellaria	82384	\N	\N	\N	\N	Vellaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27788	17322	Psammophaga	82380	\N	\N	\N	\N	Psammophaga	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27789	17322	Niveus	82378	\N	\N	\N	\N	Niveus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27790	17322	Nellya	82376	\N	\N	\N	\N	Nellya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27791	17322	M clade E X	82374	\N	\N	\N	\N	M clade E X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27792	17322	Allogromia 2	82372	\N	\N	\N	\N	Allogromia 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27793	17321	Rhabdammina 2	82399	\N	\N	\N	\N	Rhabdammina 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27794	17321	Notodendrodes	82396	\N	\N	\N	\N	Notodendrodes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27795	17321	M clade F X	82394	\N	\N	\N	\N	M clade F X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27796	17321	Hemisphaerammina	82391	\N	\N	\N	\N	Hemisphaerammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27797	17321	Allogromiina	82389	\N	\N	\N	\N	Allogromiina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27798	17320	Nemogullmia	82406	\N	\N	\N	\N	Nemogullmia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27799	17320	M clade G X	82404	\N	\N	\N	\N	M clade G X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27800	17320	Boderia	82402	\N	\N	\N	\N	Boderia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27801	17319	Saccodendron	82420	\N	\N	\N	\N	Saccodendron	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27802	17319	Pelosina	82417	\N	\N	\N	\N	Pelosina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27803	17319	Astrammina	82414	\N	\N	\N	\N	Astrammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27804	17319	Arnoldiellina	82412	\N	\N	\N	\N	Arnoldiellina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27805	17319	Armorella	82410	\N	\N	\N	\N	Armorella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27806	17318	M clade J X	82429	\N	\N	\N	\N	M clade J X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27807	17318	Crithionina 1	82425	\N	\N	\N	\N	Crithionina 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27808	17318	Capsammina	82423	\N	\N	\N	\N	Capsammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27809	17317	Reticulomyxa	82436	\N	\N	\N	\N	Reticulomyxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27810	17317	M clade K X	82434	\N	\N	\N	\N	M clade K X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27811	17317	Haplomyxa	82432	\N	\N	\N	\N	Haplomyxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27812	17316	Ovammina	82449	\N	\N	\N	\N	Ovammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27813	17316	M clade L X	82446	\N	\N	\N	\N	M clade L X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27814	17316	Hippocrepinella 2	82443	\N	\N	\N	\N	Hippocrepinella 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27815	17316	Cribrothalammina	82441	\N	\N	\N	\N	Cribrothalammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27816	17316	Cedhagenia	82439	\N	\N	\N	\N	Cedhagenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27817	17315	M clade M X	82468	\N	\N	\N	\N	M clade M X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27818	17315	Hyperammina	82466	\N	\N	\N	\N	Hyperammina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27819	17315	Edaphoallogromia	82464	\N	\N	\N	\N	Edaphoallogromia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27820	17315	Crithionina 2	82461	\N	\N	\N	\N	Crithionina 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27821	17315	Bowseria	82459	\N	\N	\N	\N	Bowseria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27822	17315	Bathysiphon 2	82457	\N	\N	\N	\N	Bathysiphon 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27823	17315	Allogromia	82455	\N	\N	\N	\N	Allogromia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27824	17315	Allogromia 1	82452	\N	\N	\N	\N	Allogromia 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27825	17314	Tinogullmia	82471	\N	\N	\N	\N	Tinogullmia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27826	17313	Vanhoeffenella	82476	\N	\N	\N	\N	Vanhoeffenella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27827	17313	M clade Van X	82474	\N	\N	\N	\N	M clade Van X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27828	17312	Monothalamids X sp.	82479	\N	\N	\N	\N	Monothalamids X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27829	17311	Soil group 4 X	82481	\N	\N	\N	\N	Soil group 4 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27830	17330	Soritidae	82524	\N	\N	\N	\N	Soritidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27831	17330	Rzehakinidae	82520	\N	\N	\N	\N	Rzehakinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27832	17330	Peneroplidae	82510	\N	\N	\N	\N	Peneroplidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27833	17330	Ophthalmidiidae	82507	\N	\N	\N	\N	Ophthalmidiidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27834	17330	Miliolidae	82498	\N	\N	\N	\N	Miliolidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27835	17330	Massilina lineage	82495	\N	\N	\N	\N	Massilina lineage	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27836	17330	Hauerinidae	82492	\N	\N	\N	\N	Hauerinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27837	17330	Alveolinidae	82485	\N	\N	\N	\N	Alveolinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27838	17329	Spirillinidae	82559	\N	\N	\N	\N	Spirillinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27839	17329	Patellinidae	82556	\N	\N	\N	\N	Patellinidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27840	17329	Ammodiscidae	82553	\N	\N	\N	\N	Ammodiscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27841	17336	Collodaria X sp.	82570	\N	\N	\N	\N	Collodaria X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27842	17335	Collophidium	82572	\N	\N	\N	\N	Collophidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27843	17334	Siphonosphaera	82587	\N	\N	\N	\N	Siphonosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27844	17334	Disolenia	82585	\N	\N	\N	\N	Disolenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27845	17334	Collosphaeridae sp.	82584	\N	\N	\N	\N	Collosphaeridae sp.<Collosphaeridae<Collodaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27846	17334	Collosphaeridae	82582	\N	\N	\N	\N	Collosphaeridae<Collosphaeridae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27847	17334	Collosphaera	82579	\N	\N	\N	\N	Collosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27848	17334	Acrosphaera	82577	\N	\N	\N	\N	Acrosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27849	17333	Thalassophysa	82605	\N	\N	\N	\N	Thalassophysa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27850	17333	Thalassicolla	82603	\N	\N	\N	\N	Thalassicolla<Sphaerozoidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27851	17333	Sphaerozoum	82598	\N	\N	\N	\N	Sphaerozoum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27852	17333	Rhaphidozoum	82596	\N	\N	\N	\N	Rhaphidozoum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27853	17333	Collozoum	82591	\N	\N	\N	\N	Collozoum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27854	17332	Thalassicolla	82608	\N	\N	\N	\N	Thalassicolla<Thalassicollidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27855	17337	Eucyrtidium sp.	82613	\N	\N	\N	\N	Eucyrtidium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27856	17346	Eucyrtidium	82616	\N	\N	\N	\N	Eucyrtidium<Eucyrtidium-Group	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27857	17345	Lithomelissa sp.	82620	\N	\N	\N	\N	Lithomelissa sp.<Lithomelissa<Nassellaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27858	17345	Lithomelissa setosa	82619	\N	\N	\N	\N	Lithomelissa setosa<Lithomelissa<Nassellaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27859	17344	Nassellaria X	82622	\N	\N	\N	\N	Nassellaria X<Nassellaria<Nassellaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27860	17343	Nassellaria X sp.	82625	\N	\N	\N	\N	Nassellaria X sp.<Nassellaria X<Nassellaria<Polycystinea	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27861	17342	Cladoscenium	82627	\N	\N	\N	\N	Cladoscenium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27862	17341	Pterocanium	82635	\N	\N	\N	\N	Pterocanium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27863	17341	Pseudocubus	82633	\N	\N	\N	\N	Pseudocubus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27864	17341	Lithomelissa	82630	\N	\N	\N	\N	Lithomelissa<Plagoniidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27865	17340	Pterocorys	82638	\N	\N	\N	\N	Pterocorys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27866	17339	Eucyrtidium	82643	\N	\N	\N	\N	Eucyrtidium<Theoperidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27867	17339	Artostrobus	82641	\N	\N	\N	\N	Artostrobus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27868	17338	Ceratospyris	82648	\N	\N	\N	\N	Ceratospyris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27869	17353	Styptosphaera	82654	\N	\N	\N	\N	Styptosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27870	17353	Rhizosphaera	82652	\N	\N	\N	\N	Rhizosphaera<Ethmosphaeridae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27871	17352	Tholospyra	82683	\N	\N	\N	\N	Tholospyra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27872	17352	Tetrapyle	82680	\N	\N	\N	\N	Tetrapyle	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27873	17352	Stylodictya	82677	\N	\N	\N	\N	Stylodictya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27874	17352	Streblacantha	82675	\N	\N	\N	\N	Streblacantha	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27875	17352	Spongotrochus	82672	\N	\N	\N	\N	Spongotrochus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27876	17352	Spongopyle	82670	\N	\N	\N	\N	Spongopyle	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27877	17352	Spongodiscus	82667	\N	\N	\N	\N	Spongodiscus<Pyloniidae-Spongodiscidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27878	17352	Spongocore	82665	\N	\N	\N	\N	Spongocore	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27879	17352	Pyloniidae-Spongodiscidae X	82663	\N	\N	\N	\N	Pyloniidae-Spongodiscidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27880	17352	Phorticium	82661	\N	\N	\N	\N	Phorticium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27881	17352	Larcopyle	82659	\N	\N	\N	\N	Larcopyle<Pyloniidae-Spongodiscidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27882	17352	Actinomma	82657	\N	\N	\N	\N	Actinomma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27883	17351	Triastrum	82709	\N	\N	\N	\N	Triastrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27884	17351	Spongodiscus	82706	\N	\N	\N	\N	Spongodiscus<Spongodiscidae-Coccodiscidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27885	17351	Spongodiscidae	82704	\N	\N	\N	\N	Spongodiscidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27886	17351	Spongodiscidae-Coccodiscidae X	82702	\N	\N	\N	\N	Spongodiscidae-Coccodiscidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27887	17351	Spongaster	82700	\N	\N	\N	\N	Spongaster	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27888	17351	Hexacontium	82697	\N	\N	\N	\N	Hexacontium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27889	17351	Euchitonia	82695	\N	\N	\N	\N	Euchitonia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27890	17351	Didymocyrtis	82693	\N	\N	\N	\N	Didymocyrtis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27891	17351	Dictyocoryne	82690	\N	\N	\N	\N	Dictyocoryne	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27892	17351	Dicranastrum	82688	\N	\N	\N	\N	Dicranastrum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27893	17351	Cypassis	82686	\N	\N	\N	\N	Cypassis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27894	17350	Stylochlamydium	82713	\N	\N	\N	\N	Stylochlamydium<Spumellaria X	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27895	17350	Spumellaria X sp.	82712	\N	\N	\N	\N	Spumellaria X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27896	17349	Spum group I X	82725	\N	\N	\N	\N	Spum group I X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27897	17349	Cladococcus	82720	\N	\N	\N	\N	Cladococcus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27898	17349	Astrosphaera	82718	\N	\N	\N	\N	Astrosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27899	17349	Arachnosphaera	82716	\N	\N	\N	\N	Arachnosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27900	17348	Spum group III X	82723	\N	\N	\N	\N	Spum group III X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27901	17347	Stylochlamydium venustum	82728	\N	\N	\N	\N	Stylochlamydium venustum<Stylochlamydium<Spumellaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27902	17362	Maullinia	82748	\N	\N	\N	\N	Maullinia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27903	17361	Phagomyxa	82752	\N	\N	\N	\N	Phagomyxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27904	17360	Tagiri4 lineage X2	82758	\N	\N	\N	\N	Tagiri4 lineage X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27905	17360	Tagiri4 lineage X1	82756	\N	\N	\N	\N	Tagiri4 lineage X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27906	17374	Ligniera	82762	\N	\N	\N	\N	Ligniera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27907	17373	Spongospora 1	82766	\N	\N	\N	\N	Spongospora 1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27908	17372	Plasmodiophora	82770	\N	\N	\N	\N	Plasmodiophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27909	17371	Plasmodiophorida U1 X2	82775	\N	\N	\N	\N	Plasmodiophorida U1 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27910	17371	Plasmodiophorida U1 X1	82773	\N	\N	\N	\N	Plasmodiophorida U1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27911	17370	Plasmodiophorida U2 X2	82780	\N	\N	\N	\N	Plasmodiophorida U2 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27912	17370	Plasmodiophorida U2 X1	82778	\N	\N	\N	\N	Plasmodiophorida U2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27913	17369	Plasmodiophorida U3 X1	82783	\N	\N	\N	\N	Plasmodiophorida U3 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27914	17368	Plasmodiophorida U4 X1	82786	\N	\N	\N	\N	Plasmodiophorida U4 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27915	17367	Plasmodiophorida U5 X1	82789	\N	\N	\N	\N	Plasmodiophorida U5 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27916	17366	Sorosphaerula	82808	\N	\N	\N	\N	Sorosphaerula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27917	17366	Sorosphaera	82806	\N	\N	\N	\N	Sorosphaera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27918	17366	Polymyxa 3	82803	\N	\N	\N	\N	Polymyxa 3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27919	17366	Polymyxa 2	82798	\N	\N	\N	\N	Polymyxa 2<Polymyxa lineage	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27920	17366	Polymyxa 1	82792	\N	\N	\N	\N	Polymyxa 1<Polymyxa lineage	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27921	17365	Polymyxa 2	82800	\N	\N	\N	\N	Polymyxa 2<Polymyxa-lineage	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27922	17365	Polymyxa 1	82795	\N	\N	\N	\N	Polymyxa 1<Polymyxa-lineage	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27923	17364	Spongospora 2	82811	\N	\N	\N	\N	Spongospora 2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27924	17363	Woronina	82815	\N	\N	\N	\N	Woronina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27925	17375	Tagiri5 lineage X1 sp.	82820	\N	\N	\N	\N	Tagiri5 lineage X1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27926	17378	Theratromyxa	82835	\N	\N	\N	\N	Theratromyxa	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27927	17378	Platyreta	82833	\N	\N	\N	\N	Platyreta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27928	17378	Leptophrys	82829	\N	\N	\N	\N	Leptophrys	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27929	17378	Leptophryidae X	82827	\N	\N	\N	\N	Leptophryidae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27930	17378	Arachnula	82824	\N	\N	\N	\N	Arachnula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27931	17377	Vamp clade A X3	82842	\N	\N	\N	\N	Vamp clade A X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27932	17377	Vamp clade A X2	82840	\N	\N	\N	\N	Vamp clade A X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27933	17377	Vamp clade A X1	82838	\N	\N	\N	\N	Vamp clade A X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27934	17376	Vampyrellidae X2	82851	\N	\N	\N	\N	Vampyrellidae X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27935	17376	Vampyrellidae X1	82849	\N	\N	\N	\N	Vampyrellidae X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27936	17376	Vampyrella	82845	\N	\N	\N	\N	Vampyrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27937	17384	lineage B1 X2	82857	\N	\N	\N	\N	lineage B1 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27938	17384	lineage B1 X1	82855	\N	\N	\N	\N	lineage B1 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27939	17383	lineage B2 X2	82862	\N	\N	\N	\N	lineage B2 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27940	17383	lineage B2 X1	82860	\N	\N	\N	\N	lineage B2 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27941	17382	lineage B3 X5	82873	\N	\N	\N	\N	lineage B3 X5	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27942	17382	lineage B3 X4	82871	\N	\N	\N	\N	lineage B3 X4	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27943	17382	lineage B3 X3	82869	\N	\N	\N	\N	lineage B3 X3	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27944	17382	lineage B3 X2	82867	\N	\N	\N	\N	lineage B3 X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27945	17382	lineage B3 X1	82865	\N	\N	\N	\N	lineage B3 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27946	17381	lineage B4 X1	82876	\N	\N	\N	\N	lineage B4 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27947	17380	Thalassomyxidae	82884	\N	\N	\N	\N	Thalassomyxidae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27948	17380	lineage B5 X	82879	\N	\N	\N	\N	lineage B5 X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27949	17379	lineage B6 X1	82890	\N	\N	\N	\N	lineage B6 X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27950	17385	Vamp clade C X2	82898	\N	\N	\N	\N	Vamp clade C X2	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27951	17385	Vamp clade C X1	82896	\N	\N	\N	\N	Vamp clade C X1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27952	17385	Penardia	82894	\N	\N	\N	\N	Penardia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27953	17388	Caecitellaceae X sp.	82905	\N	\N	\N	\N	Caecitellaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27954	17387	Caecitellus sp.	82910	\N	\N	\N	\N	Caecitellus sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27955	17387	Caecitellus pseudoparvulus	82909	\N	\N	\N	\N	Caecitellus pseudoparvulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27956	17387	Caecitellus parvulus	82908	\N	\N	\N	\N	Caecitellus parvulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27957	17387	Caecitellus paraparvulus	82907	\N	\N	\N	\N	Caecitellus paraparvulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27958	17386	Cafeteria sp.	82912	\N	\N	\N	\N	Cafeteria sp.<Cafeteria<Caecitellaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27959	17390	Cafeteria sp. MESS12	82920	\N	\N	\N	\N	Cafeteria sp. MESS12	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27960	17390	Cafeteria sp. Caron Lab Isolate	82919	\N	\N	\N	\N	Cafeteria sp. Caron Lab Isolate	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27961	17390	Cafeteria sp.	82918	\N	\N	\N	\N	Cafeteria sp.<Cafeteria<Cafeteriaceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
27962	17390	Cafeteria roenbergensis E4-10	82917	\N	\N	\N	\N	Cafeteria roenbergensis E4-10	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27963	17390	Cafeteria roenbergensis	82916	\N	\N	\N	\N	Cafeteria roenbergensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27964	17390	Cafeteria minima	82915	\N	\N	\N	\N	Cafeteria minima	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27965	17389	Cafeteriaceae X sp.	82922	\N	\N	\N	\N	Cafeteriaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27966	17391	Symbiomonas scintillans	82925	\N	\N	\N	\N	Symbiomonas scintillans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27967	17394	Bicoecaceae X sp.	82929	\N	\N	\N	\N	Bicoecaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27968	17393	Bicosoeca vacillans	82933	\N	\N	\N	\N	Bicosoeca vacillans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27969	17393	Bicosoeca sp.	82932	\N	\N	\N	\N	Bicosoeca sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27970	17393	Bicosoeca petiolata	82931	\N	\N	\N	\N	Bicosoeca petiolata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27971	17392	Halocafeteria sp.	82936	\N	\N	\N	\N	Halocafeteria sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27972	17392	Halocafeteria seosinensis	82935	\N	\N	\N	\N	Halocafeteria seosinensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27973	17399	Bicosoecida sp.SL204	82944	\N	\N	\N	\N	Bicosoecida sp.SL204	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27974	17397	Borokaceae X sp.	82947	\N	\N	\N	\N	Borokaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27975	17396	Pseudobodo tremulans	82949	\N	\N	\N	\N	Pseudobodo tremulans	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27976	17408	Amphifila marina	82971	\N	\N	\N	\N	Amphifila marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27977	17407	Amphifilidae X sp.	82973	\N	\N	\N	\N	Amphifilidae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27978	17410	Amphitrema wrightianum	82978	\N	\N	\N	\N	Amphitrema wrightianum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27979	17410	Amphitrema sp.	82977	\N	\N	\N	\N	Amphitrema sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27980	17409	Archerella flavum	82980	\N	\N	\N	\N	Archerella flavum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27981	17412	Diplophrys parva	82986	\N	\N	\N	\N	Diplophrys parva	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27982	17412	Diplophrys mutabilis	82985	\N	\N	\N	\N	Diplophrys mutabilis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27983	17413	Aplanochytrium stocchinoi	82995	\N	\N	\N	\N	Aplanochytrium stocchinoi	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27984	17413	Aplanochytrium sp PBS07	82994	\N	\N	\N	\N	Aplanochytrium sp PBS07	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27985	17413	Aplanochytrium sp.	82993	\N	\N	\N	\N	Aplanochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27986	17413	Aplanochytrium kerguelense	82992	\N	\N	\N	\N	Aplanochytrium kerguelense	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27987	17414	Labyrinthula zosterae	83000	\N	\N	\N	\N	Labyrinthula zosterae	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27988	17414	Labyrinthula terrestris	82999	\N	\N	\N	\N	Labyrinthula terrestris	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27989	17414	Labyrinthula sp.	82998	\N	\N	\N	\N	Labyrinthula sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27990	17425	Aurantiochytrium sp. TF59	83013	\N	\N	\N	\N	Aurantiochytrium sp. TF59	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27991	17425	Aurantiochytrium sp. TF49	83012	\N	\N	\N	\N	Aurantiochytrium sp. TF49	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27992	17425	Aurantiochytrium sp. TF29	83011	\N	\N	\N	\N	Aurantiochytrium sp. TF29	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27993	17425	Aurantiochytrium sp. TF28	83010	\N	\N	\N	\N	Aurantiochytrium sp. TF28	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27994	17425	Aurantiochytrium sp. TF24	83009	\N	\N	\N	\N	Aurantiochytrium sp. TF24	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27995	17425	Aurantiochytrium sp. TF23	83008	\N	\N	\N	\N	Aurantiochytrium sp. TF23	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27996	17425	Aurantiochytrium sp.	83007	\N	\N	\N	\N	Aurantiochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27997	17425	Aurantiochytrium mangrovei	83006	\N	\N	\N	\N	Aurantiochytrium mangrovei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27998	17425	Aurantiochytrium limacinum ATCCMYA-1381	83005	\N	\N	\N	\N	Aurantiochytrium limacinum ATCCMYA-1381	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
27999	17425	Aurantiochytrium limacinum	83004	\N	\N	\N	\N	Aurantiochytrium limacinum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28000	17424	Botryochytrium sp.	83016	\N	\N	\N	\N	Botryochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28001	17424	Botryochytrium radiatum	83015	\N	\N	\N	\N	Botryochytrium radiatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28002	17423	Japonochytrium sp.	83018	\N	\N	\N	\N	Japonochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28003	17422	Labyrinthuloides minuta	83021	\N	\N	\N	\N	Labyrinthuloides minuta<Labyrinthuloides<Thraustochytriidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28004	17422	Labyrinthuloides haliotidis	83020	\N	\N	\N	\N	Labyrinthuloides haliotidis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28005	17421	Parietichytrium sp.	83024	\N	\N	\N	\N	Parietichytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28006	17421	Parietichytrium sarkarianum	83023	\N	\N	\N	\N	Parietichytrium sarkarianum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28007	17420	quahogparasite-QPX-sp-NY070348D	83028	\N	\N	\N	\N	quahogparasite-QPX-sp-NY070348D	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28008	17420	quahogparasite-QPX sp-NY0313808BC1	83027	\N	\N	\N	\N	quahogparasite-QPX sp-NY0313808BC1	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28009	17420	quahogparasite-QPX sp.	83026	\N	\N	\N	\N	quahogparasite-QPX sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28010	17419	Schizochytrium sp.	83031	\N	\N	\N	\N	Schizochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28011	17419	Schizochytrium aggregatum	83030	\N	\N	\N	\N	Schizochytrium aggregatum<Schizochytrium<Thraustochytriidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28012	17418	Sicyoidochytrium sp.	83034	\N	\N	\N	\N	Sicyoidochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28013	17418	Sicyoidochytrium minutum	83033	\N	\N	\N	\N	Sicyoidochytrium minutum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28014	17417	Thraustochytriaceae X sp.	83036	\N	\N	\N	\N	Thraustochytriaceae X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28015	17416	Thraustochytrium striatum	83046	\N	\N	\N	\N	Thraustochytrium striatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28016	17416	Thraustochytrium sp. LLF1b	83045	\N	\N	\N	\N	Thraustochytrium sp. LLF1b	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28017	17416	Thraustochytrium sp.	83044	\N	\N	\N	\N	Thraustochytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28018	17416	Thraustochytrium pachydermum	83043	\N	\N	\N	\N	Thraustochytrium pachydermum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28019	17416	Thraustochytrium motivum	83042	\N	\N	\N	\N	Thraustochytrium motivum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28020	17416	Thraustochytrium kinnei	83041	\N	\N	\N	\N	Thraustochytrium kinnei	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28021	17416	Thraustochytrium gaertnerium	83040	\N	\N	\N	\N	Thraustochytrium gaertnerium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28022	17416	Thraustochytrium aureum	83039	\N	\N	\N	\N	Thraustochytrium aureum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28023	17416	Thraustochytrium aggregatum	83038	\N	\N	\N	\N	Thraustochytrium aggregatum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28024	17415	Ulkenia visurgensis	83052	\N	\N	\N	\N	Ulkenia visurgensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28025	17415	Ulkenia sp.	83051	\N	\N	\N	\N	Ulkenia sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28026	17415	Ulkenia radiata	83050	\N	\N	\N	\N	Ulkenia radiata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28027	17415	Ulkenia profunda	83049	\N	\N	\N	\N	Ulkenia profunda	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28028	17415	Ulkenia amoeboidea	83048	\N	\N	\N	\N	Ulkenia amoeboidea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28029	17429	Labyrinthuloides yorkensis	83057	\N	\N	\N	\N	Labyrinthuloides yorkensis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28030	17429	Labyrinthuloides minuta	83056	\N	\N	\N	\N	Labyrinthuloides minuta<Labyrinthuloides<Oblongichytriidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28031	17428	Oblongichytrium sp.clone 3525	83060	\N	\N	\N	\N	Oblongichytrium sp.clone 3525	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28032	17428	Oblongichytrium sp.	83059	\N	\N	\N	\N	Oblongichytrium sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28033	17427	Schizochytrium minutum	83063	\N	\N	\N	\N	Schizochytrium minutum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28034	17427	Schizochytrium aggregatum	83062	\N	\N	\N	\N	Schizochytrium aggregatum<Schizochytrium<Oblongichytriidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28035	17426	Thraustochytrium multirudimentale	83065	\N	\N	\N	\N	Thraustochytrium multirudimentale	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28036	17436	MAST 1A X sp.	83088	\N	\N	\N	\N	MAST 1A X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28037	17437	MAST 1B X sp.	83091	\N	\N	\N	\N	MAST 1B X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28038	17438	MAST 1C X sp.	83094	\N	\N	\N	\N	MAST 1C X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28039	17439	MAST 1D X sp.	83097	\N	\N	\N	\N	MAST 1D X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28040	17447	MAST 2B X sp.	83119	\N	\N	\N	\N	MAST 2B X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28041	17448	MAST 2C X sp.	83122	\N	\N	\N	\N	MAST 2C X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28042	17449	MAST 2D X sp.	83125	\N	\N	\N	\N	MAST 2D X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28043	17456	MAST 12A sp.	83131	\N	\N	\N	\N	MAST 12A sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28044	17455	MAST 12B sp.	83133	\N	\N	\N	\N	MAST 12B sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28045	17454	MAST 12C sp.	83136	\N	\N	\N	\N	MAST 12C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28046	17454	MAST 12 C sp.	83135	\N	\N	\N	\N	MAST 12 C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28047	17453	MAST 12D sp.	83138	\N	\N	\N	\N	MAST 12D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28048	17452	MAST 12E sp.	83140	\N	\N	\N	\N	MAST 12E sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28049	17451	MAST 12 X sp.	83142	\N	\N	\N	\N	MAST 12 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28050	17467	Incisomonas sp.	83146	\N	\N	\N	\N	Incisomonas sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28051	17467	Incisomonas marina	83145	\N	\N	\N	\N	Incisomonas marina	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28052	17466	MAST 3A sp.	83148	\N	\N	\N	\N	MAST 3A sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28053	17465	MAST 3B sp.	83150	\N	\N	\N	\N	MAST 3B sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28054	17464	MAST 3C sp.	83152	\N	\N	\N	\N	MAST 3C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28055	17463	MAST 3D sp.	83154	\N	\N	\N	\N	MAST 3D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28056	17462	MAST 3E sp.	83156	\N	\N	\N	\N	MAST 3E sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28057	17461	MAST 3F sp.	83158	\N	\N	\N	\N	MAST 3F sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28058	17460	MAST 3K sp.	83160	\N	\N	\N	\N	MAST 3K sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28059	17459	MAST 3L sp.	83162	\N	\N	\N	\N	MAST 3L sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28060	17458	MAST 3 X sp.	83164	\N	\N	\N	\N	MAST 3 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28061	17457	Solenicola sp.	83167	\N	\N	\N	\N	Solenicola sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28062	17457	Solenicola setigera	83166	\N	\N	\N	\N	Solenicola setigera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28063	17468	MAST 10 X sp.	83171	\N	\N	\N	\N	MAST 10 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28064	17469	MAST 11 X sp.	83174	\N	\N	\N	\N	MAST 11 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28065	17476	MAST 4A sp.	83177	\N	\N	\N	\N	MAST 4A sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28066	17475	MAST 4B1 sp.	83179	\N	\N	\N	\N	MAST 4B1 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28067	17474	MAST 4B2 sp.	83181	\N	\N	\N	\N	MAST 4B2 sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28068	17473	MAST 4C sp.	83183	\N	\N	\N	\N	MAST 4C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28069	17472	MAST 4D sp.	83185	\N	\N	\N	\N	MAST 4D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28070	17471	MAST 4E sp.	83187	\N	\N	\N	\N	MAST 4E sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28071	17470	MAST 4 X sp.	83189	\N	\N	\N	\N	MAST 4 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28072	17477	MAST 6 X sp.	83192	\N	\N	\N	\N	MAST 6 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28073	17483	MAST 7A sp.	83195	\N	\N	\N	\N	MAST 7A sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28074	17482	MAST 7B sp.	83197	\N	\N	\N	\N	MAST 7B sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28075	17481	MAST 7C sp.	83199	\N	\N	\N	\N	MAST 7C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28076	17480	MAST 7D sp.	83201	\N	\N	\N	\N	MAST 7D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28077	17479	MAST 7E sp.	83203	\N	\N	\N	\N	MAST 7E sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28078	17478	MAST 7 X sp.	83205	\N	\N	\N	\N	MAST 7 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28079	17489	MAST 8B sp.	83208	\N	\N	\N	\N	MAST 8B sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28080	17488	MAST 8C sp.	83210	\N	\N	\N	\N	MAST 8C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28081	17487	MAST 8D sp.	83212	\N	\N	\N	\N	MAST 8D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28082	17486	MAST 8E sp.	83214	\N	\N	\N	\N	MAST 8E sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28083	17485	MAST 8F sp.	83216	\N	\N	\N	\N	MAST 8F sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28084	17484	MAST 8 X sp.	83218	\N	\N	\N	\N	MAST 8 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28085	17494	MAST 9A sp.	83221	\N	\N	\N	\N	MAST 9A sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28086	17493	MAST 9B sp.	83223	\N	\N	\N	\N	MAST 9B sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28087	17492	MAST 9C sp.	83225	\N	\N	\N	\N	MAST 9C sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28088	17491	MAST 9D sp.	83227	\N	\N	\N	\N	MAST 9D sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28089	17490	MAST 9 X sp.	83229	\N	\N	\N	\N	MAST 9 X sp.	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28090	17515	Bleakeleya notata	83263	\N	\N	\N	\N	Bleakeleya notata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28091	17514	Centronella reicheltii	83265	\N	\N	\N	\N	Centronella reicheltii	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28092	17513	Ctenophora pulchella	83267	\N	\N	\N	\N	Ctenophora pulchella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28093	17512	Cycloclypeus carpenteri	83269	\N	\N	\N	\N	Cycloclypeus carpenteri<Cycloclypeus<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28094	17511	Heterostegina depressa	83271	\N	\N	\N	\N	Heterostegina depressa<Heterostegina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28095	17510	Nummulites venosus	83273	\N	\N	\N	\N	Nummulites venosus<Nummulites<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28096	17509	Operculina sp.	83278	\N	\N	\N	\N	Operculina sp.<Operculina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28097	17509	Operculina elegans	83277	\N	\N	\N	\N	Operculina elegans<Operculina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28098	17509	Operculina complanata	83276	\N	\N	\N	\N	Operculina complanata<Operculina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28099	17509	Operculina ammonoides	83275	\N	\N	\N	\N	Operculina ammonoides<Operculina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28100	17508	Operculinella cumingii	83280	\N	\N	\N	\N	Operculinella cumingii<Operculinella<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28101	17507	Planoperculina heterosteginoides	83282	\N	\N	\N	\N	Planoperculina heterosteginoides<Planoperculina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28102	17506	Planostegina operculinoides	83284	\N	\N	\N	\N	Planostegina operculinoides<Planostegina<araphid pennates	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28103	17505	Podocystis spathulata	83286	\N	\N	\N	\N	Podocystis spathulata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28104	17504	Protoraphis atlantica	83288	\N	\N	\N	\N	Protoraphis atlantica	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28105	17519	Halamphora	86665	\N	\N	\N	\N	Halamphora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28106	17519	Nupela	86442	\N	\N	\N	\N	Nupela	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28107	17519	Navicymbula	86440	\N	\N	\N	\N	Navicymbula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28108	17519	Delicata	86438	\N	\N	\N	\N	Delicata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28109	17519	Undatella	83874	\N	\N	\N	\N	Undatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28110	17519	Ulnaria	83872	\N	\N	\N	\N	Ulnaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28111	17519	Tryblionella	83870	\N	\N	\N	\N	Tryblionella<Bacillariophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28112	17519	Triceratium	83868	\N	\N	\N	\N	Triceratium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28113	17519	Thalassiothrix	83866	\N	\N	\N	\N	Thalassiothrix	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28114	17519	Thalassionema	83860	\N	\N	\N	\N	Thalassionema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28115	17519	Talaroneis	83858	\N	\N	\N	\N	Talaroneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28116	17519	Tabularia	83853	\N	\N	\N	\N	Tabularia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28117	17519	Tabellaria	83851	\N	\N	\N	\N	Tabellaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28118	17519	Synedropsis	83847	\N	\N	\N	\N	Synedropsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28119	17519	Synedra	83836	\N	\N	\N	\N	Synedra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28120	17519	Surirella	83829	\N	\N	\N	\N	Surirella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28121	17519	Striatella	83827	\N	\N	\N	\N	Striatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28122	17519	Stenopterobia	83825	\N	\N	\N	\N	Stenopterobia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28123	17519	Staurosirella	83822	\N	\N	\N	\N	Staurosirella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28124	17519	Staurosira	83816	\N	\N	\N	\N	Staurosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28125	17519	Stauroneis	83809	\N	\N	\N	\N	Stauroneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28126	17519	Sellaphora	83798	\N	\N	\N	\N	Sellaphora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28127	17519	Scoliopleura	83796	\N	\N	\N	\N	Scoliopleura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28128	17519	Rossia	83794	\N	\N	\N	\N	Rossia<Bacillariophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28129	17519	Rhopalodia	83788	\N	\N	\N	\N	Rhopalodia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28130	17519	Rhaphoneis	83784	\N	\N	\N	\N	Rhaphoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28131	17519	Rhabdonema	83781	\N	\N	\N	\N	Rhabdonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28132	17519	Reimeria	83779	\N	\N	\N	\N	Reimeria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28133	17519	Punctastriata	83777	\N	\N	\N	\N	Punctastriata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28134	17519	Pteroncola	83775	\N	\N	\N	\N	Pteroncola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28135	17519	Pseudostriatella	83773	\N	\N	\N	\N	Pseudostriatella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28136	17519	Pseudostaurosiropsis	83771	\N	\N	\N	\N	Pseudostaurosiropsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28137	17519	Pseudostaurosira	83768	\N	\N	\N	\N	Pseudostaurosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28138	17519	Pseudo-nitzschia	83754	\N	\N	\N	\N	Pseudo-nitzschia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28139	17519	Pseudohimantidium	83752	\N	\N	\N	\N	Pseudohimantidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28140	17519	Pseudogomphonema	83750	\N	\N	\N	\N	Pseudogomphonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28141	17519	Psammoneis	83746	\N	\N	\N	\N	Psammoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28142	17519	Psammodictyon	83742	\N	\N	\N	\N	Psammodictyon	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28143	17519	Prestauroneis	83740	\N	\N	\N	\N	Prestauroneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28144	17519	Pleurosigma	83736	\N	\N	\N	\N	Pleurosigma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28145	17519	Planothidium	83734	\N	\N	\N	\N	Planothidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28146	17519	Plagiostriata	83732	\N	\N	\N	\N	Plagiostriata	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28147	17519	Plagiogramma	83729	\N	\N	\N	\N	Plagiogramma<Bacillariophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28148	17519	Placoneis	83725	\N	\N	\N	\N	Placoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28149	17519	Pinnularia	83695	\N	\N	\N	\N	Pinnularia<Bacillariophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28150	17519	Phaeodactylum	83692	\N	\N	\N	\N	Phaeodactylum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28151	17519	Opephora	83689	\N	\N	\N	\N	Opephora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28152	17519	Nitzschia	83661	\N	\N	\N	\N	Nitzschia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28153	17519	Neofragilaria	83659	\N	\N	\N	\N	Neofragilaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28154	17519	Neidium	83655	\N	\N	\N	\N	Neidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28155	17519	Navicula	83629	\N	\N	\N	\N	Navicula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28156	17519	Naviculales	83627	\N	\N	\N	\N	Naviculales	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28157	17519	Nanofrustulum	83625	\N	\N	\N	\N	Nanofrustulum	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28158	17519	Mayamaea	83621	\N	\N	\N	\N	Mayamaea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28159	17519	Lyrella	83618	\N	\N	\N	\N	Lyrella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28160	17519	Luticola	83615	\N	\N	\N	\N	Luticola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28161	17519	Licmophora	83605	\N	\N	\N	\N	Licmophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28162	17519	Lemnicola	83603	\N	\N	\N	\N	Lemnicola	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28163	17519	Hyalosynedra	83601	\N	\N	\N	\N	Hyalosynedra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28164	17519	Hyalosira	83597	\N	\N	\N	\N	Hyalosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28165	17519	Hippodonta	83595	\N	\N	\N	\N	Hippodonta	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28166	17519	Haslea	83588	\N	\N	\N	\N	Haslea	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28167	17519	Hantzschia	83586	\N	\N	\N	\N	Hantzschia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28168	17519	Gyrosigma	83583	\N	\N	\N	\N	Gyrosigma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28169	17519	Grammonema	83579	\N	\N	\N	\N	Grammonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28170	17519	Grammatophora	83575	\N	\N	\N	\N	Grammatophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28171	17519	Gomphonema	83563	\N	\N	\N	\N	Gomphonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28172	17519	Gomphoneis	83561	\N	\N	\N	\N	Gomphoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28173	17519	Frustulia	83559	\N	\N	\N	\N	Frustulia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28174	17519	Fragilariopsis	83553	\N	\N	\N	\N	Fragilariopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28175	17519	Fragilariforma	83550	\N	\N	\N	\N	Fragilariforma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28176	17519	Fragilaria	83534	\N	\N	\N	\N	Fragilaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28177	17519	Fistulifera	83531	\N	\N	\N	\N	Fistulifera	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28178	17519	Fallacia	83527	\N	\N	\N	\N	Fallacia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28179	17519	Eunotia	83517	\N	\N	\N	\N	Eunotia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28180	17519	Epithemia	83513	\N	\N	\N	\N	Epithemia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28181	17519	Eolimna	83510	\N	\N	\N	\N	Eolimna	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28182	17519	Entomoneis	83505	\N	\N	\N	\N	Entomoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28183	17519	Encyonopsis	83503	\N	\N	\N	\N	Encyonopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28184	17519	Encyonema	83497	\N	\N	\N	\N	Encyonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28185	17519	Diploneis	83495	\N	\N	\N	\N	Diploneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28186	17519	Dimeregramma	83493	\N	\N	\N	\N	Dimeregramma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28187	17519	Didymosphenia	83491	\N	\N	\N	\N	Didymosphenia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28188	17519	Dickieia	83489	\N	\N	\N	\N	Dickieia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28189	17519	Diatoma	83482	\N	\N	\N	\N	Diatoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28190	17519	Delphineis	83480	\N	\N	\N	\N	Delphineis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28191	17519	Cymbopleura	83478	\N	\N	\N	\N	Cymbopleura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28192	17519	Cymbella	83379	\N	\N	\N	\N	Cymbella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28193	17519	Cymatopleura	83377	\N	\N	\N	\N	Cymatopleura	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28194	17519	Cylindrotheca	83373	\N	\N	\N	\N	Cylindrotheca	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28195	17519	Cyclophora	83370	\N	\N	\N	\N	Cyclophora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28196	17519	Craticula	83366	\N	\N	\N	\N	Craticula	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28197	17519	Convoluta[Symbiont]	83364	\N	\N	\N	\N	Convoluta[Symbiont]	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28198	17519	Cocconeis	83351	\N	\N	\N	\N	Cocconeis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28199	17519	Catacombas	83349	\N	\N	\N	\N	Catacombas	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28200	17519	Campylodiscus	83344	\N	\N	\N	\N	Campylodiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28201	17519	Caloneis	83338	\N	\N	\N	\N	Caloneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28202	17519	Berkeleya	83336	\N	\N	\N	\N	Berkeleya	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28203	17519	Bacillariophyceae X	83334	\N	\N	\N	\N	Bacillariophyceae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28204	17519	Bacillaria	83332	\N	\N	\N	\N	Bacillaria	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28205	17519	Astrosyne	83330	\N	\N	\N	\N	Astrosyne	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28206	17519	Asteroplanus	83328	\N	\N	\N	\N	Asteroplanus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28207	17519	Asterionellopsis	83326	\N	\N	\N	\N	Asterionellopsis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28208	17519	Asterionella	83320	\N	\N	\N	\N	Asterionella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28209	17519	Araphid-pennate X	83318	\N	\N	\N	\N	Araphid-pennate X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28210	17519	Anomoeoneis	83316	\N	\N	\N	\N	Anomoeoneis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28211	17519	Amphora	83306	\N	\N	\N	\N	Amphora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28212	17519	Amphiprora	83302	\N	\N	\N	\N	Amphiprora	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28213	17519	Achnanthidium	83297	\N	\N	\N	\N	Achnanthidium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28214	17519	Achnanthes	83293	\N	\N	\N	\N	Achnanthes	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28215	17518	Attheya	83877	\N	\N	\N	\N	Attheya<Bacillariophytina incertae sedis	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28216	17517	Conticribra	86656	\N	\N	\N	\N	Conticribra	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28217	17517	Bacteriastrum	86447	\N	\N	\N	\N	Bacteriastrum<Mediophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28218	17517	Trigonium	84109	\N	\N	\N	\N	Trigonium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28219	17517	Toxarium	84106	\N	\N	\N	\N	Toxarium	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28220	17517	Thalassiosira	84073	\N	\N	\N	\N	Thalassiosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28221	17517	Terpsinoe	84071	\N	\N	\N	\N	Terpsinoe	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28222	17517	Stephanodiscus	84061	\N	\N	\N	\N	Stephanodiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28223	17517	Skeletonema	84042	\N	\N	\N	\N	Skeletonema	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28224	17517	Shionodiscus	84039	\N	\N	\N	\N	Shionodiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28225	17517	Porosira	84034	\N	\N	\N	\N	Porosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28226	17517	Pleurosira	84032	\N	\N	\N	\N	Pleurosira	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28227	17517	Planktoniella	84030	\N	\N	\N	\N	Planktoniella	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28228	17517	Pierrecomperia	84028	\N	\N	\N	\N	Pierrecomperia	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28229	17517	Peridiniopsis	84025	\N	\N	\N	\N	Peridiniopsis<Mediophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28230	17517	Peridiniopsis diatom emdosymbiont	84022	\N	\N	\N	\N	Peridiniopsis diatom emdosymbiont	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28231	17517	Papiliocellulus	84018	\N	\N	\N	\N	Papiliocellulus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28232	17517	Odontella	84015	\N	\N	\N	\N	Odontella<Mediophyceae	\N	2019-01-29 05:53:34	\N	\N	\N	A	P
28233	17517	Minutocellus	84012	\N	\N	\N	\N	Minutocellus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28234	17517	Minidiscus	84009	\N	\N	\N	\N	Minidiscus	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28235	17517	Mediopyxis	84007	\N	\N	\N	\N	Mediopyxis	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
28236	17517	Mediophyceae X	84005	\N	\N	\N	\N	Mediophyceae X	\N	2018-01-02 00:00:00	\N	\N	\N	A	P
84962	84960	geometric	m700	\N	\N	\N		geometric	\N	2019-01-29 05:53:34	\N			A	M
84964	25828	dead	m171	\N	\N	\N	\N	dead<Copepoda	\N	2019-05-02 16:05:12	\N	\N	\N	A	M
84965	11518	larvae	m172	\N	\N	\N	\N	larvae<Annelida	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84967	11515	cyphonaute	m174	\N	\N	\N	\N	cyphonaute	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
84968	11514	tail	m175	\N	\N	\N	\N	tail<Chaetognatha	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84969	13333	like	m176	\N	\N	\N	\N	like<Phaeodaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84970	11512	part	m177	\N	\N	\N	\N	part<Cnidaria	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84973	25990	siphosome	m180	\N	\N	\N	\N	siphosome	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
84974	83278	nectophore	m181	\N	\N	\N	\N	nectophore<Abylopsis tetragona	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84975	83278	eudoxie	m182	\N	\N	\N	\N	eudoxie<Abylopsis tetragona	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84976	72396	nectophore	m183	\N	\N	\N	\N	nectophore<Diphyidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84977	72396	eudoxie	m184	\N	\N	\N	\N	eudoxie<Diphyidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84979	72395	nectophore	m186	\N	\N	\N	\N	nectophore<Hippopodiidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84980	51381	nectophore	m188	\N	\N	\N	\N	nectophore<Physonectae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84983	12846	metanauplii	m190	\N	\N	\N	\N	metanauplii<Crustacea	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84984	61973	like	m191	\N	\N	\N	\N	like<Temoridae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84985	45043	like	m192	\N	\N	\N	\N	like<Decapoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84986	45043	zoea	m202	\N	\N	\N	\N	zoea<Decapoda	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84987	81904	protozoea	m193	\N	\N	\N	\N	protozoea<Penaeidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84988	81915	phyllosoma	m194	\N	\N	\N	\N	phyllosoma	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
84989	83502	zoea	m195	\N	\N	\N	\N	zoea<Galatheidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84990	81916	like	m196	\N	\N	\N	\N	like<Brachyura	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84991	81916	megalopa	m197	\N	\N	\N	\N	megalopa	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
84992	83671	like	m198	\N	\N	\N	\N	like<Laomediidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84993	45041	calyptopsis	m199	\N	\N	\N	\N	calyptopsis<Euphausiacea	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84994	81905	protozoea	m360	\N	\N	\N	\N	protozoea<Sergestidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84995	45048	protozoea	m200	\N	\N	\N	\N	protozoea<Mysida	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84996	45064	larvae	m201	\N	\N	\N	\N	larvae<Squillidae	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84997	45079	nauplii	m203	\N	\N	\N	\N	nauplii<Cirripedia	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
84998	45079	cypris	m204	\N	\N	\N	\N	cypris	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
84999	12873	pluteus	m205	\N	\N	\N	\N	pluteus<Ophiuroidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85000	12875	pluteus	m206	\N	\N	\N	\N	pluteus<Echinoidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85001	12874	larvae	m207	\N	\N	\N	\N	larvae<Holothuroidea	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85003	11498	part	m209	\N	\N	\N	\N	part<Mollusca	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85004	85123	tail	m212	\N	\N	\N	\N	tail<Appendicularia	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85005	25942	larvae	m213	\N	\N	\N	\N	larvae<Salpida	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85006	25942	colony	m214	\N	\N	\N	\N	colony<Salpida	\N	2020-06-04 21:56:40	\N	\N	\N	A	M
85007	16627	wing	m216	\N	\N	\N	\N	wing	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85008	84960	artefact	m003	\N	\N	\N	\N	artefact	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85009	11816	centric	m162	\N	\N	\N	\N	centric	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85010	11816	pennate	m163	\N	\N	\N	\N	pennate<Bacillariophyta	\N	2019-01-29 05:53:34	\N	\N	\N	A	M
85013	84959	t002	m143	\N	\N	\N	\N	t002	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85014	84959	t003	m144	\N	\N	\N	\N	t003	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85015	84959	t004	m145	\N	\N	\N	\N	t004	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
85016	84959	t005	m217	\N	\N	\N	\N	t005	\N	2018-01-02 00:00:00	\N	\N	\N	A	M
\.

-- e.g. to get some data with lineage:
-- ecotaxa4=# copy (select * from worms where aphia_id in (10194, 152352, 1828, 1821, 146419)) to '/tmp/cp.sql';
COPY public.worms (aphia_id, url, scientificname, authority, status, unacceptreason, taxon_rank_id, rank, valid_aphia_id, valid_name, valid_authority, parent_name_usage_id, kingdom, phylum, class_, "order", family, genus, citation, lsid, is_marine, is_brackish, is_freshwater, is_terrestrial, is_extinct, match_type, modified, all_fetched) FROM stdin;
1	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1	Biota	\N	accepted	\N	0	\N	1	Biota\N	1	\N	\N	\N	\N	\N	\N	WoRMS (2020). Biota. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1 on 2020-09-17	urn:lsid:marinespecies.org:taxname:1	t	t	t	t	\N	\N	exact	2004-12-21 15:54:05.437	t
889851	http://www.marinespecies.org/aphia.php?p=taxdetails&id=889851	Sarcotacidea	Yamaguti, 1963	unaccepted	\N	100	Order	1381349	Ergasilida	Khodami, Mercado-Salas, Tang & Martinez Arbizu, 2019	155879	Animalia	Arthropoda	Hexanauplia	Sarcotacidea	\N	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Sarcotacidea. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=889851 on 2020-09-20	urn:lsid:marinespecies.org:taxname:889851	t	f	f	f	\N	exact	2016-11-28 11:01:17.91	t
889925	http://www.marinespecies.org/aphia.php?p=taxdetails&id=889925	Hexanauplia	Oakley, Wolfe, Lindgren & Zaharof, 2013	accepted	\N	60	Class	889925	Hexanauplia	Oakley, Wolfe, Lindgren & Zaharof, 2013	845959	Animalia	Arthropoda	Hexanauplia	\N	\N	\N	WoRMS (2020). Hexanauplia. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=889925 on 2020-09-19	urn:lsid:marinespecies.org:taxname:889925	t	t	t	\N	\N	exact	2016-11-30 12:36:48.403	t
845959	http://www.marinespecies.org/aphia.php?p=taxdetails&id=845959	Multicrustacea	Regier, Shultz, Zwick, Hussey, Ball, Wetzer, Martin & Cunningham, 2010	accepted	\N	50	Superclass	845959	Multicrustacea	Regier, Shultz, Zwick, Hussey, Ball, Wetzer, Martin & Cunningham, 2010	1066	Animalia	Arthropoda	\N	\N	\N	\N	WoRMS (2020). Multicrustacea. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=845959 on 2020-09-19	urn:lsid:marinespecies.org:taxname:845959	t	t	t	t	\N	exact	2015-05-05 09:47:59.543	t
1066	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1066	Crustacea	Brünnich, 1772	accepted	\N	40	Subphylum	1066	Crustacea	Brünnich, 1772	1065	Animalia	Arthropoda	\N	\N	\N	\N	WoRMS (2020). Crustacea. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1066 on 2020-09-19	urn:lsid:marinespecies.org:taxname:1066	t	t	t	t	\N	exact	2015-05-05 09:47:59.543	t
1065	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1065	Arthropoda	von Siebold, 1848	accepted	\N	30	Phylum	1065	Arthropoda	von Siebold, 1848	2	Animalia	Arthropoda	\N	\N	\N	\N	WoRMS (2020). Arthropoda. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1065 on 2020-09-17	urn:lsid:marinespecies.org:taxname:1065	t	t	t	t	\N	exact	2017-08-31 06:52:42.687	t
2	http://www.marinespecies.org/aphia.php?p=taxdetails&id=2	Animalia	\N	accepted	\N	10	Kingdom	2	Animalia	\N	1	Animalia	\N	\N	\N	\N	\N	WoRMS (2020). Animalia. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=2 on 2020-09-17	urn:lsid:marinespecies.org:taxname:2	t	t	t	t	\N	exact	2004-12-21 15:54:05.437	t
1101	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1101	Cyclopoida	Burmeister, 1834	accepted	\N	100	Order	1101	Cyclopoida	Burmeister, 1834	155879	Animalia	Arthropoda	Hexanauplia	Cyclopoida	\N	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Cyclopoida. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1101 on 2020-09-20	urn:lsid:marinespecies.org:taxname:1101	t	t	t	\N	\N	exact	2016-03-21 09:41:01.793	t
1381349	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1381349	Ergasilida	Khodami, Mercado-Salas, Tang & Martinez Arbizu, 2019	accepted	\N	110	Suborder	1381349	Ergasilida	Khodami, Mercado-Salas, Tang & Martinez Arbizu, 2019	1101	Animalia	Arthropoda	Hexanauplia	Cyclopoida	\N	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Ergasilida. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1381349 on 2020-09-20	urn:lsid:marinespecies.org:taxname:1381349	t	t	t	\N	\N	exact	2019-10-07 11:15:09.153	t
128586	http://www.marinespecies.org/aphia.php?p=taxdetails&id=128586	Oncaeidae	Giesbrecht, 1893	accepted	\N	140	Family	128586	Oncaeidae	Giesbrecht, 1893	1381349	Animalia	Arthropoda	Hexanauplia	Cyclopoida	Oncaeidae	\N	Walter, T.C.; Boxshall, G. (2020). World of Copepods database. Oncaeidae Giesbrecht, 1893. Accessed through: World Register of Marine Species at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=128586 on 2020-09-20	urn:lsid:marinespecies.org:taxname:128586	t	\N	\N	\N	f	exact	2019-10-07 11:15:09.153	t
155879	http://www.marinespecies.org/aphia.php?p=taxdetails&id=155879	Podoplea	Giesbrecht, 1882	accepted	\N	90	Superorder	155879	Podoplea	Giesbrecht, 1882	155876	Animalia	Arthropoda	Hexanauplia	\N	\N	\N	WoRMS (2020). Podoplea. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=155879 on 2020-09-19	urn:lsid:marinespecies.org:taxname:155879	t	\N	t	\N	\N	exact	2008-08-27 21:14:09.817	t
155876	http://www.marinespecies.org/aphia.php?p=taxdetails&id=155876	Neocopepoda	Huys & Boxshall, 1991	accepted	\N	80	Infraclass	155876	Neocopepoda	Huys & Boxshall, 1991	1080	Animalia	Arthropoda	Hexanauplia	\N	\N	\N	WoRMS (2020). Neocopepoda. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=155876 on 2020-09-19	urn:lsid:marinespecies.org:taxname:155876	t	t	t	\N	\N	exact	2008-06-23 12:21:53.35	t
1080	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1080	Copepoda	Milne Edwards, 1840	accepted	\N	70	Subclass	1080	Copepoda	Milne Edwards, 1840	889925	Animalia	Arthropoda	Hexanauplia	\N	\N	\N	WoRMS (2020). Copepoda. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1080 on 2020-09-19	urn:lsid:marinespecies.org:taxname:1080	t	t	t	\N	\N	exact	2016-11-30 12:36:48.403	t
1821	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1821	Chordata	Haeckel, 1874	accepted	\N	30	Phylum	1821	Chordata	Haeckel, 1874	2	Animalia	Chordata	\N	\N	\N	\N	WoRMS (2020). Chordata. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1821 on 2020-09-17	urn:lsid:marinespecies.org:taxname:1821	t	\N	\N	\N	\N	exact	2004-12-21 15:54:05.437	t
146419	http://www.marinespecies.org/aphia.php?p=taxdetails&id=146419	Vertebrata	\N	accepted	\N	40	Subphylum	146419	Vertebrata	\N	1821	Animalia	Chordata	\N	\N	\N	\N	WoRMS (2020). Vertebrata. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=146419 on 2020-09-19	urn:lsid:marinespecies.org:taxname:146419	t	\N	\N	\N	\N	exact	2004-12-21 15:54:05.437	t
1828	http://www.marinespecies.org/aphia.php?p=taxdetails&id=1828	Gnathostomata	\N	accepted	\N	50	Superclass	1828	Gnathostomata	\N	146419	Animalia	Chordata	\N	\N	\N	\N	WoRMS (2020). Gnathostomata. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=1828 on 2020-09-19	urn:lsid:marinespecies.org:taxname:1828	t	\N	\N	\N	\N	exact	2004-12-21 15:54:05.437	t
10194	http://www.marinespecies.org/aphia.php?p=taxdetails&id=10194	Actinopterygii	\N	accepted	\N	60	Class	10194	Actinopterygii	\N	1828	Animalia	Chordata	Actinopterygii	\N	\N	\N	WoRMS (2020). Actinopterygii. Accessed at: http://www.marinespecies.org/aphia.php?p=taxdetails&id=10194 on 2020-09-19	urn:lsid:marinespecies.org:taxname:10194	t	\N	\N	\N	\N	exact	2017-02-02 05:40:48.577	t
\.
