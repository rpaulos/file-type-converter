import dataclasses
from pathlib import Path

import pytest

from file_converter import registry
from file_converter.registry import (
    Converter,
    ConversionError,
    common_targets,
    normalize_ext,
    output_path,
    register,
    targets_for,
)


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    """Give every test a fresh, empty converter list."""
    monkeypatch.setattr(registry, "_converters", [])

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


def fake_convert(src, dst):
    pass


def make_converter(**overrides):
    fields = dict(
        name="Fake",
        inputs=frozenset({"aaa"}),
        outputs=frozenset({"bbb"}),
        func=fake_convert,
    )
    fields.update(overrides)
    return Converter(**fields)


def test_conversion_error_is_an_exception():
    with pytest.raises(ConversionError, match="broken file"):
        raise ConversionError("broken file")


def test_converter_stores_its_fields():
    c = make_converter()
    assert c.name == "Fake"
    assert "aaa" in c.inputs
    assert "bbb" in c.outputs
    assert c.func is fake_convert


def test_converter_is_available_by_default():
    assert make_converter().is_available() is True


def test_converter_can_have_custom_availability():
    c = make_converter(is_available=lambda: False)
    assert c.is_available() is False


def test_converter_is_frozen():
    c = make_converter()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.name = "Changed"


def test_register_adds_a_converter():
    @register("Fake", inputs=["aaa"], outputs=["bbb"])
    def convert_fake(src, dst):
        pass

    assert len(registry._converters) == 1
    c = registry._converters[0]
    assert c.name == "Fake"
    assert c.func is convert_fake


def test_register_normalizes_extensions():
    @register("Fake", inputs=[".JPEG", "PNG"], outputs=["TIF"])
    def convert_fake(src, dst):
        pass

    c = registry._converters[0]
    assert c.inputs == frozenset({"jpg", "png"})
    assert c.outputs == frozenset({"tiff"})


def test_register_returns_the_function_unchanged():
    @register("Fake", inputs=["aaa"], outputs=["bbb"])
    def convert_fake(src, dst):
        return "still works"

    assert convert_fake(None, None) == "still works"


def test_register_is_available_by_default():
    @register("Fake", inputs=["aaa"], outputs=["bbb"])
    def convert_fake(src, dst):
        pass

    assert registry._converters[0].is_available() is True


def test_register_custom_availability():
    @register("Fake", inputs=["aaa"], outputs=["bbb"], is_available=lambda: False)
    def convert_fake(src, dst):
        pass

    assert registry._converters[0].is_available() is False


def add_fake(inputs, outputs, available=True):
    """Register a do-nothing converter for testing."""
    register("Fake", inputs=inputs, outputs=outputs, is_available=lambda: available)(fake_convert)


def test_targets_for_file_name():
    add_fake(["png", "jpg"], ["png", "jpg", "webp"])
    assert targets_for("photo.png") == ["jpg", "webp"]   # sorted, own format excluded


def test_targets_for_accepts_path_and_bare_extension():
    add_fake(["png", "jpg"], ["png", "jpg", "webp"])
    assert targets_for(Path("C:/pics/photo.PNG")) == ["jpg", "webp"]
    assert targets_for("png") == ["jpg", "webp"]


def test_targets_for_understands_aliases():
    add_fake(["png", "jpg"], ["png", "jpg", "webp"])
    assert targets_for("photo.jpeg") == ["png", "webp"]


def test_targets_for_combines_converters():
    add_fake(["csv"], ["xlsx"])
    add_fake(["csv"], ["json"])
    assert targets_for("data.csv") == ["json", "xlsx"]


def test_targets_for_unknown_type():
    add_fake(["png"], ["jpg"])
    assert targets_for("song.mp3") == []


def test_targets_for_skips_unavailable_converters():
    add_fake(["docx"], ["pdf"], available=False)
    assert targets_for("report.docx") == []


def test_common_targets_keeps_shared_formats():
    add_fake(["png", "jpg", "gif"], ["png", "jpg", "gif", "pdf"])
    # png -> jpg, gif, pdf   and   jpg -> png, gif, pdf   → shared: gif, pdf
    assert common_targets(["a.png", "b.jpg"]) == ["gif", "pdf"]


def test_common_targets_mixed_types_share_nothing():
    add_fake(["png"], ["jpg"])
    add_fake(["csv"], ["xlsx"])
    assert common_targets(["a.png", "b.csv"]) == []


def test_common_targets_empty_list():
    assert common_targets([]) == []

def test_output_path_next_to_source(tmp_path):
    src = tmp_path / "photo.png"
    assert output_path(src, "jpg") == tmp_path / "photo.jpg"


def test_output_path_accepts_a_string(tmp_path):
    src = str(tmp_path / "photo.png")
    assert output_path(src, "jpg") == tmp_path / "photo.jpg"


def test_output_path_normalizes_extension(tmp_path):
    src = tmp_path / "photo.png"
    assert output_path(src, ".JPEG") == tmp_path / "photo.jpg"


def test_output_path_never_overwrites(tmp_path):
    src = tmp_path / "photo.png"
    (tmp_path / "photo.jpg").touch()
    assert output_path(src, "jpg") == tmp_path / "photo (1).jpg"


def test_output_path_keeps_counting(tmp_path):
    src = tmp_path / "photo.png"
    (tmp_path / "photo.jpg").touch()
    (tmp_path / "photo (1).jpg").touch()
    assert output_path(src, "jpg") == tmp_path / "photo (2).jpg"


def test_output_path_custom_folder(tmp_path):
    src = tmp_path / "photo.png"
    out = tmp_path / "converted"
    assert output_path(src, "jpg", out) == out / "photo.jpg"


def test_output_path_does_not_create_the_file(tmp_path):
    src = tmp_path / "photo.png"
    assert not output_path(src, "jpg").exists()