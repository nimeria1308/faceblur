# Copyright (C) 2025, Simona Dimitrova

from PIL.Image import Image
from PIL.ImageDraw import Draw

COLOR_CLOSE = "yellow"
COLOR_FAR = "red"
COLOR_MERGED = "green"
COLOR_INTERPOLATED = "blue"


def debug_faces(image: Image, faces, strength=1.0):
    draw = Draw(image)

    # Rectangles are (top-left, bottom_right)
    for face in faces.interpolated:
        draw.rectangle([(face.left, face.top), (face.right, face.bottom)],
                       fill=None, outline=COLOR_INTERPOLATED, width=12)

    for face in faces.merged:
        draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline=COLOR_MERGED, width=6)

    for face in faces.close:
        draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline=COLOR_CLOSE, width=3)

    for face in faces.far:
        draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline=COLOR_FAR, width=3)

    return image
