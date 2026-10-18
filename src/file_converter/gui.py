"""The desktop window."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from . import __version__, converters  # noqa: F401  (registers every converter)
from .registry import supported_inputs, targets_for


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"File Type Converter {__version__}")
        self.resize(640, 480)

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

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Files to convert:"))
        layout.addWidget(self.file_list)
        layout.addLayout(buttons)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def files(self) -> list[Path]:
        """The files currently in the list."""
        return [Path(self.file_list.item(i).data(Qt.UserRole)) for i in range(self.file_list.count())]

    def add_files(self, paths) -> list[str]:
        """Add every supported file to the list; returns the names that were skipped."""
        already = set(self.files())
        skipped = []
        for p in paths:
            path = Path(p)
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


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.add_files_and_report(sys.argv[1:])   # files dropped onto the app's icon
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())