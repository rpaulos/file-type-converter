# File Type Converter — Development Plan

A local Windows desktop app (not web-based) that converts files from one type to another.
Version 1 handles **images**, **data files**, and **documents ↔ PDF**.

---

## Scope for v1

| Category | Input formats | Output formats |
|---|---|---|
| Images | PNG, JPG/JPEG, BMP, GIF, TIFF, WEBP, ICO | PNG, JPG, BMP, GIF, TIFF, WEBP, ICO, **PDF** |
| Data | CSV, TSV, XLSX, JSON | CSV, TSV, XLSX, JSON |
| Documents → PDF | DOCX, DOC, RTF, ODT, TXT, MD, HTML | PDF |
| PDF → documents | PDF | DOCX, TXT (stretch: PNG/JPG, one image per page) |

Each category converts within itself. Images can also become PDF, and PDF can become documents
(and optionally images).

**Out of scope for v1** (see [Future ideas](#future-ideas)): audio/video, HEIC photos, multi-sheet
Excel, OCR for scanned PDFs, merging/splitting PDFs.

---

## Tech stack

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Already installed; readable; great libraries |
| Desktop UI | PySide6 (Qt) | Native look, built-in drag-and-drop, threads keep the UI responsive |
| Images | Pillow | Reads/writes all v1 image formats, can save PDF |
| Data | pandas + openpyxl | One table model for CSV/TSV/XLSX/JSON; flattens nested JSON |
| Office docs ↔ PDF | Microsoft Word via COM (`pywin32`) | Best layout fidelity; Word is installed on this PC. Also opens PDFs and saves them as DOCX |
| Office docs → PDF (fallback) | LibreOffice, headless (optional) | For users of your app who don't have Word |
| TXT / MD / HTML → PDF | Qt (`QTextDocument` + `QPdfWriter`) | Already part of PySide6, so no new dependency |
| PDF → TXT | pypdf | Pure Python text extraction |
| PDF → images (stretch) | pypdfium2 | Renders PDF pages using Chrome's PDF engine |
| Tests | pytest | Simple, the Python standard |
| CI | GitHub Actions | Runs tests on every push |
| Packaging | PyInstaller | Ships a `.exe` people can run without Python |

---

## Architecture

The key idea is a **converter registry**. Every converter declares the formats it can read and
write. The GUI and CLI only ask the registry two questions:

1. *"What can this file become?"* → `targets_for(path)`
2. *"Convert it."* → `convert(src, target_ext, out_dir)`

Adding a new format later = writing one new converter module. The UI never changes.

Some converters depend on software that may not be installed (Word, LibreOffice). Each converter
therefore has an `is_available()` check, and the registry only offers formats whose converter is
available on the current machine.

> **Licensing note:** every library above has a permissive license (MIT/BSD/Apache), so the project
> can stay MIT. A popular alternative for PDF → DOCX, `pdf2docx`, depends on **PyMuPDF**, which is
> **AGPL-3.0**. Bundling it into your `.exe` would mean licensing the whole app under AGPL. That's
> why this plan uses Word for PDF → DOCX instead.

```
File Type Converter/
├── pyproject.toml           # project metadata + dependencies
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── file_converter/
│       ├── __init__.py      # version number
│       ├── __main__.py      # `python -m file_converter`
│       ├── registry.py      # register(), targets_for(), convert(), output naming
│       ├── cli.py           # command-line front end
│       ├── gui.py           # PySide6 window
│       └── converters/
│           ├── __init__.py
│           ├── images.py    # Pillow
│           ├── data.py      # pandas
│           └── documents.py # Word / LibreOffice / Qt / pypdf
├── tests/
│   ├── test_registry.py
│   ├── test_images.py
│   ├── test_data.py
│   ├── test_documents.py
│   └── test_cli.py
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Milestones

Each milestone ends with something that works and a commit. Tick the boxes as you go.

### Milestone 1 — Project setup & GitHub

**Goal:** an empty-but-real Python project, under version control, pushed to GitHub.

- [x] Set your git identity (one time, not set yet on this machine)
  ```bash
  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"
  ```
- [x] Create and activate a virtual environment
  ```bash
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- [x] Write `pyproject.toml` (name, version `0.1.0`, `requires-python = ">=3.10"`, dependencies:
      `PySide6`, `Pillow`, `pandas`, `openpyxl`, `pypdf`, `pywin32`; dev extra: `pytest`).
      Use the `src/` layout. You can also add dependencies later, as each milestone needs them.
- [x] Create `src/file_converter/__init__.py` with `__version__ = "0.1.0"`
- [x] Install in editable mode: `pip install -e ".[dev]"`
- [x] Add `.gitignore` (`.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `build/`, `dist/`)
- [x] Add a short `README.md` and a `LICENSE` (MIT is a common default)
- [x] `git init`, first commit
- [x] Create the GitHub repo (pick public or private) and push — either:
  - **Website:** create an empty repo on github.com, then
    `git remote add origin <url>` and `git push -u origin main`, or
  - **GitHub CLI:** `winget install GitHub.cli`, `gh auth login`, then
    `gh repo create file-type-converter --source . --push --private`

**Done when:** `python -c "import file_converter; print(file_converter.__version__)"` prints `0.1.0`
and the repo is visible on GitHub.

**Concepts:** virtual environments, `pyproject.toml`, editable installs, git remotes.

---

### Milestone 2 — The converter registry

**Goal:** the core that everything else plugs into, with no real converters yet.

- [X] `normalize_ext(ext)` — lowercase, strip the dot, map aliases (`jpeg`→`jpg`, `tif`→`tiff`)
- [X] A `Converter` dataclass: `name`, `inputs`, `outputs`, `func`, and an optional
      `is_available` check (defaults to always available)
- [X] A `register(name, inputs, outputs)` **decorator** that adds a converter to a module-level list
- [X] `ConversionError` exception — the only error type the UI has to handle
- [X] `targets_for(path)` — every output format reachable from this file's extension (minus its own),
      skipping converters that aren't available on this machine
- [X] `common_targets(paths)` — formats that *all* selected files can become (for batch conversion)
- [X] `output_path(src, ext, out_dir)` — never overwrite: `photo.jpg` → `photo (1).jpg` → `photo (2).jpg`
- [X] `convert(src, target_ext, out_dir=None)` — find a matching converter, run it, return the new path;
      wrap library errors in `ConversionError` and delete half-written output files
- [X] Tests in `tests/test_registry.py` using a fake converter registered just for the test

**Done when:** tests pass for alias handling, no-overwrite naming, and "can't convert X to Y" errors.

**Concepts:** decorators, dataclasses, `pathlib.Path`, custom exceptions, pytest `tmp_path`.

---

### Milestone 3 — Image converter

**Goal:** convert between every image format in the scope table.

- [X] Basic version: `Image.open(src)` → `img.save(dst, format=...)`
- [X] **Transparency:** JPG, BMP and PDF can't store alpha — paste onto a white background first
      (otherwise transparent areas turn black)
- [X] **Phone photos:** apply `ImageOps.exif_transpose` so rotated photos stay upright
- [X] **JPG/WEBP quality:** pick sensible defaults (e.g. 92 / 90)
- [X] **ICO:** save multiple icon sizes (16–256 px, not larger than the source)
- [X] **GIF:** v1 converts the first frame only — note this in the README
- [X] Register it with the registry
- [X] Tests: create a small RGBA PNG in `tmp_path`, convert to each target, check the file opens;
      check JPG output is white (not black) where the PNG was transparent
- [X] Extra: square, padded icons (and a minimum of 16 px); CMYK JPGs convert instead of crashing

**Done when:** a transparent PNG converts cleanly to every target format and all tests pass.

**Concepts:** image modes (RGB, RGBA, P, L), alpha compositing, EXIF.

---

### Milestone 4 — Data converter

**Goal:** convert between CSV, TSV, XLSX and JSON.

- [X] `read_table(path)` → pandas `DataFrame` (CSV, TSV with `sep="\t"`, XLSX first sheet, JSON)
- [X] `write_table(df, path)` — always `index=False`; JSON as a list of records with `indent=2`
- [X] **JSON shapes to handle:**
  - list of objects → one row per object
  - nested objects → flattened columns like `owner.name` (`pd.json_normalize`)
  - `{"col": [...], "col2": [...]}` → columns
  - a single object → one row
  - anything else (e.g. just a number) → `ConversionError` with a clear message
- [X] Register it with the registry
- [X] Tests: **round trips** — CSV → XLSX → CSV gives back identical rows; same for TSV and JSON;
      nested JSON flattens correctly; bad JSON fails without leaving a file behind
- [X] Extra: CSVs from older Excel (cp1252) can be read; CSV output opens in Excel with accents intact;
      Excel dates become readable ISO dates in JSON

**Done when:** all round-trip tests pass.

**Concepts:** DataFrames, JSON structure, round-trip testing.

---

### Milestone 5 — Document converter (documents ↔ PDF)

**Goal:** turn documents into PDFs and PDFs back into editable documents. This is the hardest
converter, so build it in four small steps.

**5a. Plain text, Markdown, HTML → PDF (Qt, no extra software)**
- [X] Load the file into a `QTextDocument`: `setPlainText` for TXT, `setMarkdown` for MD, `setHtml` for HTML
- [X] Print it to a `QPdfWriter` (A4 page size, sensible margins)
- [X] Read text files as UTF-8, and fall back to another encoding if that fails
- [X] Tests: convert a small `.md` file and check the PDF exists and contains its text (read it back with pypdf)

**5b. Word documents → PDF (Microsoft Word through COM)**
- [X] `pip install pywin32`
- [X] Start Word invisibly: `win32com.client.DispatchEx("Word.Application")`, set `Visible = False`
      and `DisplayAlerts = 0` so no pop-ups appear
- [X] `Documents.Open(src, ReadOnly=True)`, then `doc.SaveAs2(dst, FileFormat=17)` (17 = PDF)
- [X] **Always** close the document and `Quit()` Word in a `finally:` block. Otherwise hidden
      `WINWORD.EXE` processes pile up in Task Manager
- [X] Use **absolute** file paths, because Word doesn't understand paths relative to your script
- [X] `is_available()`: check that `Word.Application` can be created (cache the result)
- [X] Supports DOCX, DOC, RTF and ODT, since Word opens all four
- [X] Tests: mark them to **skip** when Word isn't installed, because GitHub's CI machines don't have it:
      `@pytest.mark.skipif(not word_available(), reason="needs Microsoft Word")`

**5c. PDF → DOCX and PDF → TXT**
- [X] **PDF → DOCX via Word:** `Documents.Open(pdf, ConfirmConversions=False)` makes Word turn the PDF
      into an editable document, then `SaveAs2(dst, FileFormat=16)` (16 = DOCX)
- [X] Note in the README that results depend on the PDF: simple text PDFs come out well, complex
      layouts less so, and **scanned PDFs (photos of pages) have no text to extract** without OCR
- [X] **PDF → TXT via pypdf:** read every page with `page.extract_text()`, separate pages with a blank line
- [X] Tests: make a PDF in 5a, then convert it back to TXT and check the text survived

**5d. Fallback and stretch goals**
- [X] **LibreOffice fallback** for DOCX/DOC/RTF/ODT → PDF when Word is missing:
      `soffice --headless --convert-to pdf --outdir <folder> <file>` with `subprocess.run`
      (search the usual install folders for `soffice.exe`)
- [ ] **Stretch: PDF → PNG/JPG**, one image per page, with pypdfium2. This creates *several* output
      files, so `convert()` needs to return a **list** of paths (e.g. `report-page1.png`, `report-page2.png`)
      *(not done yet: changing what `convert()` returns affects the GUI, so decide this before Milestone 7)*
- [X] Register the document converters with the registry

**Done when:** a DOCX turns into a PDF that looks the same as in Word, that PDF turns back into an
editable DOCX, and no stray `WINWORD.EXE` stays running afterwards.

**Concepts:** COM automation, cleaning up external processes, `subprocess`, skipping tests
conditionally, file encodings.

---

### Milestone 6 — Command-line interface

**Goal:** a quick way to use the converters before the GUI exists.

- [X] `cli.py` with `argparse`:
  ```
  fconvert photo.png --to jpg
  fconvert *.csv --to xlsx --out-dir converted
  fconvert --formats          # list what converts to what
  ```
- [X] Print `OK`/`FAIL` per file; exit code `1` if anything failed
- [X] Add a `[project.scripts]` entry so `fconvert` works after `pip install -e .`
- [X] Tests for success, failure, and `--formats`

**Done when:** you can convert real files from the terminal.

**Concepts:** `argparse`, exit codes, console entry points.

---

### Milestone 7 — Desktop GUI

**Goal:** the actual app window.

- [X] Basic `QMainWindow` that opens and closes (`gui.py`, `main()` function)
- [X] File list (`QListWidget`) + **Add files…** button (`QFileDialog`, filtered to supported types)
- [X] **Drag and drop** files onto the window
- [X] **Remove selected** and **Clear** buttons
- [X] Unsupported files are skipped with a friendly message
- [X] **"Convert to"** dropdown filled from `common_targets()` — refreshes whenever the list changes
- [X] **Output location:** "save next to originals" checkbox, or pick a folder
- [X] **Convert** button + progress bar
- [X] Run conversions in a **`QThread` worker** so the window doesn't freeze on big files;
      send progress back with **signals**
- [X] Word needs COM set up in every thread that uses it: call `pythoncom.CoInitialize()` at the
      start of the worker and `pythoncom.CoUninitialize()` at the end
- [X] Word is slow to start (a few seconds), so show "Starting Word…" in the status bar
- [X] Mark each file ✔ / ✖ in the list; show a summary in the status bar
- [X] **Open output folder** button after a successful run
- [X] `[project.gui-scripts]` entry so `file-converter` launches the window
- [X] `python -m file_converter` opens the GUI (with arguments → runs the CLI)

**Done when:** you can drag in a mix of PNGs, pick JPG, convert, and open the results, and do the
same for a few DOCX files to PDF, without the window ever freezing.

**Concepts:** Qt widgets and layouts, signals & slots, threads, drag-and-drop events.

---

### Milestone 8 — Continuous integration

**Goal:** GitHub runs your tests automatically.

- [X] `.github/workflows/ci.yml`: on push to `main` and on pull requests, `windows-latest`,
      Python 3.10 and 3.12, `pip install -e ".[dev]"`, `pytest`
- [X] Word tests will show as *skipped* in CI. That's expected, so run them locally before you push
- [X] Add a CI status badge to the README
- [X] From now on, consider working on branches + pull requests so CI checks each change

**Done when:** the Actions tab on GitHub shows a green check.

**Concepts:** GitHub Actions, build matrices, branches & PRs.

---

### Milestone 9 — Packaging & release

**Goal:** a downloadable `.exe` for people without Python.

- [X] `pip install pyinstaller`
- [X] Build: `pyinstaller --noconsole --onefile --name FileTypeConverter <entry script>`
      (PyInstaller needs a plain script entry point, not the `-m` package form)
- [X] Test the `.exe` on your machine, ideally also on a PC without Python
- [X] Check that `pywin32` got bundled: DOCX → PDF must still work from the `.exe`
- [X] README: explain that DOCX/DOC/RTF/ODT conversions need **Microsoft Word or LibreOffice**
      installed. Everything else works without them
- [X] Add an app icon (you can make one with your own converter's ICO output!)
- [ ] Tag the version (`git tag v0.1.0`, `git push --tags`) and create a **GitHub Release** with the `.exe` attached
- [ ] Optional: a second workflow that builds and attaches the `.exe` automatically when you push a tag

**Done when:** someone can download the `.exe` from your GitHub Releases page and convert a file.

**Concepts:** freezing Python apps, semantic versioning, GitHub Releases.

---

## Future ideas

- **HEIC/HEIF** iPhone photos (`pillow-heif`)
- **Options panel:** resize, JPG quality slider, strip metadata
- **Excel with multiple sheets** → one CSV per sheet
- **Audio/video** via ffmpeg (MP4, MOV, MP3, WAV, GIF from video)
- **PDF tools:** merge several PDFs, split pages, combine many images into one PDF
- **OCR** for scanned PDFs (Tesseract) so they convert to real text
- **More documents:** DOCX ↔ ODT ↔ RTF via Word's `SaveAs2`; PPTX/XLSX → PDF via PowerPoint/Excel COM;
  Markdown ↔ HTML ↔ DOCX (pandoc)
- **Windows right-click menu** "Convert with File Type Converter"
- Remember last-used format and output folder between sessions
- Dark mode
