# Copyright (C) 2025, Simona Dimitrova

from PIL.Image import Image
from PIL.ImageDraw import Draw


def debug_faces(image: Image, faces, strength=1.0):
    draw = Draw(image)

    # Rectangles are (top-left, bottom_right)
    for face in faces:
        draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline="red", width=3)

    return image
