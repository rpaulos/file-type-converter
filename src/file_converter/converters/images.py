"""Image conversions using Pillow"""

from pathlib import Path

from PIL import Image, ImageOps

from ..registry import normalize_ext, register


IMAGE_INPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico"]
IMAGE_OUTPUTS = ["png", "jpg", "bmp", "gif", "tiff", "webp", "ico", "pdf"]

# Formats that can't store transparency; transparent areas get a white background.
NO_ALPHA = {"jpg", "bmp", "pdf"}

# Extra save settings per format. Pillow's defaults (JPG 75, WEBP 80) look visibly blurry.
SAVE_OPTIONS = {
    "jpg": {"quality": 92, "optimize": True},
    "webp": {"quality": 90},
}

# Windows icons can't be smaller than this.
MIN_ICON_SIZE = 16


def flatten(img: Image.Image) -> Image.Image:
    """Paste an image onto a white background, dropping transparency."""
    rgba = img.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def make_square(img: Image.Image) -> Image.Image:
    """Center an image on a transparent square, so icons aren't squashed."""
    side = max(img.width, img.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img.convert("RGBA"), ((side - img.width) // 2, (side - img.height) // 2))
    if side < MIN_ICON_SIZE:
        canvas = canvas.resize((MIN_ICON_SIZE, MIN_ICON_SIZE))
    return canvas


@register("Image", inputs=IMAGE_INPUTS, outputs=IMAGE_OUTPUTS)
def convert_image(src: Path, dst: Path) -> None:
    target = normalize_ext(dst.suffix)
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)  # respect EXIF orientation

        # print-ready JPGs use CMYK colors, which most formats can't save
        if img.mode == "CMYK":
            img = img.convert("RGB")

        if target in NO_ALPHA:
            img = flatten(img)
        elif target == "ico":
            img = make_square(img)  # Pillow then saves every standard icon size that fits

        img.save(dst, **SAVE_OPTIONS.get(target, {}))