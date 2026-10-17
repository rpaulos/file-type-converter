import pytest
from PIL import Image

import file_converter.converters  # noqa: F401  (registers the image converter)
from file_converter.registry import convert, targets_for


@pytest.fixture
def photo(tmp_path):
    """A small solid-red 40x30 PNG."""
    src = tmp_path / "photo.png"
    Image.new("RGB", (40, 30), (200, 50, 50)).save(src)
    return src


def test_png_offers_every_image_format():
    assert targets_for("photo.png") == ["bmp", "gif", "ico", "jpg", "pdf", "tiff", "webp"]


@pytest.mark.parametrize("target", ["jpg", "bmp", "gif", "tiff", "webp"])
def test_png_converts_to(photo, target):
    dst = convert(photo, target)
    assert dst.suffix == f".{target}"
    with Image.open(dst) as img:
        assert img.size == (40, 30)


def test_png_converts_to_ico(photo):
    dst = convert(photo, "ico")
    with Image.open(dst) as img:
        assert img.format == "ICO"


def test_png_converts_to_pdf(photo):
    dst = convert(photo, "pdf")
    assert dst.read_bytes().startswith(b"%PDF")   # every PDF file starts with these bytes


def test_jpeg_alias_works(photo):
    assert convert(photo, "jpeg").name == "photo.jpg"


def test_image_cannot_become_csv(photo):
    assert "csv" not in targets_for(photo)