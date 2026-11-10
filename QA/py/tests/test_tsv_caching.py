# -*- coding: utf-8 -*-
from collections import OrderedDict
from pathlib import Path
import datetime

import BO.Mappings as GlobalMapping
from BO.TSVFile import TSVFile
from BO.helpers.ImportHelpers import ImportHow, ImportDiagnostic
from BO.Mappings import ProjectMapping
from DB.Object import ObjectHeader, ObjectFields
from DB.Acquisition import Acquisition


def _create_tsv_file_instance(headers):
    tsv = TSVFile(Path("/tmp/dummy.tsv"), "dummy.tsv", Path("/tmp"))
    clean_fields = OrderedDict()
    for h in headers:
        a_field = h.strip().lower()
        clean_fields[h] = a_field
    tsv.clean_fields = clean_fields
    return tsv


def test_missing_gps_count_with_cache():
    """Verify that multiple lines with empty or missing latitude correctly increment nb_objects_without_gps."""
    headers = ["object_id", "img_file_name", "object_lat", "object_lon"]
    tsv = _create_tsv_file_instance(headers)

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    # Line 1: empty latitude
    lig1 = {"object_id": "obj1", "img_file_name": "1.png", "object_lat": "", "object_lon": ""}
    tsv.validate_line(how, diag, lig1, 1, seen_vals)
    assert diag.nb_objects_without_gps == 1

    # Line 2: also empty latitude (should not be marked as seen by cache hit)
    lig2 = {"object_id": "obj2", "img_file_name": "2.png", "object_lat": "", "object_lon": ""}
    tsv.validate_line(how, diag, lig2, 2, seen_vals)
    assert diag.nb_objects_without_gps == 2

    # Line 3: valid latitude
    lig3 = {"object_id": "obj3", "img_file_name": "3.png", "object_lat": "43.5", "object_lon": "7.3"}
    tsv.validate_line(how, diag, lig3, 3, seen_vals)
    assert diag.nb_objects_without_gps == 2

    # Line 4: same valid latitude (cache hit, should be marked as seen)
    lig4 = {"object_id": "obj4", "img_file_name": "4.png", "object_lat": "43.5", "object_lon": "7.3"}
    tsv.validate_line(how, diag, lig4, 4, seen_vals)
    assert diag.nb_objects_without_gps == 2


def test_validation_error_not_suppressed_by_cache():
    """Verify that repeated invalid values across lines are all reported and not silently suppressed by cache."""
    headers = ["object_id", "img_file_name", "object_lat", "object_lon", "object_date", "object_time", "object_annotation_status"]
    tsv = _create_tsv_file_instance(headers)

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    # Line 1 with invalid lon, invalid date, invalid time, invalid status
    lig1 = {
        "object_id": "obj1",
        "img_file_name": "1.png",
        "object_lat": "43.5",
        "object_lon": "999",
        "object_date": "invalid-date",
        "object_time": "invalid-time",
        "object_annotation_status": "invalid-status",
    }
    tsv.validate_line(how, diag, lig1, 1, seen_vals)
    # diag.errors has 1 header ("In dummy.tsv:") + 4 error messages
    assert len(diag.errors) == 5

    # Line 2 with the exact same invalid values should ALSO report 4 errors
    lig2 = {
        "object_id": "obj2",
        "img_file_name": "2.png",
        "object_lat": "43.5",
        "object_lon": "999",
        "object_date": "invalid-date",
        "object_time": "invalid-time",
        "object_annotation_status": "invalid-status",
    }
    tsv.validate_line(how, diag, lig2, 2, seen_vals)
    assert len(diag.errors) == 9


def test_user_email_synchronization_across_lines():
    """Verify that user email is not lost if line 1 has no email but line 2 provides email."""
    headers = ["object_id", "img_file_name", "object_annotation_person_name", "object_annotation_person_email"]
    tsv = _create_tsv_file_instance(headers)

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    # Line 1: Jane Doe with no email
    lig1 = {
        "object_id": "obj1",
        "img_file_name": "1.png",
        "object_annotation_person_name": "Jane Doe",
        "object_annotation_person_email": "",
    }
    tsv.validate_line(how, diag, lig1, 1, seen_vals)
    assert how.found_users["jane doe"] == {"email": ""}

    # Line 2: Jane Doe with email
    lig2 = {
        "object_id": "obj2",
        "img_file_name": "2.png",
        "object_annotation_person_name": "Jane Doe",
        "object_annotation_person_email": "jane@example.com",
    }
    tsv.validate_line(how, diag, lig2, 2, seen_vals)
    assert how.found_users["jane doe"] == {"email": "jane@example.com"}


