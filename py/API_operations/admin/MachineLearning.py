# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A service for machine learning setup/maintenance. ML is used for prediction, but here we have the core objects,
# which are not visible to 'ordinary' users.
#
from io import StringIO
from os.path import join

from API_models.crud import ProjectFilters
from API_operations.ObjectManager import ObjectManager
from API_operations.helpers.Service import Service
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB import Role
from DB.Project import ProjectIDT
from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from ML.CNN_feature_trainer import CNNFeatureTrainer
from ML.Deep_features_extractor import DeepFeaturesExtractor
from ML.Dimension_reducer import DimensionReducer
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class MachineLearningService(Service):
    """
        Admin part of ML in EcoTaxa.
    """

    def __init__(self):
        super().__init__()
        self.vault = Vault(join(self.link_src, 'vault'))
        self.models_dir = SavedModels(self.config)

    def train(self, current_user_id: UserIDT,
              prj_id: ProjectIDT,
              out_model: str) -> str:
        # Security barrier
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        obj_filter = ProjectFilters(statusfilter='V')
        with ObjectManager() as mgr:
            # Query like the API would do
            obj_with_parents, details, total = mgr.query(current_user_id=current_user_id, proj_id=prj_id,
                                                         return_fields=["txo.display_name", "img.file_name"],
                                                         order_field="obj.objid",
                                                         window_size=2000,
                                                         filters=obj_filter)
        # Prepare input data, in the form of CSV text:
        # e.g. 1,data/images/1.jpg,Cladocera
        pd_csv = StringIO()
        pd_csv.write("id,img_path,label\n")
        for an_obj_with_parents, fields in zip(obj_with_parents, details):
            objid = an_obj_with_parents[0]
            taxo, img_path = fields
            pd_csv.write("%d,%s,%s\n" % (objid, img_path, taxo))
        trainer = CNNFeatureTrainer(vault=self.vault, model_dir=self.models_dir)
        pd_csv.seek(0)
        trainer.run(pd_csv, out_model)
        # PCA
        reducer = DimensionReducer(vault=self.vault, model_dir=self.models_dir)
        pd_csv.seek(0)
        reducer.run(pd_csv, out_model)
        # Try a bit
        extractor = DeepFeaturesExtractor(vault=self.vault, model_dir=self.models_dir)
        pd_csv.seek(0)
        csv_out = extractor.test(pd_csv, out_model)
        csv_out.seek(0)
        ret = []
        for a_line in csv_out.readlines():
            ret.append(a_line)
            if len(ret) > 100:
                break
        return "".join(ret)
