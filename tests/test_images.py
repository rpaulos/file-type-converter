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


@pytest.fixture
def logo(tmp_path):
    """A 40x30 PNG: left half solid red, right half fully transparent."""
    src = tmp_path / "logo.png"
    img = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
    img.paste((255, 0, 0, 255), (0, 0, 20, 30))
    img.save(src)
    return src


@pytest.mark.parametrize("target", ["jpg", "bmp"])
def test_transparent_areas_become_white(logo, target):
    dst = convert(logo, target)
    with Image.open(dst) as img:
        img = img.convert("RGB")
        r, g, b = img.getpixel((30, 15))       # a pixel in the transparent half
        assert min(r, g, b) > 240              # white (JPG can be off by a few)
        r, g, b = img.getpixel((5, 15))        # a pixel in the red half
        assert r > 200 and g < 50 and b < 50   # still red


def test_transparent_png_to_pdf(logo):
    dst = convert(logo, "pdf")
    assert dst.read_bytes().startswith(b"%PDF")


@pytest.mark.parametrize("target", ["webp", "tiff"])
def test_formats_with_transparency_keep_it(logo, target):
    dst = convert(logo, target)
    with Image.open(dst) as img:
        assert img.mode == "RGBA"
        assert img.getpixel((30, 15))[3] == 0  # alpha is still 0 = invisible


@pytest.fixture
def phone_photo(tmp_path):
    """A 40x30 JPG whose EXIF says 'rotate 90° clockwise when showing it'."""
    src = tmp_path / "phone.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6          # 0x0112 = the Orientation tag, 6 = rotate 90° clockwise
    Image.new("RGB", (40, 30), (0, 0, 255)).save(src, exif=exif)
    return src


@pytest.mark.parametrize("target", ["png", "webp", "bmp"])
def test_phone_photos_stay_upright(phone_photo, target):
    dst = convert(phone_photo, target)
    with Image.open(dst) as img:
        assert img.size == (30, 40)   # rotated: portrait, not landscape


def detailed_image():
    """A colourful gradient: lots of detail, so quality settings make a visible difference."""
    g = Image.linear_gradient("L").resize((128, 128))
    r = Image.radial_gradient("L").resize((128, 128))
    return Image.merge("RGB", (g, r, g.rotate(90)))


@pytest.mark.parametrize("target", ["jpg", "webp"])
def test_saves_at_higher_than_default_quality(tmp_path, target):
    src = tmp_path / "gradient.png"
    detailed_image().save(src)
    reference = tmp_path / f"pillow_default.{target}"
    detailed_image().save(reference)            # Pillow's default quality

    dst = convert(src, target)
    # higher quality keeps more detail, so the file is bigger
    assert dst.stat().st_size > reference.stat().st_size


def test_ico_from_non_square_image_is_square(photo):
    dst = convert(photo, "ico")                 # photo is 40x30
    with Image.open(dst) as img:
        assert all(w == h for w, h in img.info["sizes"])


def test_ico_pads_with_transparency(photo):
    dst = convert(photo, "ico")
    with Image.open(dst) as img:
        img = img.convert("RGBA")
        middle = img.width // 2
        assert img.getpixel((middle, 0))[3] == 0          # top edge: transparent padding
        assert img.getpixel((middle, middle))[3] == 255   # centre: the red photo


def test_big_image_gets_all_icon_sizes(tmp_path):
    src = tmp_path / "big.png"
    Image.new("RGB", (300, 200), (0, 128, 0)).save(src)
    dst = convert(src, "ico")
    with Image.open(dst) as img:
        for size in [(16, 16), (32, 32), (48, 48), (256, 256)]:
            assert size in img.info["sizes"]


def test_tiny_image_still_makes_a_valid_icon(tmp_path):
    src = tmp_path / "tiny.png"
    Image.new("RGB", (10, 10), (0, 0, 255)).save(src)
    dst = convert(src, "ico")
    with Image.open(dst) as img:
        assert img.size == (16, 16)


@pytest.fixture
def cmyk_photo(tmp_path):
    """A JPG saved with CMYK colours, like files exported for printing."""
    src = tmp_path / "print.jpg"
    Image.new("CMYK", (20, 20), (0, 255, 255, 0)).save(src)
    return src


@pytest.mark.parametrize("target", ["png", "gif", "bmp", "ico", "webp"])
def test_cmyk_jpg_converts(cmyk_photo, target):
    dst = convert(cmyk_photo, target)
    with Image.open(dst) as img:
        assert img.mode != "CMYK"