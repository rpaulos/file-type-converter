"""The desktop window."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from . import __version__, converters  # noqa: F401  (registers every converter)
from .registry import common_targets, convert, supported_inputs, targets_for


class ConvertWorker(QThread):
    """Converts the files one by one in a background thread, so the window never freezes."""

    # sent after each file: its row in the list, whether it worked, and the new path or the error
    file_done = Signal(int, bool, str)

    def __init__(self, files: list[Path], target: str, out_dir: Path | None) -> None:
        super().__init__()
        self.files = files
        self.target = target
        self.out_dir = out_dir

    def run(self) -> None:
        """This is what runs in the background thread once start() is called."""
        for row, path in enumerate(self.files):
            if self.isInterruptionRequested():   # the window is closing: stop here
                break
            try:
                dst = convert(path, self.target, self.out_dir)
                self.file_done.emit(row, True, str(dst))
            except Exception as exc:   # a ConversionError, or a surprise like a full disk
                self.file_done.emit(row, False, str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"File Type Converter {__version__}")
        self.resize(640, 480)
        self.setAcceptDrops(True)   # allow files to be dropped onto the window

        self.worker = None      # the background conversion, once one has been started
        self.converted = []     # the new files made by the last conversion
        self.busy = False       # True while a conversion is running

        # the list of files to convert
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)

        # buttons, each connected to the method that runs when it's clicked
        self.add_button = QPushButton("Add files…")
        self.add_button.clicked.connect(self.choose_files)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.file_list.clear)

        # arrange them: buttons side by side, everything else stacked top to bottom
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch()

        # where converted files go: None means "next to each original"
        self.output_folder = None

        # the "Convert to" dropdown
        self.format_box = QComboBox()
        self.format_box.setMinimumWidth(120)
        self.format_box.setPlaceholderText("Add files first")

        # save next to the originals, or in a folder of your choice
        self.same_folder = QCheckBox("Save next to the original files")
        self.same_folder.setChecked(True)
        self.same_folder.toggled.connect(self.on_same_folder_toggled)
        self.folder_label = QLabel("")

        options = QHBoxLayout()
        options.addWidget(QLabel("Convert to:"))
        options.addWidget(self.format_box)
        options.addSpacing(20)
        options.addWidget(self.same_folder)
        options.addStretch()

        # progress bar, then the two buttons that act on the whole list
        self.progress = QProgressBar()
        self.open_folder_button = QPushButton("Open output folder")
        self.open_folder_button.setEnabled(False)      # nothing converted yet
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.convert_button = QPushButton("Convert")
        self.convert_button.setEnabled(False)          # no files yet
        self.convert_button.clicked.connect(self.start_conversion)

        bottom = QHBoxLayout()
        bottom.addWidget(self.progress)
        bottom.addWidget(self.open_folder_button)
        bottom.addWidget(self.convert_button)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Files to convert:"))
        layout.addWidget(self.file_list)
        layout.addLayout(buttons)
        layout.addLayout(options)
        layout.addWidget(self.folder_label)
        layout.addLayout(bottom)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        # refresh the dropdown whenever files are added, removed or cleared
        model = self.file_list.model()
        model.rowsInserted.connect(self.refresh_formats)
        model.rowsRemoved.connect(self.refresh_formats)
        model.modelReset.connect(self.refresh_formats)

        # the Convert button wakes up once a format is picked
        self.format_box.currentIndexChanged.connect(self.update_convert_button)

        self.statusBar().showMessage("Add files, choose a format, then click Convert.")

    def files(self) -> list[Path]:
        """The files currently in the list."""
        return [Path(self.file_list.item(i).data(Qt.UserRole)) for i in range(self.file_list.count())]

    def add_files(self, paths) -> list[str]:
        """Add every supported file to the list; returns the names that were skipped."""
        already = set(self.files())
        skipped = []
        for p in paths:
            path = Path(p)
            # a folder: add the supported files directly inside it
            if path.is_dir():
                inside = [f for f in sorted(path.iterdir()) if f.is_file() and targets_for(f)]
                skipped += self.add_files(inside)
                continue
            if path in already:
                continue
            if not path.is_file() or not targets_for(path):
                skipped.append(path.name)
                continue
            item = QListWidgetItem(path.name)       # what the user sees
            item.setData(Qt.UserRole, str(path))    # the full path, kept hidden in the item
            item.setToolTip(str(path))              # shown when hovering
            self.file_list.addItem(item)
            already.add(path)
        return skipped

    def choose_files(self) -> None:
        """Open the "pick files" dialog."""
        patterns = " ".join(f"*.{ext}" for ext in supported_inputs())
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose files to convert", "", f"Supported files ({patterns});;All files (*)"
        )
        self.add_files_and_report(paths)

    def add_files_and_report(self, paths) -> None:
        """Add files, and tell the user about any that were skipped."""
        skipped = self.add_files(paths)
        if skipped:
            QMessageBox.information(self, "Some files were skipped",
                                    "These files can't be converted:\n\n" + "\n".join(skipped))

    def remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Files are being dragged over the window: say yes if they're files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Files were dropped: add them to the list."""
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        event.acceptProposedAction()
        self.add_files_and_report(paths)

    def refresh_formats(self, *_) -> None:
        """Fill the dropdown with the formats every file in the list can become."""
        current = self.format_box.currentText()
        targets = common_targets(self.files())
        self.format_box.clear()
        self.format_box.addItems(targets)

        # keep the user's choice if it's still possible
        if current in targets:
            self.format_box.setCurrentText(current)

        if not self.files():
            self.format_box.setPlaceholderText("Add files first")
        elif not targets:
            self.format_box.setPlaceholderText("No format fits all files")
        else:
            self.format_box.setPlaceholderText("Choose a format")

    def update_convert_button(self, *_) -> None:
        """Convert can be clicked once a format is picked, but not during a conversion."""
        self.convert_button.setEnabled(self.format_box.currentIndex() >= 0 and not self.busy)

    def on_same_folder_toggled(self, checked: bool) -> None:
        """Ticked: save next to the originals. Unticked: ask for a folder."""
        if checked:
            self.output_folder = None
            self.folder_label.setText("")
            return

        folder = QFileDialog.getExistingDirectory(self, "Choose where to save the converted files")
        if folder:
            self.output_folder = Path(folder)
            self.folder_label.setText(f"Saving to: {folder}")
        else:
            self.same_folder.setChecked(True)   # cancelled: go back to "next to the originals"

    def set_busy(self, busy: bool) -> None:
        """While converting, lock everything that could change the list or the settings."""
        self.busy = busy
        for widget in (self.add_button, self.remove_button, self.clear_button,
                       self.format_box, self.same_folder):
            widget.setEnabled(not busy)
        self.setAcceptDrops(not busy)
        self.update_convert_button()

    def start_conversion(self) -> None:
        """Convert every file in the list, in the background."""
        files = self.files()

        # wipe the ✔ and ✖ marks from an earlier conversion
        for row, path in enumerate(files):
            item = self.file_list.item(row)
            item.setText(path.name)
            item.setToolTip(str(path))

        self.converted = []
        self.progress.setRange(0, len(files))
        self.progress.setValue(0)
        self.open_folder_button.setEnabled(False)
        self.statusBar().showMessage("Converting…")
        self.set_busy(True)

        self.worker = ConvertWorker(files, self.format_box.currentText(), self.output_folder)
        self.worker.file_done.connect(self.on_file_done)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.start()

    def on_file_done(self, row: int, ok: bool, message: str) -> None:
        """One file is finished: mark it ✔ or ✖ and move the progress bar on."""
        item = self.file_list.item(row)
        name = Path(item.data(Qt.UserRole)).name
        if ok:
            item.setText(f"✔  {name}")
            item.setToolTip(f"Saved as {message}")
            self.converted.append(Path(message))
        else:
            item.setText(f"✖  {name}")
            item.setToolTip(message)                 # hover to see what went wrong
        self.progress.setValue(self.progress.value() + 1)

    def on_conversion_finished(self) -> None:
        """Every file is done: say how it went and unlock the window."""
        failed = len(self.worker.files) - len(self.converted)
        message = f"Done: {len(self.converted)} converted"
        if failed:
            message += f", {failed} failed (hover over a ✖ to see why)"
        self.statusBar().showMessage(message)
        self.open_folder_button.setEnabled(bool(self.converted))
        self.set_busy(False)

    def open_output_folder(self) -> None:
        """Show the converted files in File Explorer."""
        folder = self.converted[0].parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self, event) -> None:
        """Closing during a conversion: finish the current file, skip the rest, then close."""
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait()
        super().closeEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.add_files_and_report(sys.argv[1:])   # files dropped onto the app's icon
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
