"""Command-line interface: fconvert photo.png --to jpg"""

import argparse
import sys
import glob
import os

from . import converters  # noqa: F401  (registers every converter)
from .registry import ConversionError, convert, supported_inputs, targets_for

def expand(pattern: str) -> list[str]:
    """Turn a wildcard like "*.png" into matching file names; PowerShell doesn't do it for us."""
    # a real file whose name happens to contain [ or ] is used as-is
    if os.path.exists(pattern) or not any(ch in pattern for ch in "*?["):
        return [pattern]
    return sorted(glob.glob(pattern))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fconvert", description="Convert files between formats.")
    parser.add_argument("files", nargs="*", help="files to convert (wildcards like *.png work)")
    parser.add_argument("-t", "--to", help="format to convert to, e.g. jpg, pdf, xlsx")
    parser.add_argument("-o", "--out-dir", help="folder for the converted files (default: next to each original)")
    parser.add_argument("--formats", action="store_true", help="list what can be converted to what")
    args = parser.parse_args(argv)

    if args.formats:
        for ext in supported_inputs():
            print(f"{ext:>5} -> {', '.join(targets_for(ext))}")
        return 0

    if not args.files or not args.to:
        parser.error("give one or more files and --to FORMAT (or use --formats)")

    failures = 0
    for path in args.files:
        try:
            dst = convert(path, args.to, args.out_dir)
            print(f"OK   {path} -> {dst}")
        except ConversionError as exc:
            failures += 1
            print(f"FAIL {exc}", file=sys.stderr)

    failures = 0
    for pattern in args.files:
        paths = expand(pattern)
        if not paths:
            failures += 1
            print(f"FAIL No files match {pattern}", file=sys.stderr)
        for path in paths:
            try:
                dst = convert(path, args.to, args.out_dir)
                print(f"OK   {path} -> {dst}")
            except ConversionError as exc:
                failures += 1
                print(f"FAIL {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())