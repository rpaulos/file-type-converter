"""The desktop window."""

import sys
from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget, QCheckBox, QComboBox
)

from . import __version__, converters  # noqa: F401  (registers every converter)
from .registry import supported_inputs, targets_for, common_targets


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"File Type Converter {__version__}")
        self.resize(640, 480)
        self.setAcceptDrops(True)   # allow files to be dropped onto the window

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

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Files to convert:"))
        layout.addWidget(self.file_list)
        layout.addLayout(buttons)
        layout.addLayout(options)
        layout.addWidget(self.folder_label)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        # refresh the dropdown whenever files are added, removed or cleared
        model = self.file_list.model()
        model.rowsInserted.connect(self.refresh_formats)
        model.rowsRemoved.connect(self.refresh_formats)
        model.modelReset.connect(self.refresh_formats)

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


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.add_files_and_report(sys.argv[1:])   # files dropped onto the app's icon
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())