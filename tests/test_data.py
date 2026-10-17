import json

import pandas as pd
import pytest

import file_converter.converters  # noqa: F401  (registers the data converter)
from file_converter.registry import ConversionError, convert, targets_for

ROWS = [
    {"name": "Ada", "age": 36, "city": "London"},
    {"name": "Grace", "age": 85, "city": "New York"},
]


@pytest.fixture
def people_csv(tmp_path):
    """A small CSV file with two rows."""
    src = tmp_path / "people.csv"
    pd.DataFrame(ROWS).to_csv(src, index=False)
    return src


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_csv_offers_every_data_format():
    assert targets_for("people.csv") == ["json", "tsv", "xlsx"]


def test_data_cannot_become_an_image(people_csv):
    assert "png" not in targets_for(people_csv)


@pytest.mark.parametrize("middle", ["tsv", "xlsx", "json"])
def test_round_trip_keeps_every_row(people_csv, middle):
    there = convert(people_csv, middle)
    back = convert(there, "csv")
    assert pd.read_csv(back).to_dict("records") == ROWS


def test_csv_to_json_is_a_list_of_records(people_csv):
    dst = convert(people_csv, "json")
    assert json.loads(dst.read_text(encoding="utf-8")) == ROWS


def test_csv_to_xlsx_opens_in_excel_format(people_csv):
    dst = convert(people_csv, "xlsx")
    df = pd.read_excel(dst)
    assert list(df.columns) == ["name", "age", "city"]
    assert len(df) == 2


def test_nested_json_is_flattened(tmp_path):
    src = write_json(tmp_path / "pets.json", [
        {"id": 1, "owner": {"name": "Ada", "city": "London"}},
        {"id": 2, "owner": {"name": "Grace", "city": "New York"}},
    ])
    df = pd.read_csv(convert(src, "csv"))
    assert list(df.columns) == ["id", "owner.name", "owner.city"]
    assert df["owner.name"].tolist() == ["Ada", "Grace"]


def test_json_object_of_columns(tmp_path):
    src = write_json(tmp_path / "cols.json", {"a": [1, 2], "b": [3, 4]})
    df = pd.read_csv(convert(src, "csv"))
    assert df.to_dict("list") == {"a": [1, 2], "b": [3, 4]}


def test_single_json_object_becomes_one_row(tmp_path):
    src = write_json(tmp_path / "one.json", {"name": "Ada", "age": 36})
    df = pd.read_csv(convert(src, "csv"))
    assert df.to_dict("records") == [{"name": "Ada", "age": 36}]


def test_json_that_is_not_a_table_is_rejected(tmp_path):
    src = write_json(tmp_path / "number.json", 42)
    with pytest.raises(ConversionError, match="list or an object"):
        convert(src, "csv")
    assert not (tmp_path / "number.csv").exists()   # no half-written file left behind


def test_broken_json_fails_cleanly(tmp_path):
    src = tmp_path / "broken.json"
    src.write_text('[{"name": "Ada",', encoding="utf-8")
    with pytest.raises(ConversionError):
        convert(src, "xlsx")
    assert not (tmp_path / "broken.xlsx").exists()


def test_accented_letters_survive(tmp_path):
    src = write_json(tmp_path / "cafe.json", [{"name": "Café Zoë", "city": "São Paulo"}])
    back = convert(convert(src, "csv"), "json")
    assert json.loads(back.read_text(encoding="utf-8")) == [{"name": "Café Zoë", "city": "São Paulo"}]


def test_reads_csv_saved_by_old_excel(tmp_path):
    src = tmp_path / "old_excel.csv"
    src.write_bytes("name,city\nJosé,Málaga\n".encode("cp1252"))
    dst = convert(src, "json")
    assert json.loads(dst.read_text(encoding="utf-8")) == [{"name": "José", "city": "Málaga"}]


def test_dates_from_excel_become_readable_text(tmp_path):
    src = tmp_path / "dates.xlsx"
    pd.DataFrame({"day": pd.to_datetime(["2026-10-17"])}).to_excel(src, index=False)
    dst = convert(src, "json")
    assert json.loads(dst.read_text(encoding="utf-8")) == [{"day": "2026-10-17T00:00:00.000"}]
