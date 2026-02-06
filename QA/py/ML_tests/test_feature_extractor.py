import pytest
import os
import sys
import pandas as pd
from typing import Any, Dict

# We set this one in env. and anyway TF is not working without it
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from unittest.mock import MagicMock
from ML.Deep_features_extractor import DeepFeaturesExtractor
from FS.Vault import Vault
from FS.MachineLearningModels import SavedModels

TEST_DIR = os.path.dirname(__file__)
THE_MODEL = "zooscan"


@pytest.fixture
def vault():
    return Vault(os.path.join(TEST_DIR, "vault"))


@pytest.fixture
def saved_models():
    config = MagicMock()
    config.get_cnf.return_value = os.path.join(TEST_DIR, "models")
    return SavedModels(config)


@pytest.fixture
def deep_extractor(vault, saved_models):
    return DeepFeaturesExtractor(vault, saved_models)


@pytest.fixture
def test_images():
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


def test_deep_models_shape(saved_models, deep_extractor):
    for a_model in saved_models.list():
        input_shape, my_fe, pca = deep_extractor.load_model(a_model)
        print(input_shape)  # (224, 224, 3) for all models


def test_deep_features_extractor(saved_models, deep_extractor, test_images):
    assert THE_MODEL in saved_models.list()
    res = deep_extractor.run(test_images, THE_MODEL)
    # res.to_csv(os.path.join(TEST_DIR, "deep_features.csv"))
    # Compare with expected
    expected = pd.read_csv(os.path.join(TEST_DIR, "deep_features.csv"), index_col="id")
    # Columns in CSV are strings "0", "1", etc.
    res.columns = res.columns.astype(str)
    tolerance = 0.05 if sys.version_info[:2] == (3, 12) else 0.001
    pd.testing.assert_frame_equal(res, expected, atol=tolerance, check_dtype=False)


def test_missing_image(saved_models, deep_extractor, test_images):
    assert THE_MODEL in saved_models.list()
    test_images[100] = "foo" + test_images[100]  # Use a valid key from test_images
    with pytest.raises(Exception):
        deep_extractor.run(test_images, THE_MODEL)
