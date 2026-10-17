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