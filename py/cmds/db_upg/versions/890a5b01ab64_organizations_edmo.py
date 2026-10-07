"""organizations edmo

Revision ID: 890a5b01ab64
Revises: c593af18f13a
Create Date: 2026-09-30 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "890a5b01ab64"
down_revision = "c593af18f13a"

import re
from typing import List

from alembic import op

# Plain SQL only, so that offline mode (`alembic upgrade --sql`, QA/py/pg_files/upgrade_prod.sql)
# produces exactly what online mode runs. Matches are embedded, resolved once from the reviewed
# edmo_matches.xlsx, no access to the EDMO website.
UPGRADE_SQL = r"""
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
"""

DOWNGRADE_SQL = r"""
-- Put back organizations as they were before the EDMO normalisation. Organizations or users
-- created afterwards are kept, collection links to survivors are restored as in the backup.
UPDATE organizations org
   SET name = '__edmo_tmp_' || org.id
  FROM organizations_edmo_log lgg
 WHERE lgg.action = 'update'
   AND org.id = lgg.org_id;

INSERT INTO organizations (id, name, directories)
SELECT bak.id, bak.name, bak.directories
  FROM organizations_edmo_bak bak
  JOIN organizations_edmo_log lgg ON lgg.org_id = bak.id AND lgg.action = 'merge';

UPDATE organizations org
   SET name        = bak.name,
       directories = bak.directories
  FROM organizations_edmo_bak bak
  JOIN organizations_edmo_log lgg ON lgg.org_id = bak.id AND lgg.action = 'update'
 WHERE org.id = bak.id;

UPDATE users usr
   SET organization_id = bak.organization_id
  FROM users_organization_edmo_bak bak
  JOIN organizations_edmo_log lgg ON lgg.org_id = bak.organization_id AND lgg.action = 'merge'
 WHERE usr.id = bak.id
   AND usr.organization_id = lgg.merged_into;

DELETE FROM collection_orga_role cor
 WHERE cor.organization_id IN (SELECT merged_into FROM organizations_edmo_log WHERE action = 'merge')
   AND NOT EXISTS (SELECT 1
                     FROM collection_orga_role_edmo_bak bak
                    WHERE bak.collection_id = cor.collection_id
                      AND bak.organization_id = cor.organization_id
                      AND bak.role = cor.role);

INSERT INTO collection_orga_role (collection_id, organization_id, role, display_order)
SELECT bak.collection_id, bak.organization_id, bak.role, bak.display_order
  FROM collection_orga_role_edmo_bak bak
  JOIN organizations_edmo_log lgg ON lgg.org_id = bak.organization_id AND lgg.action = 'merge'
 WHERE EXISTS (SELECT 1 FROM collection col WHERE col.id = bak.collection_id)
    ON CONFLICT DO NOTHING;

DROP TABLE organizations_edmo_log;

DROP TABLE collection_orga_role_edmo_bak;

DROP TABLE users_organization_edmo_bak;

DROP TABLE organizations_edmo_bak;
"""


def _statements(sql: str) -> List[str]:
    """Statements are separated by a blank line after their ';'"""
    return [
        a_stmt.strip().rstrip(";")
        for a_stmt in re.split(r";\n\s*\n", sql.strip() + "\n\n")
        if a_stmt.strip()
    ]


def upgrade():
    for a_stmt in _statements(UPGRADE_SQL):
        op.execute(a_stmt)


def downgrade():
    for a_stmt in _statements(DOWNGRADE_SQL):
        op.execute(a_stmt)
