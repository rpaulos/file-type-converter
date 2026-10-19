import subprocess
import sys

from file_converter import __main__ as entry


def test_no_arguments_opens_the_window(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["file_converter"])
    monkeypatch.setattr(entry, "gui_main", lambda: "window opened")
    assert entry.main() == "window opened"


def test_arguments_run_the_command_line_tool(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["file_converter", "--formats"])
    monkeypatch.setattr(entry, "cli_main", lambda: "command line ran")
    assert entry.main() == "command line ran"


def test_python_dash_m_really_works():
    result = subprocess.run(
        [sys.executable, "-m", "file_converter", "--formats"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    assert "png" in result.stdout
