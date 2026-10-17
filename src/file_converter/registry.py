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