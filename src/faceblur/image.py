# Copyright (C) 2025, Simona Dimitrova

FORMATS = {
    "BMP": ["bmp"],
    "PNG": ["png"],
    "JPEG": [
        "jfif",
        "jpe",
        "jpg",
        "jpeg",
    ],
    "JPEG2000": [
        "jp2",
        "j2k",
        "jpc",
        "jpf",
        "jpx",
        "j2c",
    ],
    "TIFF": [
        "tif",
        "tiff",
    ],
    "WEBP": ["webp"],
    "HEIF": [  # pillow-heif
        "heic",
        "heics",
        "heif",
        "heifs",
        "hif",
    ],
    "TGA": ["tga"],
    "PPM": [
        "pbm",
        "pgm",
        "ppm",
        "pnm",
        "pfm",
    ],
}

EXTENSIONS = sorted(list(set([ext for format in FORMATS.values() for ext in format])))
