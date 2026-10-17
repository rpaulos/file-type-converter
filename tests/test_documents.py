import subprocess
import time

import pytest
from pypdf import PdfReader

import file_converter.converters  # noqa: F401  (registers the document converters)
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