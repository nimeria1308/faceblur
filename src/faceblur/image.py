# Copyright (C) 2025, Simona Dimitrova

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
