import pytest

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtCore import QMimeData, QPointF, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QMessageBox

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

def file_mime(*paths):
    """The data Windows sends when files are dragged."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def drag_over(window, mime):
    event = QDragEnterEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    window.dragEnterEvent(event)
    return event


def drop(window, mime):
    event = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    window.dropEvent(event)
    return event


def test_accepts_dragged_files(window, tmp_path):
    mime = file_mime(make_png(tmp_path / "a.png"))
    assert drag_over(window, mime).isAccepted()


def test_ignores_dragged_text(window):
    mime = QMimeData()
    mime.setText("just some text")
    assert not drag_over(window, mime).isAccepted()


def test_dropping_files_adds_them(window, tmp_path):
    a = make_png(tmp_path / "a.png")
    b = make_png(tmp_path / "b.png")
    drop(window, file_mime(a, b))
    assert window.files() == [a, b]


def test_dropping_a_folder_adds_supported_files_inside(window, tmp_path):
    folder = tmp_path / "holiday"
    folder.mkdir()
    a = make_png(folder / "a.png")
    (folder / "notes.mp3").write_bytes(b"not music")
    csv = folder / "b.csv"
    csv.write_text("x\n1\n", encoding="utf-8")
    drop(window, file_mime(folder))
    assert window.files() == [a, csv]          # the .mp3 is quietly left out


def test_dropping_unsupported_file_shows_message(window, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: shown.append(args))
    song = tmp_path / "song.mp3"
    song.write_bytes(b"not music")
    drop(window, file_mime(song))
    assert window.files() == []
    assert "song.mp3" in shown[0][2]           # the message text names the file