def test_taxon_category_registration_across_lines():
    """Verify that taxon name is registered even if first line has category_id and second line does not."""
    headers = ["object_id", "img_file_name", "object_annotation_category", "object_annotation_category_id"]
    tsv = _create_tsv_file_instance(headers)

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    # Line 1: Copepoda with ID
    lig1 = {
        "object_id": "obj1",
        "img_file_name": "1.png",
        "object_annotation_category": "Copepoda",
        "object_annotation_category_id": "123",
    }
    tsv.validate_line(how, diag, lig1, 1, seen_vals)
    assert "copepoda" not in how.found_taxa

    # Line 2: Copepoda without ID
    lig2 = {
        "object_id": "obj2",
        "img_file_name": "2.png",
        "object_annotation_category": "Copepoda",
        "object_annotation_category_id": "",
    }
    tsv.validate_line(how, diag, lig2, 2, seen_vals)
    assert "copepoda" in how.found_taxa


def test_read_fields_to_dicts_classif_date_caching():
    """Verify that classif_date is not cached under dummy keys or cross-polluting lines with different times."""
    field_set = {"object_annotation_date"}
    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    vals_cache = {}

    dicts_to_write_1 = {alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()}
    lig1 = {
        "object_annotation_date": "2020-01-01",
        "object_annotation_time": "10:00:00",
    }
    TSVFile.read_fields_to_dicts(how, field_set, lig1, dicts_to_write_1, vals_cache)
    assert dicts_to_write_1[ObjectHeader.__tablename__]["classif_date"] == datetime.datetime(2020, 1, 1, 10, 0, 0)
    assert "object_annotation_date" not in vals_cache

    dicts_to_write_2 = {alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()}
    lig2 = {
        "object_annotation_date": "2020-01-01",
        "object_annotation_time": "15:30:00",
    }
    TSVFile.read_fields_to_dicts(how, field_set, lig2, dicts_to_write_2, vals_cache)
    assert dicts_to_write_2[ObjectHeader.__tablename__]["classif_date"] == datetime.datetime(2020, 1, 1, 15, 30, 0)


def test_read_fields_to_dicts_nested_caching():
    """Verify that vals_cache is populated as Dict[str, Dict[Any, Any]] mapping field_name -> raw_val -> produced."""
    field_set = {"object_lat", "object_date", "object_id"}
    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    vals_cache = {}

    dicts_to_write = {alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()}
    lig = {
        "object_lat": "43°30 00",
        "object_date": "2021-05-15",
        "object_id": "test_obj_1",
    }
    TSVFile.read_fields_to_dicts(how, field_set, lig, dicts_to_write, vals_cache)

    assert dicts_to_write[ObjectHeader.__tablename__]["latitude"] == 43.5
    assert dicts_to_write[ObjectHeader.__tablename__]["objdate"] == datetime.date(2021, 5, 15)
    assert dicts_to_write[ObjectHeader.__tablename__]["orig_id"] == "test_obj_1"

    # Check nested structure: vals_cache[field_name][raw_val] == produced_val
    assert vals_cache["object_lat"]["43°30 00"] == 43.5
    assert vals_cache["object_date"]["2021-05-15"] == datetime.date(2021, 5, 15)
    assert vals_cache["object_id"]["test_obj_1"] == "test_obj_1"

    # Second line with same raw values should hit the cache
    dicts_to_write_2 = {alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()}
    TSVFile.read_fields_to_dicts(how, field_set, lig, dicts_to_write_2, vals_cache)
    assert dicts_to_write_2[ObjectHeader.__tablename__]["latitude"] == 43.5
    assert dicts_to_write_2[ObjectHeader.__tablename__]["objdate"] == datetime.date(2021, 5, 15)
    assert dicts_to_write_2[ObjectHeader.__tablename__]["orig_id"] == "test_obj_1"


