# Copyright (C) 2025, Simona Dimitrova

from PIL import Image, ImageOps

FORMATS = {
    "bmp": ["bmp"],
    "png": ["png"],
    "jpeg": [
        "jpg",
        "jpe",
        "jpeg",
        "jfif",
    ],
    "jpeg2000": [
        "jp2",
        "j2k",
        "jpc",
        "jpf",
        "jpx",
        "j2c",
    ],
    "tiff": [
        "tif",
        "tiff",
    ],
    "webp": ["webp"],
    "heif": [  # pillow-heif
        "heic",
        "heics",
        "heif",
        "heifs",
        "hif",
    ],
    "tga": ["tga"],
    "ppm": [
        "ppm",
        "pbm",
        "pgm",
        "pnm",
        "pfm",
    ],
}

EXTENSIONS = sorted(list(set([ext for format in FORMATS.values() for ext in format])))


def image_open(filename):
    image = Image.open(filename)

    # mediapipe's models support RGB only, which will fail for RGBA PNGs.
    # Saving to JPG supports RGB only.
    # Therefore to be safe, just convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Automatically rotate / transpose, etc. to straighten it up
    image = ImageOps.exif_transpose(image)

    return image
