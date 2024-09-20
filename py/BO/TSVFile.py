# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import csv
import datetime
import sys
from collections import OrderedDict
from pathlib import Path
from typing import (
    Dict,
    Set,
    Any,
    Mapping,
    Tuple,
    ClassVar,
    Optional,
    cast,
    Union,
    TextIO,
)

# noinspection PyPackageRequirements
from PIL import Image as PIL_Image  # type: ignore

import BO.Mappings as GlobalMapping
from BO.Mappings import ProjectMapping, ParentTableClassT
from BO.SpaceTime import compute_sun_position, USED_FIELDS_FOR_SUNPOS
from BO.Training import TrainingBOProvider
from BO.helpers.ImportHelpers import (
    ImportHow,
    ImportWhere,
    ImportDiagnostic,
    ImportStats,
)
from DB import Prediction
from DB.Acquisition import Acquisition
from DB.Object import (
    classif_qual_revert,
    ObjectHeader,
    ObjectFields,
    PREDICTED_CLASSIF_QUAL,
    USED_FIELDS_FOR_CLASSIF,
    HIDDEN_FIELDS_FOR_CLASSIF,
    VALIDATED_CLASSIF_QUAL,
    DUBIOUS_CLASSIF_QUAL,
)
from DB.Process import Process
from DB.Project import ProjectIDT
from DB.Sample import Sample
from DB.helpers import Session
from DB.helpers.Bean import Bean
from DB.helpers.Direct import text
from DB.helpers.ORM import detach_from_session
from helpers.DynamicLogs import get_logger
from .Image import ImageBO
from .ObjectSet import EnumeratedObjectSet
from .User import UserIDT
from .helpers.TSVHelpers import (
    clean_value,
    clean_value_and_none,
    to_float,
    none_to_empty,
    convert_degree_minute_float_to_decimal_degree,
)

logger = get_logger(__name__)

ABSORBED_DIFF_CLASSIF_WHEN = datetime.timedelta(seconds=1)


