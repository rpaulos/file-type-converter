"""Document conversions: text and Word documents to PDF, and PDF back to Word or text."""

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader
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
WORD_DOCX = 16   # Word's internal code for "save as DOCX"


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


def save_with_word(src: Path, dst: Path, file_format: int) -> None:
    """Open src in hidden Word and save it as dst in one of Word's formats."""
    try:
        with word_app() as word:
            # ConfirmConversions=False: open PDFs without asking "Word will now convert..."
            doc = word.Documents.Open(str(src.resolve()), ConfirmConversions=False, ReadOnly=True)
            try:
                doc.SaveAs2(str(dst.resolve()), FileFormat=file_format)
            finally:
                doc.Close(SaveChanges=0)
    except com_error as exc:
        raise ConversionError(f"{src.name}: {word_error_message(exc)}") from exc


@register("Word to PDF", inputs=WORD_FORMATS, outputs=["pdf"], is_available=word_available)
def word_to_pdf(src: Path, dst: Path) -> None:
    save_with_word(src, dst, WORD_PDF)


@register("PDF to Word", inputs=["pdf"], outputs=["docx"], is_available=word_available)
def pdf_to_word(src: Path, dst: Path) -> None:
    # Word rebuilds the PDF as an editable document; simple layouts come out best
    save_with_word(src, dst, WORD_DOCX)


@register("PDF to text", inputs=["pdf"], outputs=["txt"])
def pdf_to_text(src: Path, dst: Path) -> None:
    pages = [(page.extract_text() or "").strip() for page in PdfReader(src).pages]

    # scanned PDFs are just pictures of pages: there's no text to pull out without OCR
    if not any(pages):
        raise ConversionError(f"{src.name} has no selectable text (it may be a scanned image)")

    # a blank line between pages
    dst.write_text("\n\n".join(pages), encoding="utf-8")


# ---- LibreOffice: the fallback when Word isn't installed ----------------------
# Registered after "Word to PDF", so the registry only uses it when Word is missing.

LIBREOFFICE_LOCATIONS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]
LIBREOFFICE_TIMEOUT = 120  # seconds


@lru_cache(maxsize=None)
def find_libreoffice() -> Path | None:
    """Where LibreOffice's soffice.exe is, or None if it isn't installed."""
    on_path = shutil.which("soffice")
    if on_path:
        return Path(on_path)
    for location in LIBREOFFICE_LOCATIONS:
        if location.is_file():
            return location
    return None


@register(
    "LibreOffice to PDF",
    inputs=WORD_FORMATS,
    outputs=["pdf"],
    is_available=lambda: find_libreoffice() is not None,
)
def libreoffice_to_pdf(src: Path, dst: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        command = [
            str(find_libreoffice()),
            # its own settings folder, so an open LibreOffice window can't interfere
            f"-env:UserInstallation={(tmp / 'profile').as_uri()}",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(tmp),
            str(src.resolve()),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=LIBREOFFICE_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            raise ConversionError(f"{src.name}: LibreOffice took too long") from exc

        # LibreOffice picks the output name itself (<stem>.pdf), so move it to our name
        made = tmp / f"{src.stem}.pdf"
        if result.returncode != 0 or not made.exists():
            raise ConversionError(f"{src.name}: LibreOffice couldn't convert it")
        shutil.move(made, dst)