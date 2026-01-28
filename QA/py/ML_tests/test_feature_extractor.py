import os
import pandas as pd
from typing import Any, Dict

# We set this one in env. and anyway TF is not working without it
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from unittest.mock import MagicMock
from ML.Deep_features_extractor import DeepFeaturesExtractor
from FS.Vault import Vault
from FS.MachineLearningModels import SavedModels

TEST_DIR = os.path.dirname(__file__)


def notest_deep_models_shape():
    vault = Vault(os.path.join(TEST_DIR, "vault"))
    config = MagicMock()
    config.get_cnf.return_value = os.path.join(TEST_DIR, "models")
    saved_models = SavedModels(config)
    df = DeepFeaturesExtractor(vault, saved_models)
    for a_model in saved_models.list():
        input_shape, my_fe, pca = df.load_model(a_model)
        print(input_shape)  # (224, 224, 3) for all models


THE_MODEL = "zooscan"


def test_deep_features_extractor():
    vault = Vault(os.path.join(TEST_DIR, "vault"))
    config = MagicMock()
    config.get_cnf.return_value = os.path.join(TEST_DIR, "models")
    saved_models = SavedModels(config)
    df = DeepFeaturesExtractor(vault, saved_models)
    assert THE_MODEL in saved_models.list()
    objects = read_test_images()
    res = df.run(objects, THE_MODEL)
    # res.to_csv(os.path.join(TEST_DIR, "deep_features.csv"))
    # Compare with expected
    expected = pd.read_csv(os.path.join(TEST_DIR, "deep_features.csv"), index_col="id")
    # Columns in CSV are strings "0", "1", etc.
    res.columns = res.columns.astype(str)
    pd.testing.assert_frame_equal(res, expected, atol=1e-3, check_dtype=False)


def test_missing_image():
    vault = Vault(os.path.join(TEST_DIR, "vault"))
    config = MagicMock()
    config.get_cnf.return_value = os.path.join(TEST_DIR, "models")
    saved_models = SavedModels(config)
    df = DeepFeaturesExtractor(vault, saved_models)
    assert THE_MODEL in saved_models.list()
    objects = read_test_images()
    objects[1000] = "foo" + objects[1000]
    res = df.run(objects, THE_MODEL)


def read_test_images() -> Dict[Any, Any]:
    objects = {}
    vault_path = os.path.join(TEST_DIR, "vault")
    objid = 100
    all_files = []
    for root, dirs, files in os.walk(vault_path):
        for f in files:
            if f.endswith(".png"):
                all_files.append(os.path.join(root, f))
    all_files.sort()
    for full_path in all_files:
        rel_path = os.path.relpath(full_path, vault_path)
        objects[objid] = rel_path
        objid += 1
    return objects
