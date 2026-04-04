# -*- coding: utf-8 -*-
from os.path import dirname, realpath
from pathlib import Path

# All files paths are now relative to root shared directory
TEST_DIR = Path(dirname(realpath(__file__))).resolve()
SHARED_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
FTP_DIR = SHARED_DIR / "ftp"
DATA_DIR = Path("")
PLAIN_FILE = DATA_DIR / "import_test.zip"  # As seen from server
PLAIN_FILE_PATH = SHARED_DIR / "import_test.zip"  # As seen from client
V6_FILE = DATA_DIR / "UVP6_example.zip"
V6_DIR = DATA_DIR / "import_uvp6_zip_in_dir"
PLAIN_DIR = DATA_DIR / "import_test"
UPDATE_DIR = DATA_DIR / "import_update"
BAD_FREE_DIR = DATA_DIR / "import_bad_free_data"
SPARSE_DIR = DATA_DIR / "import_sparse"
PLUS_DIR = DATA_DIR / "import_test_plus"
PLUS_MORE_DIR = DATA_DIR / "import_test_plus_more"
JUST_PREDICTED_DIR = DATA_DIR / "import_just_predicted"
V_OR_D_ONLY_DIR = DATA_DIR / "import_v_or_d_just_state"
WEIRD_DIR = DATA_DIR / "import_test_weird"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
ISSUES_DIR3 = DATA_DIR / "import_issues" / "tsv_too_many_cols"
ISSUES_DIR4 = DATA_DIR / "import_issues" / "duplicate_in_tsv"
ISSUES_DIR5 = DATA_DIR / "import_issues" / "predicted_but_what"
ISSUES_DIR6 = DATA_DIR / "import_issues" / "classif_without_state"
ISSUES_DIR7 = DATA_DIR / "import_issues" / "extra_data_without_header"
MIX_OF_STATES = DATA_DIR / "import_mixed_states"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"
EMPTY_TSV_DIR = DATA_DIR / "import_issues" / "empty_tsv"
EMPTY_TSV_DIR2 = DATA_DIR / "import_issues" / "empty_tsv2"
BREAKING_HIERARCHY_DIR = DATA_DIR / "import_issues" / "breaking_hierarchy"
EMPTY_TSV_IN_UPD_DIR = DATA_DIR / "import_test_upd_empty"
AMBIG_DIR = DATA_DIR / "import de categories ambigues"
VARIOUS_STATES_DIR = DATA_DIR / "import_various_states"
IMPORT_TOT_VOL = DATA_DIR / "import_test_tot_vol"
IMPORT_TOT_VOL_UPDATE = DATA_DIR / "import_test_tot_vol_update"
IMPORT_TOT_VOL_BAD_UPDATE = DATA_DIR / "import_test_tot_vol_bad_update"
