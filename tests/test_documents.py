import pytest
from pypdf import PdfReader

import file_converter.converters  # noqa: F401  (registers the document converters)
from file_converter.registry import convert, targets_for


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