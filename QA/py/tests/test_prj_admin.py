import logging

from tests.credentials import ADMIN_AUTH

# noinspection PyPackageRequirements


PROJECT_CLASSIF_STATS_URL = "/project_set/stats?ids={prj_ids}"

PROJECT_FREE_COLS_STATS_URL = "/projects/{project_id}/stats"


def test_project_stats(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "Stats test project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "Stats test project")
    # Taxa & classif statistics
    url = PROJECT_CLASSIF_STATS_URL.format(prj_ids=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    assert rsp.json() == [{'nb_dubious': 0, 'nb_predicted': 11, 'nb_unclassified': 0, 'nb_validated': 0,
                           'projid': prj_id,
                           'used_taxa': [45072, 78418, 84963, 85011, 85012, 85078]}]

    # Get free column statistics
    url = PROJECT_FREE_COLS_STATS_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    expected = ['Stats test project',
                "OrderedDict([('by', 'n01'), ('width', 'n02'), ('height', 'n03'), ('area', " "'n04'), ('mean', 'n05'), ('major', 'n06'), ('minor', 'n07'), ('feret', " "'n08'), ('area_exc', 'n09'), ('thickr', 'n10'), ('esd', 'n11'), " "('elongation', 'n12'), ('range', 'n13'), ('meanpos', 'n14'), ('centroids', " "'n15'), ('cv', 'n16'), ('sr', 'n17'), ('perimareaexc', 'n18'), " "('feretareaexc', 'n19'), ('perimferet', 'n20'), ('perimmajor', 'n21'), " "('circex', 'n22'), ('cdexc', 'n23'), ('kurt_mean', 'n24'), ('skew_mean', " "'n25'), ('convperim_perim', 'n26'), ('convarea_area', 'n27'), " "('symetrieh_area', 'n28'), ('symetriev_area', 'n29'), ('nb1_area', 'n30'), " "('nb2_area', 'n31'), ('nb3_area', 'n32'), ('nb1_range', 'n33'), " "('nb2_range', 'n34'), ('nb3_range', 'n35'), ('median_mean', 'n36'), " "('median_mean_range', 'n37'), ('skeleton_area', 'n38'), ('extra', 't01')])",
                ' (0): ', 'Total: 0 values, dup 0 values',
                'generic_m106_mn01_n2_sml (2): ' '[9940,10961,#2,u1],[23,56,#2,u1],[28,38,#2,u1],[490,929,#2,u1],[210.8000030518,222.75,#2,u1],'
                '[27,44.2000007629,#2,u1],[23.1000003815,26.7999992371,#2,u1],[29.2000007629,58.2000007629,#2,u1],[0,9,#2,u1],'
                '[1.8600000143,2,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],'
                '[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],'
                '[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],'
                '[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],'
                '[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1],[NaN,NaN,#2,u1]',
                'Total: 76 values, dup 38 values',
                'generic_m106_mn01_n1_sml (4): ' '[9811,10823,#4,u1],[33,65,#4,u1],[47,69,#4,u1],[733,1583,#4,u1],'
                '[192.2400054932,222.7899932861,#4,u1],[48.7999992371,70.1999969482,#4,u1],'
                '[19.1000003815,41.2000007629,#4,u1],[51.5999984741,73.1999969482,#4,u1],'
                '[0,100,#3,u2],[2,2.8239998817,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],'
                '[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],'
                '[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],'
                '[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],'
                '[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],[NaN,NaN,#4,u1],'
                '[NaN,NaN,#4,u1]',
                'Total: 152 values, dup 39 values']
    actual = rsp.json()
    assert actual == expected
