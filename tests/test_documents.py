import dataclasses
import re
import subprocess
import time
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

import file_converter.converters  # noqa: F401  (registers the document converters)
from file_converter import registry
from file_converter.converters import documents
from file_converter.converters.documents import word_app, word_available
from file_converter.registry import ConversionError, convert, targets_for


def pdf_text(path):
    """All the text inside a PDF, so tests can check what ended up in it."""
    return "\n".join(page.extract_text() for page in PdfReader(path).pages)


@pytest.mark.parametrize("name", ["notes.txt", "readme.md", "page.html"])
def test_text_formats_offer_pdf(name):
    assert targets_for(name) == ["pdf"]


@pytest.mark.parametrize("name", ["page.htm", "notes.markdown"])
def test_common_aliases_work(name):
    assert targets_for(name) == ["pdf"]


def test_txt_to_pdf(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("Buy milk\nCall Grace", encoding="utf-8")
    text = pdf_text(convert(src, "pdf"))
    assert "Buy milk" in text
    assert "Call Grace" in text


def test_markdown_becomes_formatting(tmp_path):
    src = tmp_path / "list.md"
    src.write_text("# Shopping\n\n- **Apples**\n- Pears", encoding="utf-8")
    text = pdf_text(convert(src, "pdf"))
    assert "Shopping" in text and "Apples" in text
    assert "#" not in text and "**" not in text   # symbols turned into real headings and bold


def test_html_tags_are_not_printed(tmp_path):
    src = tmp_path / "page.html"
    src.write_text("<h1>Title</h1><p>Hello <b>world</b></p>", encoding="utf-8")
    text = pdf_text(convert(src, "pdf"))
    assert "Title" in text and "world" in text
    assert "<h1>" not in text


def test_long_text_gets_several_pages(tmp_path):
    src = tmp_path / "long.txt"
    src.write_text("A line of text\n" * 200, encoding="utf-8")
    assert len(PdfReader(convert(src, "pdf")).pages) > 1


def test_accented_letters_survive(tmp_path):
    src = tmp_path / "cafe.txt"
    src.write_text("Café crème with Zoë", encoding="utf-8")
    assert "Café crème with Zoë" in pdf_text(convert(src, "pdf"))


def test_reads_text_saved_by_old_notepad(tmp_path):
    src = tmp_path / "old.txt"
    src.write_bytes("José lives in Málaga".encode("cp1252"))
    assert "José lives in Málaga" in pdf_text(convert(src, "pdf"))


# ---- Word -------------------------------------------------------------------

needs_word = pytest.mark.skipif(not word_available(), reason="needs Microsoft Word")

# A tiny RTF document written by hand. RTF is a plain-text format that Word opens;
# \'e9 and \'e8 are how RTF writes é and è.
RTF = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Calibri;}}\f0\fs24 Hello from Word. Caf\'e9 cr\'e8me.\par}"


@pytest.fixture
def rtf_file(tmp_path):
    src = tmp_path / "letter.rtf"
    src.write_text(RTF, encoding="ascii")
    return src


def word_processes() -> int:
    """How many copies of Word are running right now (visible or hidden)."""
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/NH"], capture_output=True, text=True
    ).stdout
    return out.upper().count("WINWORD.EXE")


@needs_word
@pytest.mark.parametrize("name", ["report.docx", "old.doc", "letter.rtf", "notes.odt"])
def test_word_formats_offer_pdf(name):
    assert "pdf" in targets_for(name)


@needs_word
def test_word_rtf_to_pdf(rtf_file):
    text = pdf_text(convert(rtf_file, "pdf"))
    assert "Hello from Word" in text
    assert "Café crème" in text


@needs_word
def test_word_docx_to_pdf(rtf_file):
    # make a real .docx by letting Word save the RTF as one (16 = Word's code for DOCX)
    docx = rtf_file.with_suffix(".docx")
    with word_app() as word:
        doc = word.Documents.Open(str(rtf_file), ReadOnly=True)
        doc.SaveAs2(str(docx), FileFormat=16)
        doc.Close(SaveChanges=0)

    assert "Hello from Word" in pdf_text(convert(docx, "pdf"))


@needs_word
def test_word_is_closed_afterwards(rtf_file):
    before = word_processes()
    convert(rtf_file, "pdf")
    for _ in range(20):               # Word takes a few seconds to shut down
        if word_processes() <= before:
            break
        time.sleep(0.5)
    assert word_processes() <= before


@needs_word
def test_broken_word_file_gives_a_clear_error(tmp_path):
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"this is not really a Word file")
    with pytest.raises(ConversionError) as info:
        convert(bad, "pdf")

    # Word's wording varies ("...appears to be corrupted.", "...error trying to open..."),
    # so check it's one readable line, not the raw COM error tuple
    message = str(info.value)
    assert message.startswith("broken.docx: ")
    assert "Exception occurred" not in message
    assert "\n" not in message


# ---- PDF back to text and Word -------------------------------------------------

@pytest.fixture
def text_pdf(tmp_path):
    """A PDF of more than one page with real text in it, made by the Text to PDF converter."""
    src = tmp_path / "notes.txt"
    src.write_text("First page starts here\n" + "filler line\n" * 120 + "Last line of the notes",
                   encoding="utf-8")
    return convert(src, "pdf")


