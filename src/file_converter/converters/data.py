"""Tabular data conversions (CSV, TSV, Excel, JSON) using pandas."""

import json
from pathlib import Path

import pandas as pd

from ..registry import ConversionError, normalize_ext, register

DATA_FORMATS = ["csv", "tsv", "xlsx", "json"]

# "utf-8-sig" also strips the invisible marker Excel puts at the start of UTF-8 files;
# cp1252 is what older Excel versions on Windows use for CSV.
TEXT_ENCODINGS = ["utf-8-sig", "cp1252"]


def read_text_table(path: Path, sep: str) -> pd.DataFrame:
    """Read a CSV/TSV file, trying each encoding until one works."""
    for encoding in TEXT_ENCODINGS:
        try:
            return pd.read_csv(path, sep=sep, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ConversionError(f"{path.name}: can't work out the text encoding")


def read_json_table(path: Path) -> pd.DataFrame:
    """Turn the common JSON shapes into a table."""
    with path.open(encoding="utf-8-sig") as f:
        data = json.load(f)

    # [{"name": "Ada"}, {"name": "Grace"}] -> one row per object;
    # nested objects become "parent.child" columns
    if isinstance(data, list):
        return pd.json_normalize(data)

    if isinstance(data, dict):
        # {"name": ["Ada", "Grace"], "age": [36, 85]} -> one column per key
        if data and all(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)
        # {"name": "Ada", "age": 36} -> a single row
        return pd.json_normalize(data)

    raise ConversionError(f"{path.name}: JSON must be a list or an object to become a table")


def read_table(path: Path) -> pd.DataFrame:
    ext = normalize_ext(path.suffix)
    if ext == "csv":
        return read_text_table(path, sep=",")
    if ext == "tsv":
        return read_text_table(path, sep="\t")
    if ext == "xlsx":
        return pd.read_excel(path)  # first sheet only
    if ext == "json":
        return read_json_table(path)
    raise ConversionError(f"Unsupported data format: .{ext}")


def write_table(df: pd.DataFrame, path: Path) -> None:
    ext = normalize_ext(path.suffix)
    if ext == "csv":
        # with "utf-8-sig", Excel shows accented letters (é, ñ, ü) correctly
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif ext == "tsv":
        df.to_csv(path, sep="\t", index=False, encoding="utf-8-sig")
    elif ext == "xlsx":
        df.to_excel(path, index=False)
    elif ext == "json":
        # "iso" writes dates as "2026-10-17T00:00:00" instead of milliseconds since 1970
        df.to_json(path, orient="records", indent=2, force_ascii=False, date_format="iso")
    else:
        raise ConversionError(f"Unsupported data format: .{ext}")


@register("Data", inputs=DATA_FORMATS, outputs=DATA_FORMATS)
def convert_data(src: Path, dst: Path) -> None:
    write_table(read_table(src), dst)
