"""Document conversions: text, Markdown and HTML to PDF."""

from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from ..registry import ConversionError, normalize_ext, register
from .data import TEXT_ENCODINGS

TEXT_FORMATS = ["txt", "md", "html"]

# Qt needs one "application" object before it can measure fonts and draw text.
_qt_app = None


def ensure_qt_app() -> None:
    """Create Qt's application object, unless the app window already made one."""
    global _qt_app
    if QGuiApplication.instance() is None:
        _qt_app = QGuiApplication([])


def read_text_file(path: Path) -> str:
    """Read a text file, trying each encoding until one works."""
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ConversionError(f"{path.name}: can't work out the text encoding")


@register("Text to PDF", inputs=TEXT_FORMATS, outputs=["pdf"])
def text_to_pdf(src: Path, dst: Path) -> None:
    ensure_qt_app()
    text = read_text_file(src)

    # load the text; Qt understands Markdown and HTML formatting
    doc = QTextDocument()
    kind = normalize_ext(src.suffix)
    if kind == "md":
        doc.setMarkdown(text)
    elif kind == "html":
        doc.setHtml(text)
    else:
        doc.setPlainText(text)

    # "print" it into a PDF file: A4 paper with 2 cm margins
    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Millimeter)
    doc.print_(writer)