def test_pdf_offers_txt():
    assert "txt" in targets_for("report.pdf")


def test_pdf_to_txt_keeps_the_text(text_pdf):
    text = convert(text_pdf, "txt").read_text(encoding="utf-8")
    assert "First page starts here" in text
    assert "Last line of the notes" in text


def test_pdf_to_txt_separates_pages(text_pdf):
    assert len(PdfReader(text_pdf).pages) > 1
    text = convert(text_pdf, "txt").read_text(encoding="utf-8")
    assert "\n\n" in text            # the blank line between pages


def test_scanned_pdf_has_no_text(tmp_path):
    src = tmp_path / "scan.png"
    Image.new("RGB", (200, 100), "white").save(src)
    pdf = convert(src, "pdf")        # an image-only PDF, like a scanner makes

    with pytest.raises(ConversionError, match="no selectable text"):
        convert(pdf, "txt")
    assert not (tmp_path / "scan.txt").exists()


@needs_word
def test_pdf_offers_docx():
    assert "docx" in targets_for("report.pdf")


@needs_word
def test_word_pdf_to_docx(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("Buy milk\nCall Grace", encoding="utf-8")
    docx = convert(convert(src, "pdf"), "docx")

    # a .docx is a zip file; the text lives in word/document.xml between XML tags
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "", xml)
    assert "Buy milk" in text
    assert "Call Grace" in text


# ---- LibreOffice fallback ------------------------------------------------------
# LibreOffice usually isn't installed, so most tests use a fake that records the
# command it was given and writes a pretend PDF where the real one would.

needs_libreoffice = pytest.mark.skipif(
    documents.find_libreoffice() is None, reason="needs LibreOffice"
)


@pytest.fixture
def fake_libreoffice(monkeypatch):
    """Pretend LibreOffice is installed; returns the list of commands it was given."""
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        outdir = Path(command[command.index("--outdir") + 1])
        src = Path(command[-1])
        (outdir / f"{src.stem}.pdf").write_bytes(b"%PDF-1.4 pretend")
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(documents, "find_libreoffice", lambda: Path(r"C:\LibreOffice\soffice.exe"))
    monkeypatch.setattr(documents.subprocess, "run", fake_run)
    return commands


def test_word_is_tried_before_libreoffice():
    names = [c.name for c in registry._converters]
    assert names.index("Word to PDF") < names.index("LibreOffice to PDF")


def test_converters_that_start_an_app_say_so():
    apps = {c.name: c.app for c in registry._converters}
    assert apps["Word to PDF"] == "Word"
    assert apps["PDF to Word"] == "Word"
    assert apps["LibreOffice to PDF"] == "LibreOffice"
    assert apps["Text to PDF"] == ""


def test_libreoffice_runs_a_headless_conversion(fake_libreoffice, rtf_file, tmp_path):
    dst = tmp_path / "out.pdf"
    documents.libreoffice_to_pdf(rtf_file, dst)

    command = fake_libreoffice[0]
    assert "--headless" in command
    assert command[command.index("--convert-to") + 1] == "pdf"
    assert command[-1] == str(rtf_file.resolve())
    assert dst.read_bytes().startswith(b"%PDF")


def test_libreoffice_output_gets_our_file_name(fake_libreoffice, rtf_file, tmp_path):
    dst = tmp_path / "letter (1).pdf"
    documents.libreoffice_to_pdf(rtf_file, dst)
    assert dst.exists()
    assert not (tmp_path / "letter.pdf").exists()   # LibreOffice's own name was replaced


def test_libreoffice_is_used_when_word_is_missing(monkeypatch, fake_libreoffice, rtf_file):
    # a copy of the registry where "Word to PDF" says it's unavailable
    no_word = [
        dataclasses.replace(c, is_available=lambda: False) if c.name == "Word to PDF" else c
        for c in registry._converters
    ]
    monkeypatch.setattr(registry, "_converters", no_word)

    dst = convert(rtf_file, "pdf")
    assert dst.exists()
    assert len(fake_libreoffice) == 1                # LibreOffice did the work


def test_libreoffice_failure_gives_a_clear_error(monkeypatch, rtf_file, tmp_path):
    def failing_run(command, **kwargs):
        return subprocess.CompletedProcess(command, returncode=1, stdout="", stderr="Error")

    monkeypatch.setattr(documents, "find_libreoffice", lambda: Path(r"C:\LibreOffice\soffice.exe"))
    monkeypatch.setattr(documents.subprocess, "run", failing_run)
    with pytest.raises(ConversionError, match="LibreOffice couldn't convert"):
        documents.libreoffice_to_pdf(rtf_file, tmp_path / "out.pdf")


def test_libreoffice_that_hangs_is_stopped(monkeypatch, rtf_file, tmp_path):
    def hanging_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(documents, "find_libreoffice", lambda: Path(r"C:\LibreOffice\soffice.exe"))
    monkeypatch.setattr(documents.subprocess, "run", hanging_run)
    with pytest.raises(ConversionError, match="took too long"):
        documents.libreoffice_to_pdf(rtf_file, tmp_path / "out.pdf")


@needs_libreoffice
def test_real_libreoffice_rtf_to_pdf(rtf_file, tmp_path):
    dst = tmp_path / "out.pdf"
    documents.libreoffice_to_pdf(rtf_file, dst)
    assert "Hello from Word" in pdf_text(dst)