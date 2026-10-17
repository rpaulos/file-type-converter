"""Image conversions using Pillow"""

from pathlib import Path

from PIL import Image

from ..registry import normalize_ext, register


IMAGE_INPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico"]
IMAGE_OUTPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico", "pdf"]

# Formats that can't store transparency; transparent areas get a white background.
NO_ALPHA = {"jpg", "bmp", "pdf"}


def flatten(img: Image.Image) -> Image.Image:
    """Paste an image onto a white background, dropping transparency."""
    rgba = img.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


@register("Image", inputs=IMAGE_INPUTS, outputs=IMAGE_OUTPUTS)
def convert_image(src: Path, dst: Path) -> None:
    target = normalize_ext(dst.suffix)
    with Image.open(src) as img:
        if target in NO_ALPHA:
            img = flatten(img)
        img.save(dst)