def test_validate_line_seen_vals_structure():
    """Verify that seen_vals in validate_line is populated as Dict[str, Set[Any]] mapping field_name -> Set[raw_val]."""
    headers = ["object_id", "img_file_name", "object_lat", "object_lon", "object_date"]
    tsv = _create_tsv_file_instance(headers)

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    lig = {
        "object_id": "obj1",
        "img_file_name": "1.png",
        "object_lat": "43.5",
        "object_lon": "7.3",
        "object_date": "2021-05-15",
    }
    tsv.validate_line(how, diag, lig, 1, seen_vals)

    # Check that seen_vals is a dict of sets mapping raw_field -> set of seen raw values
    assert isinstance(seen_vals, dict)
    assert isinstance(seen_vals["object_lat"], set)
    assert "43.5" in seen_vals["object_lat"]
    assert isinstance(seen_vals["object_lon"], set)
    assert "7.3" in seen_vals["object_lon"]
    assert isinstance(seen_vals["object_date"], set)
    assert "2021-05-15" in seen_vals["object_date"]


def test_clean_fields_and_mapping_structure(tmp_path):
    """Verify that TSVFile.open populates clean_fields and get_fields_infos produces mapping_per_field."""
    tsv_content = (
        " Object_ID \tObJect_Lat\tObject_Date\tobject_area\tacq_operator\tunmapped_col\tinvalidprefix_col\n"
        "[t]\t[f]\t[t]\t[f]\t[t]\t[t]\t[t]\n"
        "obj1\t43.5\t2021-05-15\t123.45\toperator1\tsome_text\tother_text\n"
    )
    tsv_path = tmp_path / "test.tsv"
    tsv_path.write_text(tsv_content, encoding="utf-8")

    tsv = TSVFile(tsv_path, "test.tsv", tmp_path)
    with tsv.open():
        assert isinstance(tsv.clean_fields, OrderedDict)
        assert tsv.clean_fields[" Object_ID "] == "object_id"
        assert tsv.clean_fields["ObJect_Lat"] == "object_lat"
        assert tsv.clean_fields["Object_Date"] == "object_date"
        assert tsv.clean_fields["object_area"] == "object_area"
        assert tsv.clean_fields["acq_operator"] == "acq_operator"
        assert tsv.clean_fields["unmapped_col"] == "unmapped_col"
        assert tsv.clean_fields["invalidprefix_col"] == "invalidprefix_col"

        how = ImportHow(1, False, ProjectMapping(), False, [], 1)
        how.custom_mapping.add_column(ObjectFields.__tablename__, "object", "area", "n")
        how.custom_mapping.add_column(Acquisition.__tablename__, "acq", "operator", "t")
        mapping = tsv.get_fields_infos(how)
        assert mapping["object_id"]["type"] == "t"
        assert mapping["object_lat"]["type"] == "n"
        assert mapping["object_date"]["type"] == "t"
        assert mapping["object_area"]["type"] == "n"
        assert mapping["acq_operator"]["type"] == "t"
        assert "unmapped_col" not in mapping
        assert "invalidprefix_col" not in mapping


def test_validate_line_skips_unmapped_columns():
    """Verify that validate_line skips unmapped columns (where field is not in mapping_per_field)."""
    headers = ["object_id", "img_file_name", "object_lat", "unmapped_col"]
    tsv = TSVFile(Path("/tmp/dummy.tsv"), "dummy.tsv", Path("/tmp"))
    tsv.clean_fields = OrderedDict([
        ("object_id", "object_id"),
        ("img_file_name", "img_file_name"),
        ("object_lat", "object_lat"),
        ("unmapped_col", "unmapped_col"),
    ])

    how = ImportHow(1, False, ProjectMapping(), False, [], 1)
    diag = ImportDiagnostic()
    seen_vals = {}

    lig = {
        "object_id": "obj1",
        "img_file_name": "1.png",
        "object_lat": "43.5",
        "unmapped_col": "some_value",
    }
    tsv.validate_line(how, diag, lig, 1, seen_vals)

    # unmapped_col should not be registered in diag.cols_seen or seen_vals
    assert "unmapped_col" not in diag.cols_seen
    assert "unmapped_col" not in seen_vals
    assert "object_lat" in diag.cols_seen
