import pytest
from PIL import Image
from PySide6.QtCore import Qt

from file_converter.gui import MainWindow


@pytest.fixture
def window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)      # pytest-qt closes it after the test
    return w


def make_png(path):
    Image.new("RGB", (20, 20), (200, 50, 50)).save(path)
    return path


def test_window_title(window):
    assert window.windowTitle().startswith("File Type Converter")


def test_starts_empty(window):
    assert window.files() == []


def test_add_supported_files(window, tmp_path):
    png = make_png(tmp_path / "a.png")
    csv = tmp_path / "b.csv"
    csv.write_text("x\n1\n", encoding="utf-8")
    assert window.add_files([png, csv]) == []
    assert window.files() == [png, csv]
    assert window.file_list.item(0).text() == "a.png"


def test_unsupported_and_missing_files_are_skipped(window, tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"not music")
    assert window.add_files([song, tmp_path / "gone.png"]) == ["song.mp3", "gone.png"]
    assert window.files() == []


def test_same_file_is_not_added_twice(window, tmp_path):
    png = make_png(tmp_path / "a.png")
    window.add_files([png])
    window.add_files([png])
    assert window.files() == [png]


def test_remove_selected(window, tmp_path):
    a = make_png(tmp_path / "a.png")
    b = make_png(tmp_path / "b.png")
    window.add_files([a, b])
    window.file_list.item(0).setSelected(True)
    window.remove_selected()
    assert window.files() == [b]


def test_clear_button(window, tmp_path, qtbot):
    window.add_files([make_png(tmp_path / "a.png")])
    qtbot.mouseClick(window.clear_button, Qt.LeftButton)
    assert window.files() == []