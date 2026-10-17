# File Type Converter

A desktop app that converts images, data files and documents between formats.

## Supported conversions

| Category | From | To |
|---|---|---|
| Images | PNG, JPG, BMP, GIF, TIFF, WEBP, ICO | PNG, JPG, BMP, GIF, TIFF, WEBP, ICO, PDF |
| Data | CSV, TSV, XLSX, JSON | CSV, TSV, XLSX, JSON |
| Documents | TXT, MD, HTML | PDF |
| Documents | DOCX, DOC, RTF, ODT | PDF (needs Microsoft Word) |
| PDF | PDF | TXT, DOCX (DOCX needs Microsoft Word) |

## Good to know

- **Transparency:** JPG, BMP and PDF can't store transparent pixels, so transparent areas become white.
- **Animated GIFs:** only the first frame is converted.
- **Icons (ICO):** non-square pictures are centred on a transparent square, and every standard
  icon size that fits (16 to 256 px) is included.
- **Excel files:** only the first sheet is converted.
- **JSON:** a list of objects becomes one row per object, and nested objects become columns like
  `owner.name`. JSON that isn't a list or an object (for example just a number) can't become a table.
- **PDF → DOCX** is done by Word, which rebuilds the PDF as an editable document. Simple text PDFs
  come out well; complex layouts less so. It can take 20 seconds or more.
- **Scanned PDFs** (photos of pages) contain no text, so they can't become TXT or a useful DOCX.
- **CSV files** are saved so that Excel shows accented letters (é, ñ, ü) correctly. CSVs saved by older
  versions of Excel can be read too.
