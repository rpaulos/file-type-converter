"""Starts the app. PyInstaller builds FileTypeConverter.exe from this file."""

import sys

from file_converter.gui import main

sys.exit(main())