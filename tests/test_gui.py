from pathlib import Path
from types import SimpleNamespace

import pytest

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtCore import QMimeData, QPointF, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QMessageBox, QFileDialog

from file_converter import gui, registry
from file_converter.converters.documents import word_available
from file_converter.gui import ConvertWorker, MainWindow


@pytest.fixture
def window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)      # pytest-qt closes it after the test
    return w


def make_png(path):
    Image.new("RGB", (20, 20), (200, 50, 50)).save(path)
    return path


def make_jpg(path):
    Image.new("RGB", (20, 20), (50, 50, 200)).save(path)
    return path


def test_window_title(window):
    assert window.windowTitle().startswith("File Type Converter")


def test_window_has_the_app_icon(window):
    assert not window.windowIcon().isNull()


def test_icon_file_has_every_size_windows_uses():
    sizes = Image.open(gui.ICON).info["sizes"]
    for size in [16, 24, 32, 48, 256]:
        assert (size, size) in sizes


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

def make_csv(path):
    path.write_text("x\n1\n", encoding="utf-8")
    return path


def formats(window):
    """Every format currently in the "Convert to" dropdown."""
    box = window.format_box
    return [box.itemText(i) for i in range(box.count())]


def test_no_formats_until_files_are_added(window):
    assert formats(window) == []


def test_formats_for_one_file(window, tmp_path):
    window.add_files([make_png(tmp_path / "a.png")])
    assert formats(window) == ["bmp", "gif", "ico", "jpg", "pdf", "tiff", "webp"]


def test_only_formats_every_file_can_become(window, tmp_path):
    window.add_files([make_png(tmp_path / "a.png"), make_csv(tmp_path / "b.csv")])
    assert formats(window) == []
    assert window.format_box.placeholderText() == "No format fits all files"


def test_formats_update_after_removing_a_file(window, tmp_path):
    window.add_files([make_png(tmp_path / "a.png"), make_csv(tmp_path / "b.csv")])
    window.file_list.item(1).setSelected(True)
    window.remove_selected()
    assert "jpg" in formats(window)


def test_clear_empties_the_formats(window, tmp_path, qtbot):
    window.add_files([make_png(tmp_path / "a.png")])
    qtbot.mouseClick(window.clear_button, Qt.LeftButton)
    assert formats(window) == []


def test_chosen_format_is_kept_when_files_change(window, tmp_path):
    window.add_files([make_png(tmp_path / "a.png")])
    window.format_box.setCurrentText("webp")
    jpg = tmp_path / "b.jpg"
    Image.new("RGB", (20, 20)).save(jpg)
    window.add_files([jpg])
    assert window.format_box.currentText() == "webp"


def test_saves_next_to_originals_by_default(window):
    assert window.same_folder.isChecked()
    assert window.output_folder is None


def test_choosing_an_output_folder(window, tmp_path, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(tmp_path))
    window.same_folder.setChecked(False)
    assert window.output_folder == tmp_path
    assert str(tmp_path) in window.folder_label.text()


def test_cancelling_the_folder_choice(window, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: "")
    window.same_folder.setChecked(False)
    assert window.same_folder.isChecked()        # back to "next to the originals"
    assert window.output_folder is None


def convert_all(window, qtbot, target):
    """Pick a format, click Convert, and wait for the background thread to finish."""
    window.format_box.setCurrentText(target)
    qtbot.mouseClick(window.convert_button, Qt.LeftButton)
    qtbot.waitUntil(lambda: not window.busy, timeout=60_000)   # Word can be slow to start


def test_asks_for_a_format_once_files_are_added(window, tmp_path):
    window.add_files([make_png(tmp_path / "a.png")])
    assert window.format_box.currentIndex() == -1          # nothing picked yet
    assert window.format_box.placeholderText() == "Choose a format"


def test_convert_button_needs_a_format(window, tmp_path):
    assert not window.convert_button.isEnabled()
    window.add_files([make_png(tmp_path / "a.png")])
    assert not window.convert_button.isEnabled()           # files, but no format yet
    window.format_box.setCurrentText("jpg")
    assert window.convert_button.isEnabled()
    window.add_files([make_csv(tmp_path / "b.csv")])       # no format fits both
    assert not window.convert_button.isEnabled()


def test_converts_every_file(window, qtbot, tmp_path):
    window.add_files([make_png(tmp_path / "a.png"), make_png(tmp_path / "b.png")])
    convert_all(window, qtbot, "jpg")
    assert (tmp_path / "a.jpg").exists()
    assert (tmp_path / "b.jpg").exists()
    assert window.file_list.item(0).text() == "✔  a.png"
    assert window.progress.value() == 2
    assert window.statusBar().currentMessage() == "Done: 2 converted"


def test_saves_into_the_chosen_folder(window, qtbot, tmp_path, monkeypatch):
    out = tmp_path / "converted"
    out.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(out))
    window.same_folder.setChecked(False)
    window.add_files([make_png(tmp_path / "a.png")])
    convert_all(window, qtbot, "webp")
    assert (out / "a.webp").exists()


