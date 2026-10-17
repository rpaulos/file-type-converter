"""Central registry of converters."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ALIASES = {"jpeg": "jpg", "tif": "tiff"}


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

_converters: list["Converter"] = []

def register(
    name: str,
    inputs: list[str],
    outputs: list[str],
    is_available: Callable[[], bool] = always_available,
):
    
    def decorator(func):
        converter = Converter(
            name=name,
            inputs=frozenset(normalize_ext(e) for e in inputs),
            outputs=frozenset(normalize_ext(e) for e in outputs),
            func=func,
            is_available=is_available,
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
    """Output formats that every one of the given files can be converted to."""

    sets = [set(targets_for(p)) for p in paths]
    if not sets:
        return []

    # keep only the formats that appear in every file's set
    return sorted(set.intersection(*sets))


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


def convert(src, target_ext: str, out_dir=None) -> Path:
    """Convert src to target_ext and return the new file's path."""

    src = Path(src)

    if not src.is_file():
        raise ConversionError(f"File not found: {src}")
    
    in_ext = normalize_ext(src.suffix)
    target = normalize_ext(target_ext)

    if in_ext == target:
        raise ConversionError(f"{src.name} is already a .{target} file")

    # find a converter that reads this format, writes the target, and can run here
    for c in _converters:
        if in_ext in c.inputs and target in c.outputs and c.is_available():
            dst = output_path(src, target, out_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)

            try:
                c.func(src, dst)
            except ConversionError:
                raise
            except Exception as exc:
                dst.unlink(missing_ok=True)
                raise ConversionError(f"{src.name}: {exc}") from exc
            return dst

    # the loop finished without finding one
    raise ConversionError(f"Can't convert .{in_ext} to .{target}")