class TSVFile(object):
    """
    A tab-separated file, index of images with additional information about them.
    """

    def __init__(self, path: Path, user_loc: str, bundle_path: Path):
        self.path: Path = path
        self.user_loc: str = user_loc
        try:
            relative_file = path.relative_to(bundle_path)
            # relative name for recording what was done
            self.relative_name: str = relative_file.as_posix()
            # Images take TSV directory as base. The TSV can be in a bundle's subdirectory.
            self.image_dir = path.parent
        except ValueError:
            self.relative_name = path.as_posix()
            # Images are in the bundle
            self.image_dir = bundle_path

        # when open()-ed, below members are active
        self.rdr: csv.DictReader
        # key: not normalized field, from TSV header e.g. "\t ObJect_laT "
        # value: normalized field i.e. "object_lat"
        self.clean_fields: OrderedDict[str, str]
        # The 2nd line, with types
        # key: normalized field
        # value: TSV type e.g. [f]
        self.type_line: Dict[str, str]

    # noinspection PyAttributeOutsideInit
    def open(self) -> TextIO:
        csv_file = open(self.path.as_posix(), encoding="latin_1")
        first_3 = csv_file.read(3)
        if first_3 == "ï»¿":
            # BOM in latin-1 in unicode...
            csv_file.close()
            csv_file = open(self.path.as_posix(), encoding="utf-8-sig")
        else:
            # Rewind stream to avoid damaging the header
            csv_file.seek(0)
        # Read as a dict, first line gives the format
        self.rdr = csv.DictReader(csv_file, delimiter="\t", quotechar='"')
        # Cleanup field names, keeping original ones as key.
        clean_fields: OrderedDict[str, str] = OrderedDict()
        if self.rdr.fieldnames is not None:
            for raw_field in self.rdr.fieldnames:
                if raw_field is None:
                    continue
                clean_fields[raw_field] = raw_field.strip(" \t").lower()
        self.clean_fields = clean_fields
        # Read types line (2nd line in file)
        try:
            line_2 = self.rdr.__next__()
            self.type_line = {
                clean_fields[raw_field]: v
                for raw_field, v in line_2.items()
                if raw_field is not None
            }
        except StopIteration:
            self.type_line = {}
        # When called using "with", the file will be closed on code block leave
        return csv_file

    REPORT_EVERY: ClassVar = 100

    def do_import(self, where: ImportWhere, how: ImportHow, stats: ImportStats) -> int:
        """
        Import self into DB.
        """
        session = where.db_writer.session
        counter = stats.current_row_count
        training_provider = TrainingBOProvider(
            session,
            how.user_id,
            stats.start_time,
        )

        with self.open():
            # Only keep the fields we can persist, the ones ignored at first step would be signalled here as well
            # if we didn't prohibit the move to 2nd step in this case.
            field_set = set(self.clean_fields.values())
            field_set = self.filter_unused_fields(how, field_set) - set(
                GlobalMapping.DOUBLED_FIELDS.keys()
            )

            # We can now prepare ORM classes with optimal performance
            target_fields = self.dispatch_fields_by_table(how.custom_mapping, field_set)
            where.db_writer.narrow_to(target_fields[ObjectFields.__tablename__])

            both_categories_present: bool = (
                "object_annotation_category_id" in field_set
                and "object_annotation_category" in field_set
            )

            vals_cache: Dict[str, str] = dict()
            # Loop over all lines
            row_count_for_csv = 0
            for rawlig in self.rdr:
                # Bean counting
                row_count_for_csv += 1
                counter += 1

                # Value is wrongly deduced (by typings) as a mandatory str from the rdr, it's optional in fact
                rawlig2 = cast(Dict[str, Optional[str]], rawlig)

                lig = {self.clean_fields[field]: v for field, v in rawlig2.items()}

                if both_categories_present:
                    # Remove textual category if the category id is provided and populated
                    if clean_value(lig.get("object_annotation_category_id", "")) == "":
                        del lig["object_annotation_category_id"]
                    else:
                        del lig["object_annotation_category"]

                # First, read TSV line into dicts, faster than doing settattr()
                dicts_to_write: Dict[str, Dict] = {
                    alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()
                }
                self.read_fields_to_dicts(
                    how, field_set, lig, dicts_to_write, vals_cache
                )

                # Create SQLAlchemy mappers of the object itself and slaves (1<->1)
                object_head_to_write = Bean(
                    **dicts_to_write[ObjectHeader.__tablename__]
                ).with_columns(
                    # ObjectHeader.classif_auto_id.name,
                    # ObjectHeader.classif_auto_when.name,
                    # ObjectHeader.classif_auto_score.name,
                    ObjectHeader.training_id.name,
                )  # These columns _might_ be populated, but DBWriter needs them all the time for bulk insert
                object_fields_to_write = Bean(
                    **dicts_to_write[ObjectFields.__tablename__]
                )
                image_to_write = Bean(**dicts_to_write["images"])
                # Note: Parents are created the same way, _when needed_ (i.e. nearly never),
                #  in @see add_parent_objects
                prediction_to_write: Optional[Bean] = None

                if how.can_update_only:
                    self.update_parent_objects(how, session, dicts_to_write)
                else:
                    # Initial load
                    state = self.ensure_consistent_fields(
                        object_head_to_write, stats.start_time, how.user_id
                    )
                    if state == PREDICTED_CLASSIF_QUAL:
                        # Need to store a prediction
                        prediction_to_write = Bean(
                            {
                                "training_id": training_provider.get().training_id,
                                "classif_id": object_head_to_write["classif_id"],
                                "score": 1.0,
                            }
                        )

                    # Attempt to compute sun position
                    self.do_sun_position_field(object_head_to_write)
                    # Add parents
                    self.add_parent_objects(
                        how, session, object_head_to_write, dicts_to_write
                    )
                    # Care for existing images
                    key_exist_obj = "%s*%s" % (
                        object_head_to_write.orig_id,
                        image_to_write.orig_file_name,
                    )
                    if key_exist_obj in how.objects_and_images_to_skip:
                        logger.info(
                            "Image skipped: %s %s",
                            object_head_to_write.orig_id,
                            image_to_write.orig_file_name,
                        )
                        continue

                new_records = self.create_or_link_slaves(
                    how,
                    stats.start_time,
                    session,
                    object_head_to_write,
                    object_fields_to_write,
                    image_to_write,
                    training_provider,
                )

                where.db_writer.add_db_entities(
                    object_head_to_write,
                    object_fields_to_write,
                    image_to_write,
                    prediction_to_write,
                    new_records,
                )

                if new_records > 1:
                    # We now have an Id from sequences, so reference it.
                    how.existing_objects[
                        object_head_to_write.orig_id
                    ] = object_head_to_write.objid
                    how.image_ranks_per_obj[object_head_to_write.objid] = set()
                else:
                    # The key already exists with same value, checked in @see self.create_or_link_slaves
                    pass

                instead_image = None
                if new_records > 0 and how.vignette_maker:
                    # If there is need for a vignette, the file named in the TSV is NOT the one written,
                    # and pointed at, by the usual DB line. Instead, it's the vignette.
                    instead_image = how.vignette_maker.make_vignette(
                        image_to_write.orig_file_name
                    )
                    if how.vignette_maker.must_keep_original():
                        # TODO: Put the code below in a def
                        # In this case, the original image is kept in another DB line
                        backup_img_to_write = Bean(**dicts_to_write["images"])
                        backup_img_to_write.imgrank = 100
                        backup_img_to_write.thumb_width = None
                        backup_img_to_write.thumb_height = None
                        # Store backup image into DB
                        where.db_writer.add_vignette_backup(
                            object_head_to_write, backup_img_to_write
                        )
                        # Store original image
                        orig_file_name = self.path_for_image(
                            image_to_write.orig_file_name
                        )
                        sub_path = where.vault.store_image(
                            orig_file_name, backup_img_to_write.imgid
                        )
                        # Get original image dimensions
                        im = PIL_Image.open(where.vault.image_path(sub_path))
                        (
                            backup_img_to_write.width,
                            backup_img_to_write.height,
                        ) = im.size
                        del im

                if new_records > 0:
                    self.deal_with_images(where, how, image_to_write, instead_image)

                if (counter % self.REPORT_EVERY) == 0:
                    where.db_writer.persist()
                    session.commit()
                    stats.report(counter)

        return row_count_for_csv

    @staticmethod
    def do_sun_position_field(object_head_to_write: Bean):
        """
        Initial compute or update of sun position field.
        """
        # Default value, so there is something to write into the DB in case of problem
        object_head_to_write.sunpos = "?"
        # Is there enough data for computation?
        nb_fields = object_head_to_write.nb_fields_from(USED_FIELDS_FOR_SUNPOS)
        if nb_fields < len(USED_FIELDS_FOR_SUNPOS):
            if nb_fields > 0:
                # Warn if only a few fields, but not if 0
                logger.warning("Not enough fields for computing sun position")
            return
        # All fields are in, so give it a try
        try:
            object_head_to_write.sunpos = compute_sun_position(object_head_to_write)
        except Exception as e:
            # See astral.py for cases
            # Astral error : Sun never reaches 12.0 degrees below the horizon, at this location.
            # for {'objtime': datetime.time(12, 29), 'latitude': -64.2, 'objdate': datetime.date(2011, 1, 9),
            # 'longitude': -52.59 }
            logger.error("Astral error : %s for %s", e, object_head_to_write)

    @staticmethod
    def ensure_consistent_fields(
        object_head_to_write: Bean,
        start_time: Optional[datetime.datetime],
        current_user: UserIDT,
    ) -> Optional[str]:
        """
        Some fields need defaults to keep consistency.
        - 'Validated' and 'Dubious' need a category (forced during TSV read), an author and a date
        - 'Predicted' should set same fields as a prediction which ran inside EcoTaxa
        """
        state = object_head_to_write.get("classif_qual")
        if start_time is None:
            return state  # No time provided to update the record, is must be that the full one is sent (during Subset)
        if state == PREDICTED_CLASSIF_QUAL:
            classif_id = object_head_to_write.get("classif_id")
            assert classif_id
            # Provide reasonable default values
            # object_head_to_write["classif_auto_id"] = classif_id
            # object_head_to_write["classif_auto_when"] = datetime.datetime.fromtimestamp(
            #     start_time
            # )
            # object_head_to_write["classif_auto_score"] = 1.0
            # These are for manual states 'V' or 'D'. When 'P' we wipe them
            object_head_to_write["classif_who"] = None
            object_head_to_write["classif_when"] = None
        elif state in (VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL):
            if object_head_to_write.get("classif_who") is None:
                object_head_to_write["classif_who"] = current_user
            if object_head_to_write.get("classif_when") is None:
                object_head_to_write["classif_when"] = start_time
        return state

    @staticmethod
    def prepare_classif_update(object_head: ObjectHeader, object_update: Bean) -> bool:
        """
        Detect intent to update classification related data: category, time of change, author
        """
        if object_head.classif_id != object_update.classif_id:
            return True  # Normal update, if relevant
        else:
            previous_state = object_head.classif_qual
            target_state = object_update.classif_qual
            if target_state == PREDICTED_CLASSIF_QUAL:
                if previous_state == PREDICTED_CLASSIF_QUAL:
                    # Assume that the new pseudo-prediction is not new, as it resulted in same category
                    # object_update.classif_auto_when = object_head.classif_auto_when
                    pass
                else:
                    return True  # Full state change
            else:
                # Human state
                if object_head.classif_who != object_update.classif_who:
                    return True  # Same classification, different author, update if relevant
                else:
                    upd_when = object_update.classif_when
                    # Just a date update, could be due to precision difference
                    if (
                        object_head.classif_when is not None
                        and upd_when is not None
                        and object_head.classif_when > upd_when
                        and object_head.classif_when - upd_when
                        < ABSORBED_DIFF_CLASSIF_WHEN
                    ):
                        object_update.classif_when = object_head.classif_when
                    else:
                        return True
        return False

    def path_for_image(self, image_path: str):
        """
        Path to an image referenced by self. Due to joinpath() behavior:
        - If no "/" in image_path: must be in same directory as self
        - If "/" in image_path but not leading / or drive letter: can be in a subdirectory
        - If leading / or drive letter: can be anywhere
        """
        return self.image_dir.joinpath(image_path)

    def filter_unused_fields(self, how: ImportHow, field_set: set) -> set:
        """
        Sanitize field list by removing the ones which are not known in mapping, nor used programmatically.
        :param how: import directives.
        :param field_set:
        :return:
        """
        ok_fields = set(
            [
                field
                for field in field_set
                if how.custom_mapping.search_field(field) is not None
                or field in GlobalMapping.PREDEFINED_FIELDS
                or field in GlobalMapping.DOUBLED_FIELDS
            ]
        )
        # Remove classification fields if updating but not classification
        if how.can_update_only and not how.update_with_classif:
            for fld in GlobalMapping.ANNOTATION_FIELDS.keys():
                if fld in ok_fields:
                    ok_fields.remove(fld)
        ko_fields = [field for field in field_set if field not in ok_fields]
        if len(ko_fields) > 0:  # pragma: no cover
            # This cannot happen as step1 prevents it. However the code is left in case API evolves.
            logger.warning(
                "In %s, field(s) %s not used, values will be ignored",
                self.user_loc,
                ko_fields,
            )
        return ok_fields

    @staticmethod
    def add_parent_objects(
        how: ImportHow,
        session: Session,
        object_head_to_write,
        dicts_to_write: Mapping[str, Dict],
    ):
        """
        Assignment of Sample, Acquisition & Process ID, creating them if necessary.
        Due to amount of duplicated information in TSV, this happens for few % of rows
         so no real need to optimize here.
        """
        assert not how.can_update_only

        # The data from TSV, to write. Eventually just an empty dict, but still a dict.
        dict_to_write = dicts_to_write[Sample.__tablename__]
        sample_orig_id = dict_to_write.get("orig_id")
        if sample_orig_id is None:  # No orig_id for the sample in provided dict
            sample_orig_id = "__DUMMY_ID__%d__" % how.prj_id
            # And inject the value for creation if needed
            dict_to_write["orig_id"] = sample_orig_id
        # Look for the sample by its (eventually amended) orig_id
        sample_before = how.existing_samples.get(sample_orig_id)
        if sample_before is not None:
            # Existing sample, store its PK for the Acquisition
            sample_pk = sample_before.pk()
        else:
            # Create a new sample
            new_sample = TSVFile.create_parent(
                session, dict_to_write, how.prj_id, Sample
            )
            # Store sample object for later reference, but detach it from ORM,
            # otherwise a simple call to .pk() provokes a select :(
            how.existing_samples[sample_orig_id] = detach_from_session(
                session, new_sample
            )
            # Store current PK for next iteration
            sample_pk = new_sample.pk()
            # Log the appeared sample
            logger.info("++ ID sample %s %d", sample_orig_id, sample_pk)

        # The data from TSV, to write. Eventually just an empty dict, but still a dict.
        dict_to_write = dicts_to_write[Acquisition.__tablename__]
        acquis_orig_id = dict_to_write.get("orig_id")
        if acquis_orig_id is None:  # No orig_id for acquisition in provided dict
            acquis_orig_id = "__DUMMY_ID__%d__" % sample_pk
            # And inject the value for creation if needed
            dict_to_write["orig_id"] = acquis_orig_id
        # Look for the acquisition by its (eventually amended) orig_id
        acquis_before = how.existing_acquisitions.get((sample_orig_id, acquis_orig_id))
        if acquis_before is not None:
            # Existing acquisition, in the same sample, store its PK for the Process & object
            acquis_pk = acquis_before.pk()
            upper_level_created = False
        else:
            # Acquisition does not exist with this orig_id inside the sample
            dict_to_write["acq_sample_id"] = sample_pk
            new_acquis = TSVFile.create_parent(
                session, dict_to_write, how.prj_id, Acquisition
            )
            # Store acquisition object for later reference, but detach it from ORM,
            # otherwise the simple call to .pk() below provokes a select :(
            how.existing_acquisitions[
                (sample_orig_id, acquis_orig_id)
            ] = detach_from_session(session, new_acquis)
            # Store current PK for following level
            acquis_pk = new_acquis.pk()
            upper_level_created = True
            # Log the appeared parent
            logger.info("++ ID acquisition %s %d", acquis_orig_id, acquis_pk)

        # Set parent of object
        object_head_to_write.acquisid = acquis_pk

        # Process is a twin table of Acquisition, its orig_id can be anything so no check to do.
        if not upper_level_created:
            # _only if_ enclosing Acquisition was just created then create process
            return
        dict_to_write = dicts_to_write[
            Process.__tablename__
        ]  # The data from TSV, to write.
        dict_to_write["processid"] = acquis_pk
        # Ensure an orig_id exists, as it's local we don't really need the composition but it doesn't hurt
        if dict_to_write.get("orig_id") is None:
            dict_to_write["orig_id"] = "__DUMMY_ID__%d__" % acquis_pk
        new_process = TSVFile.create_parent(session, dict_to_write, how.prj_id, Process)
        assert new_process is not None
        # Log the appeared process
        logger.info("++ ID process %s %d", new_process.orig_id, acquis_pk)

    @staticmethod
    def create_parent(
        session: Session, dict_to_write, prj_id: ProjectIDT, parent_class
    ):
        """
            Create the SQLAlchemy wrapper for Sample, Acquisition or Process.
        :return: The created DB wrapper.
        """
        # noinspection PyCallingNonCallable
        parent = parent_class(**dict_to_write)
        # Link with project
        parent.projid = prj_id
        session.add(parent)
        session.flush()
        return parent

    @staticmethod
    def update_parent_objects(
        how: ImportHow, session: Session, dicts_for_update: Mapping[str, Dict]
    ):
        """
        Update of Sample, Acquisition & Process.
        For locating the records, we tolerate the lack of orig_id like during creation.
        """
        assert how.can_update_only
        upper_level_pk = how.prj_id
        upper_level_orig_id = ""
        # Loop up->down, i.e. Sample to Process
        parent_class: ParentTableClassT
        for alias, parent_class in GlobalMapping.PARENT_CLASSES.items():
            # The data from TSV, to update with. Eventually just an empty dict, but still a dict.
            dict_for_update = dicts_for_update[alias]

            parent: Optional[Union[Sample, Acquisition, Process]]
            if parent_class != Process:
                # Locate using Sample & Acquisition orig_id
                parent_orig_id = dict_for_update.get("orig_id")
                if parent_orig_id is None:
                    # No orig_id for parent object in provided dict
                    # Default with present parent's parent technical ID
                    parent_orig_id = "__DUMMY_ID__%d__" % upper_level_pk
                # Look for the parent by its (eventually amended) orig_id
                if parent_class == Sample:
                    parent = how.existing_samples.get(parent_orig_id)
                else:
                    # Acquisition
                    parent = how.existing_acquisitions.get(
                        (upper_level_orig_id, parent_orig_id)
                    )
                if parent is None:
                    # No parent found for update, thus we cannot locate children, as there
                    # is an implicit relationship just by the fact that the 3 are on the same line
                    break
                # Collect the PK for children in case we need to use a __DUMMY
                upper_level_pk = parent.pk()
                upper_level_orig_id = parent_orig_id
            else:
                # Fetch the process from DB
                parent = session.query(Process).get(upper_level_pk)
                assert parent is not None

            # OK we have something to update
            # So update the DB line using sqlalchemy
            updates = TSVFile.update_orm_object(parent, dict_for_update)
            if len(updates) > 0:
                logger.info("Updating %s '%s' using %s", alias, parent.orig_id, updates)
                session.flush()

    @staticmethod
    def update_orm_object(
        model: Union[ObjectHeader, Sample, Acquisition, Process, ObjectFields],
        update_dict: Dict[str, Any],
    ):
        """
        In-memory update of the ORM record, based on the difference with a needed state.
        :return: An explanation text for the updates to come.
        """
        update_msgs = []
        for attr, value in model.__dict__.items():
            if attr in update_dict and update_dict[attr] != value:
                upd_val = update_dict[attr]
                setattr(model, attr, upd_val)
                update_msgs.append((attr, repr(value) + "->" + repr(upd_val)))
        # TODO: Extra values in update_dict ?
        return update_msgs

    @staticmethod
    def dispatch_fields_by_table(
        custom_mapping: ProjectMapping, field_set: Set
    ) -> Dict[str, Set]:
        """
            Build a set of target DB columns by target table.
        :param custom_mapping:
        :param field_set:
        :return:
        """
        ret: Dict[str, Set] = {
            alias: set() for alias in GlobalMapping.TARGET_CLASSES.keys()
        }
        for a_field in field_set:
            mapping = GlobalMapping.PREDEFINED_FIELDS.get(a_field)
            if not mapping:
                mapping = custom_mapping.search_field(a_field)
                assert mapping is not None
            target_tbl = mapping["table"]
            target_fld = mapping["field"]
            ret[target_tbl].add(target_fld)
        return ret

    @staticmethod
    def read_fields_to_dicts(
        how: ImportHow,
        field_set: Set[str],
        lig: Dict[str, Optional[str]],
        dicts_to_write,
        vals_cache: Dict,
    ):
        """
        Read the data line into target dicts. Values go into the right bucket, i.e. target dict, depending
        on mappings (standard one and per-project custom one).
        :param how: Importing directives.
        :param field_set: The fields present in DB record.
        :param lig: A line of TSV data, as {header: val} dict.
        :param dicts_to_write: The output data.
        :param vals_cache: A cache of values, per column and seen value.
        """
        predefined_mapping = GlobalMapping.PREDEFINED_FIELDS
        custom_mapping = how.custom_mapping
        # CSV reader returns a minimal dict with no value equal to None,
        # so we have values only for common fields.
        for a_field in field_set.intersection(lig.keys()):
            # We have a value
            raw_val = lig[a_field]
            m = predefined_mapping.get(a_field)
            if not m:
                m = custom_mapping.search_field(a_field)
                assert m is not None
            db_table = m["table"]
            db_col = m["field"]
            is_numeric = m["type"] == "n"
            # Try to get the transformed value from the cache
            cache_key: Tuple[str, Any] = (a_field, raw_val)
            if cache_key in vals_cache:
                cached_field_value = vals_cache.get(cache_key)
            else:
                csv_val = clean_value(raw_val, is_numeric)
                # If no relevant value, set field to NULL, i.e. None
                if csv_val == "":
                    cached_field_value = None
                elif a_field == "object_lat":
                    # It's [n] type but since UVPApp they can contain a notation like ddd°MM.SS
                    # which can be [t] as well.
                    cached_field_value = convert_degree_minute_float_to_decimal_degree(
                        csv_val
                    )
                elif a_field == "object_lon":
                    cached_field_value = convert_degree_minute_float_to_decimal_degree(
                        csv_val
                    )
                elif is_numeric:
                    cached_field_value = to_float(csv_val)
                elif a_field == "object_date":
                    cached_field_value = ObjectHeader.date_from_txt(csv_val)
                elif a_field == "object_time":
                    cached_field_value = ObjectHeader.time_from_txt(csv_val)
                elif db_col == "classif_when":
                    date = ObjectHeader.date_from_txt(csv_val)
                    csv_val_time = clean_value(
                        lig.get("object_annotation_time", "00:00:00")
                    )
                    time = ObjectHeader.time_from_txt(csv_val_time)

                    cached_field_value = datetime.datetime.combine(date, time)
                    # no caching of this one as it depends on another value on same line
                    cache_key = ("0", None)
                elif db_col == "classif_id":
                    # We map 2 fields to classif_id, the second (text one) has [t] type, treated here.
                    # The first, numeric, version is in "if type=n" case above.
                    mapped_val = how.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Use initial mapping
                    cached_field_value = how.found_taxa[
                        none_to_empty(mapped_val).lower()
                    ]
                    # better crash than write bad value into the DB
                    assert (
                        cached_field_value is not None
                    ), "Column %s: no classification of %s mapped as %s" % (
                        a_field,
                        csv_val,
                        mapped_val,
                    )
                elif db_col == "classif_who":
                    # Eventually map to another user if asked so
                    usr_key = none_to_empty(csv_val).lower()
                    cached_field_value = how.found_users[usr_key].get("id", None)
                elif db_col == "classif_qual":
                    cached_field_value = classif_qual_revert.get(csv_val.lower())
                else:
                    # Assume it's an ordinary text field with nothing special
                    cached_field_value = csv_val
                # Cache if relevant, setting the cache_key to "0" above effectively voids
                vals_cache[cache_key] = cached_field_value

            # Write the field into the right object
            dict_to_write = dicts_to_write[db_table]
            dict_to_write[db_col] = cached_field_value
        # Ensure that all dicts' fields are valued, to None if needed. This is needed for bulk inserts,
        # in DBWriter.py, as SQL Alchemy core computes an insert for the first line and just injects the
        # data for following ones.
        for a_field in field_set.difference(lig.keys()):
            fld_mping = custom_mapping.search_field(a_field)
            m = predefined_mapping.get(a_field, fld_mping)
            assert m is not None
            if m["field"] not in dicts_to_write[m["table"]]:
                dicts_to_write[m["table"]][m["field"]] = None

    @staticmethod
    def create_or_link_slaves(
        how: ImportHow,
        start_time: Optional[datetime.datetime],
        session: Session,
        object_head_to_write,
        object_fields_to_write,
        image_to_write,
        training_provider: Optional[TrainingBOProvider] = None,
    ) -> int:
        """
        Create, link or update slave entities, i.e. head, fields, image.
        Also update them... TODO: Split/fork the def
        :returns the number of new records
        """
        if object_head_to_write.orig_id in how.existing_objects:
            # Set the objid which will be copied for storing the image, the object itself
            # will not be stored due to returned value.
            objid = how.existing_objects[object_head_to_write.orig_id]
            object_head_to_write.objid = objid
            if how.can_update_only:
                # noinspection DuplicatedCode
                for a_cls, its_pk, an_upd in zip(
                    [ObjectHeader, ObjectFields],
                    ["objid", "objfid"],
                    [object_head_to_write, object_fields_to_write],
                ):
                    filter_for_id = text("%s=%d" % (its_pk, objid))
                    # Fetch the record to update
                    obj = session.query(a_cls).filter(filter_for_id).first()
                    assert obj is not None
                    if a_cls == ObjectHeader:
                        an_upd.update_from_obj(  # Don't kill hidden but useful field(s)
                            obj, HIDDEN_FIELDS_FOR_CLASSIF, force=True
                        )
                        # Eventually refresh classification
                        if an_upd.nb_fields_from(USED_FIELDS_FOR_CLASSIF) > 0:
                            # Give the bean enough data for computation, as the update could be partial.
                            an_upd.update_from_obj(obj, USED_FIELDS_FOR_CLASSIF)
                            state = TSVFile.ensure_consistent_fields(
                                an_upd,
                                start_time=start_time,
                                current_user=how.user_id,
                            )
                            if (
                                obj.classif_qual != PREDICTED_CLASSIF_QUAL
                                and state == PREDICTED_CLASSIF_QUAL
                            ):
                                # Need to store a new prediction
                                pred = Prediction()
                                assert training_provider is not None
                                pred.training_id = training_provider.get().training_id
                                pred.object_id = objid
                                pred.classif_id = object_head_to_write["classif_id"]
                                pred.score = 1.0
                                session.add(pred)
                                session.flush()
                                an_upd["training_id"] = pred.training_id
                            # Care for classification historisation
                            if TSVFile.prepare_classif_update(obj, an_upd):
                                EnumeratedObjectSet.historize_classification_for(
                                    session,
                                    [objid],
                                    only_qual=None,  # TODO: Quite inefficient but simple
                                )
                        # Eventually refresh sun position
                        if an_upd.nb_fields_from(USED_FIELDS_FOR_SUNPOS) > 0:
                            # Give the bean enough data for computation
                            an_upd.update_from_obj(obj, USED_FIELDS_FOR_SUNPOS)
                            TSVFile.do_sun_position_field(an_upd)
                    updates = TSVFile.update_orm_object(obj, an_upd)
                    if len(updates) > 0:
                        logger.info("Updating '%s' using %s", filter_for_id, updates)
                        session.flush()
                ret = 0  # nothing to write
            else:
                # 'Simply' a line with a complementary image
                logger.info(
                    "One more image for %s:%s ",
                    object_head_to_write.orig_id,
                    image_to_write,
                )
                ret = 1  # just a new image
        else:
            if how.can_update_only:
                # No objects creation while updating
                logger.info(
                    "Object %s not found while updating ",
                    object_head_to_write.orig_id,
                )
                ret = 0
            else:
                ret = 3  # new image + new object_head + new object_fields
        return ret

    def deal_with_images(
        self,
        where: ImportWhere,
        how: ImportHow,
        image_to_write: Bean,
        instead_image: Optional[Path] = None,
    ):
        """
            Generate image, eventually the vignette, create DB line(s) and copy image file into vault.
        :param where:
        :param how:
        :param image_to_write:
        :param instead_image: Store this image instead of the one in Image record.
        :return:
        """
        if instead_image:
            # Source file is a replacement
            img_file_path = instead_image
        else:
            # Files come from a subdirectory for UVP6 but from same directory for non-UVP6
            # TODO: Unsure if it works on Windows, as there is a "/" for UVP6
            img_file_path = self.path_for_image(image_to_write.orig_file_name)

        sub_path = where.vault.store_image(img_file_path, image_to_write.imgid)
        present_ranks = how.image_ranks_per_obj.setdefault(image_to_write.objid, set())
        if image_to_write.get("imgrank") is None:
            self.compute_rank(image_to_write, present_ranks)
        else:
            # The TSV format is float
            image_to_write.imgrank = int(image_to_write.imgrank)
            if image_to_write.imgrank in present_ranks:
                tsv_rank = image_to_write.imgrank
                self.compute_rank(image_to_write, present_ranks)
                logger.info(
                    "For %s, cannot use rank from TSV %d, using %d instead",
                    img_file_path,
                    tsv_rank,
                    image_to_write.imgrank,
                )
        present_ranks.add(image_to_write.imgrank)

        err = ImageBO.dimensions_and_resize(
            how.max_dim, where.vault, sub_path, image_to_write
        )
        if err:
            logger.error(err + ", not copied")

    @staticmethod
    def compute_rank(image_to_write, present_ranks):
        # No (more) duplicates, so pick next number from existing ones
        ranks_to_use = [a_rank for a_rank in present_ranks if a_rank < 100]
        if len(ranks_to_use) == 0:
            image_to_write.imgrank = 0
        else:
            image_to_write.imgrank = max(ranks_to_use) + 1

    def do_validate(self, how: ImportHow, diag: ImportDiagnostic):
        with self.open():
            self.validate_structure(how, diag)
            rows_for_csv = self.validate_content(how, diag)
            return rows_for_csv

    def validate_structure(self, how: ImportHow, diag: ImportDiagnostic):
        """
        TSV ordinary 'structure' is in first text line.
        Our implementation adds a line of expected types in second line.
        """
        a_field: str
        fields_per_prfx: OrderedDict[str, Set] = OrderedDict()
        for a_field in self.clean_fields.values():
            # split at first _ as the column name might contain an _
            split_col = a_field.split("_", 1)
            if len(split_col) != 2:
                diag.error(
                    "Invalid Header '%s'. Format must be Table_Field." % a_field,
                    self.user_loc,
                )
                continue
            # e.g. acq_sn -> acq
            tsv_table_prfx = split_col[0]
            # For consistency check inside each table
            fields_for_prfx = fields_per_prfx.setdefault(tsv_table_prfx, set())
            fields_for_prfx.add(a_field)
            if a_field in GlobalMapping.PREDEFINED_FIELDS:
                # OK it's a predefined one
                continue
            if a_field in GlobalMapping.DOUBLED_FIELDS:
                # Not mapped, but not a programmatically-used field
                continue
            # Not a predefined field, so nXX or tXX
            if how.custom_mapping.search_field(a_field) is not None:
                # Custom field was already mapped, in a previous import or another TSV of present import
                continue
            # e.g. acq -> acquisitions
            target_table = GlobalMapping.TSV_table_to_table(tsv_table_prfx)
            if target_table not in GlobalMapping.POSSIBLE_TABLES:
                diag.error(
                    "Invalid Header '%s'. Unknown table prefix '%s'."
                    % (a_field, target_table),
                    self.user_loc,
                )
                continue
            if target_table not in (
                ObjectHeader.__tablename__,
                ObjectFields.__tablename__,
            ):
                # In other tables, all types are forced to text
                sel_type = "t"
                # TODO: Tell the user that an eventual type is just ignored
            else:
                sel_type = self.type_line[a_field]
                try:
                    sel_type = GlobalMapping.POSSIBLE_TYPES[sel_type]
                except KeyError:
                    diag.error(
                        "Invalid Type '%s' for field '%s'." % (sel_type, a_field),
                        self.user_loc,
                    )
                    continue
            # Add the new custom column
            target_col = split_col[1]
            ok_added, real_name = how.custom_mapping.add_column(
                target_table, tsv_table_prfx, target_col, sel_type
            )
            if ok_added:
                logger.info(
                    "New field %s found in file %s -> %s",
                    a_field,
                    self.user_loc,
                    real_name,
                )
            else:
                diag.error(
                    "Field %s cannot be mapped. Too many custom fields, or bad type."
                    % a_field,
                    self.user_loc,
                )
            # Warn that project settings were extended, i.e. empty columns
            if not how.custom_mapping.was_empty:
                diag.warn(
                    "New field %s found in file %s -> %s"
                    % (a_field, self.user_loc, real_name)
                )
        # Ensure we have ids for all objects, at least potentially as we're just checking the header
        for a_prfx, fields in fields_per_prfx.items():
            if a_prfx not in GlobalMapping.PREFIX_TO_TABLE:
                continue
            expected_id = "%s_id" % a_prfx
            if expected_id not in fields:
                fields_for_msg = sorted(list(fields))  # Make the output predictable
                diag.error(
                    "Field %s is mandatory as there are some %s columns: %s."
                    % (expected_id, a_prfx, fields_for_msg),
                    self.user_loc,
                )

    def validate_content(self, how: ImportHow, diag: ImportDiagnostic):
        row_count_for_csv = 0
        vals_cache: Dict = {}
        local_keys: Dict[str, int] = {}
        logged_parents: Set[Tuple[Any, Any]] = set()
        lig: Dict
        for lig in self.rdr:
            row_count_for_csv += 1
            line_num = row_count_for_csv + 2

            self.validate_line(how, diag, lig, line_num, vals_cache)

            # Verify the image file
            object_id = clean_value_and_none(lig.get("object_id", ""))
            if object_id == "":
                diag.error(
                    "line %d: Missing object_id." % line_num,
                    self.user_loc,
                )
            img_file_name = clean_value_and_none(
                lig.get("img_file_name", "absent img_file_name")
            )
            # Below works as well for UVP6, as the file 'name' is in fact a relative path,
            # e.g. 'sub1/20200205-111823_3.png'
            img_file_path = self.path_for_image(img_file_name)
            if not img_file_path.exists():
                if not how.can_update_only:
                    # Images are not mandatory during update
                    diag.error(
                        "line %d: Missing Image '%s'." % (line_num, img_file_name),
                        self.user_loc,
                    )
            else:
                # noinspection PyBroadException
                try:
                    ImageBO.validate_image(img_file_path.as_posix())
                except Exception:
                    exc_str = str(sys.exc_info()[1]) + " " + str(sys.exc_info()[0])
                    # Drop the vault folder from the error message, if there.
                    exc_str = exc_str.replace(str(self.image_dir), "...")
                    diag.error(
                        "line %d: Error while reading image '%s': %s"
                        % (line_num, img_file_name, exc_str),
                        self.user_loc,
                    )

            # Verify duplicate images
            key_exist_obj = "%s*%s" % (object_id, img_file_name)
            if key_exist_obj in local_keys:
                previous_line = local_keys[key_exist_obj]
                diag.error(
                    "line %d: (Object '%s', Image '%s') is already in this TSV line %d."
                    % (line_num, object_id, img_file_name, previous_line),
                    self.user_loc,
                )
            elif not how.skip_object_duplicates:
                # Ban the duplicates, except if we can skip them.
                if key_exist_obj in diag.existing_objects_and_image:
                    diag.error(
                        "line %d: (Object '%s', Image '%s') is already in EcoTaxa or being imported."
                        % (line_num, object_id, img_file_name),
                        self.user_loc,
                    )
            local_keys[key_exist_obj] = row_count_for_csv + 2

            # Verify that we do not make the topology worse...
            if not how.can_update_only:
                sample_id = clean_value_and_none(lig.get("sample_id", ""))
                acquis_id = clean_value_and_none(lig.get("acq_id", ""))
                if not (sample_id, acquis_id) in logged_parents:
                    logger.info("sample: %s acquis: %s", sample_id, acquis_id)
                    logged_parents.add((sample_id, acquis_id))
                if sample_id != "" and acquis_id != "":
                    # Empty values are defaulted
                    maybe_err = diag.topology.evaluate_add_association(
                        sample_id, acquis_id
                    )
                    if maybe_err:
                        diag.error(maybe_err)
                # Add the association anyway, it will reduce the repetition of errors
                diag.topology.add_association(sample_id, acquis_id)

            # Verify that implied associated categories are really present
            classif_qual = lig.get("object_annotation_status", "")
            classif_id = lig.get(
                "object_annotation_category",
                lig.get("object_annotation_category_id", ""),
            ).strip()
            if classif_qual != "":
                if not classif_id:
                    diag.error(
                        "line %d: When annotation status '%s' is provided there has to be a category."
                        % (line_num, classif_qual),
                        self.user_loc,
                    )
            # Verify that a present category is associated with a state
            if classif_id != "":
                if classif_qual == "":
                    diag.error(
                        "line %d: When a category (%s) is provided it has to be with a status."
                        % (line_num, classif_id),
                        self.user_loc,
                    )

        # For other TSV analysis
        diag.existing_objects_and_image.update(local_keys.keys())

        return row_count_for_csv

    def validate_line(
        self,
        how: ImportHow,
        diag: ImportDiagnostic,
        lig: Dict[Optional[str], str],
        line_num: int,
        vals_cache: Dict,
    ):
        """
            Validate a line from data point of view.
        :param how:
        :param diag:
        :param lig:
        :param line_num: User (from 1) line number
        :param vals_cache:
        :return:
        """
        if None in lig.keys():
            diag.error(
                "line %d: Value(s) %s must not be in a header-less column."
                % (line_num, lig[None]),
                self.user_loc,
            )
            return
        latitude_was_seen = False
        predefined_mapping = GlobalMapping.PREDEFINED_FIELDS
        second_mapping = GlobalMapping.DOUBLED_FIELDS
        custom_mapping = how.custom_mapping
        for raw_field, a_field in self.clean_fields.items():
            m = predefined_mapping.get(a_field)
            if m is None:
                m = second_mapping.get(a_field)
                if m is None:
                    m = custom_mapping.search_field(a_field)
                    # No mapping, not stored
                    if m is None:
                        continue
            raw_val = lig.get(raw_field)
            # Try to get the value from the cache
            cache_key = (raw_field, raw_val)
            if cache_key in vals_cache:
                if a_field == "object_lat":
                    latitude_was_seen = True
                continue
            vals_cache[cache_key] = 1
            is_numeric = m["type"] == "n"
            # Same column with same value was not seen already, proceed
            csv_val: str = clean_value_and_none(raw_val, is_numeric)
            diag.cols_seen.add(a_field)
            # From V1.1, if column is present then it's considered as seen.
            #  Before, the criterion was 'at least one value'.
            if csv_val == "":
                # If no relevant value, leave field as NULL
                continue
            if a_field == "object_lat":
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf is None or vf < -90 or vf > 90:
                    diag.error(
                        "line %d: Invalid Lat. value '%s' for field '%s'. "
                        "Correct range is -90/+90°." % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
                    del vals_cache[cache_key]
                else:
                    latitude_was_seen = True
            elif a_field == "object_lon":
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf is None or vf < -180 or vf > 180:
                    diag.error(
                        "line %d: Invalid Long. value '%s' for field '%s'. "
                        "Correct range is -180/+180°." % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
            elif is_numeric:
                vf = to_float(csv_val)
                if vf is None:
                    diag.error(
                        "line %d: Invalid float value '%s' for field '%s'."
                        % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
                elif a_field == "object_annotation_category_id":
                    diag.classif_id_seen.add(int(vf))
            elif a_field in ("object_date", "object_annotation_date"):
                try:
                    ObjectHeader.date_from_txt(csv_val)
                except ValueError:
                    diag.error(
                        "line %d: Invalid Date value '%s' for field '%s'."
                        % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
            elif a_field in ("object_time", "object_annotation_time"):
                try:
                    ObjectHeader.time_from_txt(csv_val)
                except ValueError:
                    diag.error(
                        "line %d: Invalid Time value '%s' for field '%s'."
                        % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
            elif a_field == "object_annotation_category":
                if (
                    clean_value_and_none(lig.get("object_annotation_category_id", ""))
                    == ""
                ):
                    # Apply the mapping, if and only if there is no id
                    csv_val = how.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Record that the taxon was seen
                    how.found_taxa[csv_val.lower()] = None
            elif a_field == "object_annotation_person_name":
                maybe_email = clean_value_and_none(
                    lig.get("object_annotation_person_email", "")
                )
                # TODO: It's more "diag" than "how"
                how.found_users[csv_val.lower()] = {"email": maybe_email}
            elif a_field == "object_annotation_status":
                if csv_val != "noid" and csv_val.lower() not in classif_qual_revert:
                    diag.error(
                        "line %d: Invalid Annotation Status '%s' for field '%s'."
                        % (line_num, csv_val, raw_field),
                        self.user_loc,
                    )
        # Update missing GPS count
        if not latitude_was_seen:
            diag.nb_objects_without_gps += 1
