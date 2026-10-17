from file_converter.registry import normalize_ext


def test_lowercases_and_strips_dot():
    assert normalize_ext(".PNG") == "png"


def test_works_without_dot():
    assert normalize_ext("png") == "png"


def test_jpeg_becomes_jpg():
    assert normalize_ext(".jpeg") == "jpg"
    assert normalize_ext("JPEG") == "jpg"


def test_tif_becomes_tiff():
    assert normalize_ext("tif") == "tiff"


def test_unknown_extension_is_unchanged():
    assert normalize_ext(".webp") == "webp"