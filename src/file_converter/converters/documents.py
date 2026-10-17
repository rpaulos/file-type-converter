"""Document conversions: text, Markdown and HTML to PDF, and Word documents to PDF."""

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from ..registry import ConversionError, normalize_ext, register
from .data import TEXT_ENCODINGS

# pywin32 only exists on Windows; without it, the Word converters simply stay unavailable
try:
    import win32com.client
    from pywintypes import com_error
except ImportError:
    win32com = None

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


WORD_FORMATS = ["docx", "doc", "rtf", "odt"]
WORD_PDF = 17    # Word's internal code for "save as PDF"


@lru_cache(maxsize=None)
def word_available() -> bool:
    """Is Microsoft Word installed? Checks the registry, so Word doesn't have to start."""
    if win32com is None:
        return False
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application").Close()
        return True
    except OSError:
        return False


@contextmanager
def word_app():
    """Start a hidden copy of Word, and always quit it afterwards."""
    word = win32com.client.DispatchEx("Word.Application")
    try:
        word.Visible = False
        word.DisplayAlerts = 0     # no pop-up dialogs waiting for a click nobody can see
        yield word
    finally:
        word.Quit(SaveChanges=0)


def word_error_message(exc) -> str:
    """Pull Word's own explanation (first line) out of a COM error."""
    try:
        return exc.excepinfo[2].splitlines()[0]
    except (AttributeError, IndexError, TypeError):
        return str(exc)


@register("Word to PDF", inputs=WORD_FORMATS, outputs=["pdf"], is_available=word_available)
def word_to_pdf(src: Path, dst: Path) -> None:
    try:
        with word_app() as word:
            doc = word.Documents.Open(str(src.resolve()), ReadOnly=True)
            try:
                doc.SaveAs2(str(dst.resolve()), FileFormat=WORD_PDF)
            finally:
                doc.Close(SaveChanges=0)
    except com_error as exc:
        raise ConversionError(f"{src.name}: {word_error_message(exc)}") from exc