def test_a_failed_file_is_marked_and_the_rest_carry_on(window, qtbot, tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"this is not really a picture")
    good = make_png(tmp_path / "good.png")
    window.add_files([broken, good])
    convert_all(window, qtbot, "jpg")
    assert window.file_list.item(0).text() == "✖  broken.png"
    assert "broken.png" in window.file_list.item(0).toolTip()      # the error message
    assert window.file_list.item(1).text() == "✔  good.png"
    assert "1 failed" in window.statusBar().currentMessage()


def test_window_is_locked_while_busy(window):
    window.set_busy(True)
    assert not window.add_button.isEnabled()
    assert not window.convert_button.isEnabled()
    assert not window.acceptDrops()
    window.set_busy(False)
    assert window.add_button.isEnabled()
    assert window.acceptDrops()


def test_converting_again_clears_old_marks(window, qtbot, tmp_path):
    window.add_files([make_png(tmp_path / "a.png")])
    convert_all(window, qtbot, "jpg")
    window.add_files([make_png(tmp_path / "b.png")])
    convert_all(window, qtbot, "gif")
    assert window.file_list.item(0).text() == "✔  a.png"
    assert window.progress.value() == 2


def test_open_output_folder(window, qtbot, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url))
    assert not window.open_folder_button.isEnabled()
    window.add_files([make_png(tmp_path / "a.png")])
    convert_all(window, qtbot, "jpg")
    qtbot.mouseClick(window.open_folder_button, Qt.LeftButton)
    assert Path(opened[0].toLocalFile()) == tmp_path


def test_closing_during_a_conversion_stops_it(window, qtbot, tmp_path):
    window.add_files([make_png(tmp_path / f"{n}.png") for n in range(30)])
    window.format_box.setCurrentText("tiff")
    qtbot.mouseClick(window.convert_button, Qt.LeftButton)
    window.close()
    assert not window.worker.isRunning()


def run_worker(qtbot, files, target):
    """Run a ConvertWorker on its own and collect its status messages."""
    worker = ConvertWorker(files, target, None)
    messages = []
    # DirectConnection: record each message straight away, in the worker's own thread.
    # Fine for adding to a list; widgets must never be touched like this.
    worker.status.connect(messages.append, Qt.DirectConnection)
    with qtbot.waitSignal(worker.finished, timeout=60_000):
        worker.start()
    return messages


def test_worker_says_which_file_it_is_on(qtbot, tmp_path):
    files = [make_png(tmp_path / "a.png"), make_png(tmp_path / "b.png")]
    assert run_worker(qtbot, files, "jpg") == [
        "Converting a.png (1 of 2)…",
        "Converting b.png (2 of 2)…",
    ]


def test_worker_says_when_it_starts_an_outside_app(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "_converters", [])     # only the fake converter below

    @registry.register("Fake Word", inputs=["docx"], outputs=["pdf"], app="Word")
    def fake_word(src, dst):
        dst.write_text("pretend PDF")

    doc = tmp_path / "letter.docx"
    doc.write_text("pretend document")
    assert run_worker(qtbot, [doc], "pdf") == ["Starting Word for letter.docx (1 of 1)…"]


def test_worker_sets_up_com_for_its_thread(qtbot, monkeypatch):
    calls = []
    fake_pythoncom = SimpleNamespace(
        CoInitialize=lambda: calls.append("set up"),
        CoUninitialize=lambda: calls.append("tidy up"),
    )
    monkeypatch.setattr(gui, "pythoncom", fake_pythoncom)
    run_worker(qtbot, [], "jpg")
    assert calls == ["set up", "tidy up"]


@pytest.mark.skipif(not word_available(), reason="needs Microsoft Word")
def test_word_documents_convert_in_the_background(window, qtbot, tmp_path):
    rtf = tmp_path / "letter.rtf"
    rtf.write_text(r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Calibri;}}\f0\fs24 Hello.\par}",
                   encoding="ascii")
    window.add_files([rtf])
    convert_all(window, qtbot, "pdf")
    assert window.file_list.item(0).text() == "✔  letter.rtf"
    assert (tmp_path / "letter.pdf").exists()


def test_png_and_jpg_together_can_become_either(window, tmp_path):
    window.add_files([make_png(tmp_path / "cat.png"), make_jpg(tmp_path / "holiday.jpg")])
    assert "png" in formats(window)
    assert "jpg" in formats(window)


def test_a_file_already_in_the_format_is_left_alone(window, qtbot, tmp_path):
    window.add_files([make_png(tmp_path / "cat.png"), make_jpg(tmp_path / "holiday.jpg")])
    convert_all(window, qtbot, "png")
    assert window.file_list.item(0).text() == "—  cat.png"
    assert "Already a .png" in window.file_list.item(0).toolTip()
    assert window.file_list.item(1).text() == "✔  holiday.jpg"
    assert sorted(p.name for p in tmp_path.glob("*.png")) == ["cat.png", "holiday.png"]
    assert window.statusBar().currentMessage() == "Done: 1 converted, 1 already png"
    assert window.progress.value() == 2


def test_worker_skips_quietly(qtbot, tmp_path):
    files = [make_png(tmp_path / "cat.png"), make_jpg(tmp_path / "holiday.jpg")]
    assert run_worker(qtbot, files, "png") == ["Converting holiday.jpg (2 of 2)…"]