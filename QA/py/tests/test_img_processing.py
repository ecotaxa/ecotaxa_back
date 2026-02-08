# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest
from PIL import Image as PIL_Image

from BO.Image import ImageBO
from DB.helpers.Bean import Bean
from FS.Vault import Vault
from test_import import SHARED_DIR

# Use existing test data
IMAGES_DIR = SHARED_DIR / "images"
RESIZED_DIR = IMAGES_DIR / "resized"
TEST_IMAGE = IMAGES_DIR / "0128.png"
TEST_IMAGES = [
    IMAGES_DIR / "0128.png",
    IMAGES_DIR / "9990.jpg",
    IMAGES_DIR / "4261.gif",
]


def compare_images(img1_path, img2_path):
    """Compare two images pixel by pixel."""
    with PIL_Image.open(img1_path) as im1, PIL_Image.open(img2_path) as im2:
        if im1.size != im2.size:
            return False
        return list(im1.getdata()) == list(im2.getdata())


@pytest.fixture
def temp_vault(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    return Vault(str(vault_path))


def test_validate_image():
    # Valid image
    ImageBO.validate_image(str(TEST_IMAGE))

    # Unsupported format (text file)
    bad_file = Path("bad_image.txt")
    bad_file.write_text("not an image")
    with pytest.raises(Exception):  # PIL might raise UnidentifiedImageError or similar
        ImageBO.validate_image(str(bad_file))
    bad_file.unlink()


def test_validate_image_too_large():
    # Trigger DecompressionBombError by reducing MAX_IMAGE_PIXELS
    old_max = PIL_Image.MAX_IMAGE_PIXELS
    # 0128.png is small, but we can set MAX_IMAGE_PIXELS even smaller
    im = PIL_Image.open(TEST_IMAGE)
    pixels = im.size[0] * im.size[1]
    im.close()

    PIL_Image.MAX_IMAGE_PIXELS = pixels // 2
    try:
        with pytest.raises(ImportError, match="Image too large"):
            ImageBO.validate_image(str(TEST_IMAGE))
    finally:
        PIL_Image.MAX_IMAGE_PIXELS = old_max


def test_validate_image_corrupted(tmp_path, monkeypatch):
    # Create a dummy file
    corrupted_file = tmp_path / "corrupted.png"
    corrupted_file.write_text("not really a png")

    # Mock PIL_Image.open to raise SyntaxError, as it's what ImageBO.validate_image expects for corrupted PNGs
    def mock_open(_path):
        raise SyntaxError("broken PNG file")

    monkeypatch.setattr("BO.Image.PIL_Image.open", mock_open)

    with pytest.raises(ImportError, match="Corrupted PNG"):
        ImageBO.validate_image(str(corrupted_file))


@pytest.mark.parametrize("img_path", TEST_IMAGES)
def test_dimensions_and_resize_no_resize(temp_vault, img_path):
    # Setup: put image in vault
    img_id = 123
    sub_path = temp_vault.store_image(img_path, img_id)

    image_to_write = Bean()
    image_to_write.imgid = img_id

    # max_dim larger than image
    im = PIL_Image.open(img_path)
    w, h = im.size
    im.close()

    max_dim = max(w, h) + 10

    ImageBO.dimensions_and_resize(max_dim, temp_vault, sub_path, image_to_write)

    assert image_to_write.width == w
    assert image_to_write.height == h
    assert image_to_write.thumb_width is None
    assert image_to_write.thumb_height is None

    # Check that no thumbnail was created
    _, thumb_abs = temp_vault.thumbnail_paths(img_id)
    assert not os.path.exists(thumb_abs)


@pytest.mark.parametrize("img_path", TEST_IMAGES)
def test_dimensions_and_resize_with_resize(temp_vault, img_path):
    # Setup: put image in vault
    img_id = 456
    sub_path = temp_vault.store_image(img_path, img_id)

    image_to_write = Bean()
    image_to_write.imgid = img_id

    im = PIL_Image.open(img_path)
    w, h = im.size
    im.close()

    max_dim = min(w, h) // 2
    if max_dim == 0:
        max_dim = 1

    ImageBO.dimensions_and_resize(max_dim, temp_vault, sub_path, image_to_write)

    assert image_to_write.width == w
    assert image_to_write.height == h
    assert image_to_write.thumb_width is not None
    assert image_to_write.thumb_height is not None
    assert image_to_write.thumb_width <= max_dim
    assert image_to_write.thumb_height <= max_dim

    # Check if thumbnail was actually created
    thumb_rel, thumb_abs = temp_vault.thumbnail_paths(img_id)
    assert os.path.exists(thumb_abs)

    # Comparison with reference
    ref_image = RESIZED_DIR / (img_path.stem + "_mini.jpg")
    assert ref_image.exists()
    assert compare_images(
        thumb_abs, ref_image
    ), f"Thumbnail {thumb_abs} differs from reference {ref_image}"
