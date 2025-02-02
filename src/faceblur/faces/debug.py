# Copyright (C) 2025, Simona Dimitrova

from PIL.Image import Image
from PIL.ImageDraw import Draw


def debug_faces(image: Image, faces):
    draw = Draw(image)

    def _draw(faces, colour, size):
        for face in faces:
            # denormalise
            face = face.denormalise(image.width, image.height)

            # Draw rectangle: Rectangles are (top-left, bottom_right)
            draw.rectangle([(face.left, face.top), (face.right, face.bottom)], fill=None, outline=colour, width=size)

    original_faces, processed_faces = faces

    # Original faces
    _draw(original_faces, "red", 6)

    # Processed faces
    if processed_faces is not None:
        _draw(processed_faces, "blue", 3)

    return image
