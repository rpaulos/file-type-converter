"""Central registry of converters."""


def normalize_ext(ext: str) -> str:
    """'.JPG' -> 'jpg', 'jpeg' -> 'jpg', 'tif' -> 'tiff'."""

    # normalize to lowercase
    ext = ext.lower()

    # remove leading dot if present
    if ext.startswith("."):
        ext = ext[1:]

    # swap aliases
    ALIASES = {"jpeg": "jpg", "tif": "tiff"}
    return ALIASES.get(ext, ext)
