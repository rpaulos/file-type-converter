import pytest
from PIL import Image

from file_converter.cli import main


def make_png(path):
    Image.new("RGB", (20, 20), (200, 50, 50)).save(path)
    return path


def test_converts_a_file(tmp_path, capsys):
    photo = make_png(tmp_path / "photo.png")
    assert main([str(photo), "--to", "jpg"]) == 0
    assert (tmp_path / "photo.jpg").exists()
    assert "OK" in capsys.readouterr().out


def test_converts_several_files(tmp_path):
    a = make_png(tmp_path / "a.png")
    b = make_png(tmp_path / "b.png")
    assert main([str(a), str(b), "--to", "webp"]) == 0
    assert (tmp_path / "a.webp").exists()
    assert (tmp_path / "b.webp").exists()


def test_out_dir(tmp_path):
    photo = make_png(tmp_path / "photo.png")
    out = tmp_path / "converted"
    assert main([str(photo), "--to", "jpg", "--out-dir", str(out)]) == 0
    assert (out / "photo.jpg").exists()


def test_missing_file_fails(tmp_path, capsys):
    assert main([str(tmp_path / "missing.png"), "--to", "jpg"]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_one_failure_does_not_stop_the_rest(tmp_path):
    photo = make_png(tmp_path / "photo.png")
    assert main([str(tmp_path / "missing.png"), str(photo), "--to", "jpg"]) == 1
    assert (tmp_path / "photo.jpg").exists()


def test_lists_formats(capsys):
    assert main(["--formats"]) == 0
    out = capsys.readouterr().out
    assert "png" in out
    assert "csv" in out


def test_needs_a_target_format(tmp_path):
    photo = make_png(tmp_path / "photo.png")
    with pytest.raises(SystemExit) as info:
        main([str(photo)])
    assert info.value.code == 2      # argparse's code for "the command was used wrong"


def test_wildcards_are_expanded(tmp_path):
    make_png(tmp_path / "a.png")
    make_png(tmp_path / "b.png")
    assert main([str(tmp_path / "*.png"), "--to", "bmp"]) == 0
    assert (tmp_path / "a.bmp").exists()
    assert (tmp_path / "b.bmp").exists()


def test_wildcard_that_matches_nothing(tmp_path, capsys):
    assert main([str(tmp_path / "*.png"), "--to", "jpg"]) == 1
    assert "No files match" in capsys.readouterr().err


def test_each_file_is_converted_once(tmp_path):
    photo = make_png(tmp_path / "photo.png")
    assert main([str(photo), "--to", "jpg"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["photo.jpg", "photo.png"]