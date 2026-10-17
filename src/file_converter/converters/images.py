"""Image conversions using Pillow"""

from pathlib import Path

from PIL import Image

from ..registry import register

IMAGE_INPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico"]
IMAGE_OUTPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico", "pdf"]


@register("Image", inputs=IMAGE_INPUTS, outputs=IMAGE_OUTPUTS)
def convert_image(src: Path, dst: Path) -> None:
    with Image.open(src) as img:
        img.save(dst)