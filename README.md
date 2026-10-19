# File Type Converter

[![Tests](https://github.com/rpaulos/file-type-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/rpaulos/file-type-converter/actions/workflows/ci.yml)

A desktop app that converts images, data files and documents between formats.

## Download

Get **FileTypeConverter.exe** from the
[latest release](https://github.com/rpaulos/file-type-converter/releases/latest). No Python needed:
double-click it (it takes a few seconds to open), or drag files onto it to open them straight away.

- Windows may say **"Windows protected your PC"** the first time, because the app isn't signed with a
  paid certificate. Click **More info**, then **Run anyway**.
- Converting **DOCX, DOC, RTF and ODT** files needs **Microsoft Word** or the free
  [LibreOffice](https://www.libreoffice.org/) installed, and **PDF → DOCX** needs Word.
  Everything else works on its own.

## Supported conversions

| Category | From | To |
|---|---|---|
| Images | PNG, JPG, BMP, GIF, TIFF, WEBP, ICO | PNG, JPG, BMP, GIF, TIFF, WEBP, ICO, PDF |
| Data | CSV, TSV, XLSX, JSON | CSV, TSV, XLSX, JSON |
| Documents | TXT, MD, HTML | PDF |
| Documents | DOCX, DOC, RTF, ODT | PDF (needs Microsoft Word or LibreOffice) |
| PDF | PDF | TXT, DOCX (DOCX needs Microsoft Word) |

## Good to know

- **Mixed lists:** the "Convert to" choice applies to every file in the list. Files that are already
  in that format (say, the PNGs when you convert a mix of PNGs and JPGs to PNG) are left as they are.
- **Transparency:** JPG, BMP and PDF can't store transparent pixels, so transparent areas become white.
- **Animated GIFs:** only the first frame is converted.
- **Icons (ICO):** non-square pictures are centred on a transparent square, and every standard
  icon size that fits (16 to 256 px) is included.
- **Excel files:** only the first sheet is converted.
- **JSON:** a list of objects becomes one row per object, and nested objects become columns like
  `owner.name`. JSON that isn't a list or an object (for example just a number) can't become a table.
- **Word documents → PDF** uses Microsoft Word when it's installed. Without Word, the free
  [LibreOffice](https://www.libreoffice.org/) is used instead, if it's installed.
- **PDF → DOCX** is done by Word, which rebuilds the PDF as an editable document. Simple text PDFs
  come out well; complex layouts less so. It can take 20 seconds or more.
- **Scanned PDFs** (photos of pages) contain no text, so they can't become TXT or a useful DOCX.
- **CSV files** are saved so that Excel shows accented letters (é, ñ, ü) correctly. CSVs saved by older
  versions of Excel can be read too.

## Command line

```
fconvert photo.png --to jpg
fconvert *.csv --to xlsx --out-dir converted
fconvert --formats
```

## Running the tests

```
pip install -e ".[dev]"
pytest
```

GitHub runs the tests on every push to `main` and on every pull request (see the badge above).
GitHub's computers don't have Microsoft Word, so the Word tests are skipped there. Run them on
your own PC before you push.

## Building the .exe

```
pip install -e ".[build]"
pyinstaller --noconfirm FileTypeConverter.spec
```

The app ends up in `dist\FileTypeConverter.exe`. `FileTypeConverter.spec` is PyInstaller's recipe:
it starts from `launcher.py` and packs in the icon.

## Releasing a new version

1. Change the version number in `pyproject.toml` and `src/file_converter/__init__.py`.
2. Tag the commit on `main` and push the tag:
   ```
   git tag v0.2.0
   git push origin v0.2.0
   ```

GitHub then runs the tests, builds the .exe and publishes it on the
[Releases page](https://github.com/rpaulos/file-type-converter/releases)
(see `.github/workflows/release.yml`).