# Copyright (C) 2025, Simona Dimitrova

from PIL.Image import Image
from PIL.ImageDraw import Draw


def debug_faces(image: Image, faces, strength=1.0):
    draw = Draw(image)

    def _draw(faces, colour, size):
        for face in faces:
            # denormalise
            face = face.denormalise(image.width, image.height)

            # Draw rectangle: Rectangles are (top-left, bottom_right)
            draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline=colour, width=size)

    # Original faces
    _draw(faces[0], "red", 6)

    # Processed faces
    _draw(faces[1], "blue", 3)

    return image
