"""`python -m file_converter` opens the window; with arguments, it runs the command-line tool."""

import sys

from .cli import main as cli_main
from .gui import main as gui_main


def main() -> int:
    # e.g. python -m file_converter photo.png --to jpg
    if len(sys.argv) > 1:
        return cli_main()
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
