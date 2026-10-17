import dataclasses

import pytest

from file_converter import registry
from file_converter.registry import Converter, ConversionError, normalize_ext, register


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