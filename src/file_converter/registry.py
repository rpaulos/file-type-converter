"""Central registry of converters."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ALIASES = {"jpeg": "jpg", "tif": "tiff", "htm": "html", "markdown": "md"}


def normalize_ext(ext: str) -> str:
    """'.JPG' -> 'jpg', 'jpeg' -> 'jpg', 'tif' -> 'tiff'."""

    # normalize to lowercase
    ext = ext.lower()

    # remove leading dot if present
    if ext.startswith("."):
        ext = ext[1:]

    # swap aliases
    return ALIASES.get(ext, ext)

class ConversionError(Exception):
    """Raised when a file cannot be converted."""

def always_available() -> bool:
    """Default availability check: the converter needs no extra software."""
    return True


@dataclass(frozen=True)
class Converter:
    """One way of converting files: which formats it reads, writes, and how"""

    name: str
    inputs: frozenset[str]
    outputs: frozenset[str]
    func: Callable[[Path, Path], None]
    is_available: Callable[[], bool] = always_available
    app: str = ""   # an outside program it starts, like "Word" (slow to open); "" for none

_converters: list["Converter"] = []

def register(
    name: str,
    inputs: list[str],
    outputs: list[str],
    is_available: Callable[[], bool] = always_available,
    app: str = "",
):

    def decorator(func):
        converter = Converter(
            name=name,
            inputs=frozenset(normalize_ext(e) for e in inputs),
            outputs=frozenset(normalize_ext(e) for e in outputs),
            func=func,
            is_available=is_available,
            app=app,
        )
        _converters.append(converter)
        return func
    return decorator


def targets_for(path) -> list[str]:
    """Output formats available for a file (or a bare extension like 'png')."""

    # get the extension; fall back to the whole string for "png" or ".png"
    ext = normalize_ext(Path(path).suffix or str(path))

    # collect outputs from every available converter that reads this format
    targets = set()
    for c in _converters:
        if ext in c.inputs and c.is_available():
            targets.update(c.outputs)

    # png -> png isn't a conversion
    targets.discard(ext)
    return sorted(targets)


def common_targets(paths) -> list[str]:
    """Output formats that every one of the given files can be converted to, or already is.

    A file that's already in the chosen format is simply left alone, so a PNG and a JPG
    can both "become" PNG. A format that every file already has isn't offered, though:
    there'd be nothing to convert.
    """

    paths = list(paths)   # it's gone through twice below
    own = [normalize_ext(Path(p).suffix) for p in paths]
    if not own:
        return []

    # each file's options: what it can become, plus what it already is
    sets = [set(targets_for(p)) | {ext} for p, ext in zip(paths, own)]

    # keep only the formats that appear in every file's set
    common = set.intersection(*sets)

    # every file is already this format: nothing to do
    if len(set(own)) == 1:
        common.discard(own[0])
    return sorted(common)


def output_path(src, target_ext: str, out_dir=None) -> Path:
    src = Path(src)

    if out_dir is None:
        out_dir = src.parent
    else:
        out_dir = Path(out_dir)

    ext = normalize_ext(target_ext)
    dst = out_dir / src.with_suffix(f".{ext}").name

    n = 0
    while dst.exists():
        n += 1
        dst = out_dir / f"{src.stem} ({n}).{ext}"

    return dst


def find_converter(src, target_ext: str) -> Converter | None:
    """The converter that would turn src into target_ext, or None if there isn't one."""

    in_ext = normalize_ext(Path(src).suffix)
    target = normalize_ext(target_ext)

    # the first one that reads this format, writes the target, and can run here
    for c in _converters:
        if in_ext in c.inputs and target in c.outputs and c.is_available():
            return c
    return None


def convert(src, target_ext: str, out_dir=None) -> Path:
    """Convert src to target_ext and return the new file's path."""

    src = Path(src)

    if not src.is_file():
        raise ConversionError(f"File not found: {src}")

    in_ext = normalize_ext(src.suffix)
    target = normalize_ext(target_ext)

    if in_ext == target:
        raise ConversionError(f"{src.name} is already a .{target} file")

    converter = find_converter(src, target)
    if converter is None:
        raise ConversionError(f"Can't convert .{in_ext} to .{target}")

    dst = output_path(src, target, out_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        converter.func(src, dst)
    except ConversionError:
        raise
    except Exception as exc:
        dst.unlink(missing_ok=True)
        raise ConversionError(f"{src.name}: {exc}") from exc
    return dst


def supported_inputs() -> list[str]:
    """Every format that at least one available converter can read."""
    formats = set()
    for c in _converters:
        if c.is_available():
            formats.update(c.inputs)
    return sorted(formats)