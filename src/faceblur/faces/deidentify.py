# Copyright (C) 2025, Simona Dimitrova

from PIL import ImageFilter
from PIL.Image import Image


MIN_FILTER_SIZE = 4
MAX_FILTER_SIZE = 1024
FACE_FILTER_DIVISOR = 20


def _calculate_filter_size(face, strength=1.0):
    return tuple(
        max(MIN_FILTER_SIZE, min(MAX_FILTER_SIZE, round(f / FACE_FILTER_DIVISOR) * strength))
        for f in (face.width, face.height)
    )


def blur_faces(image: Image, faces, strength=1.0):
    for face in faces:
        # denormalise
        face = face.denormalise(image.width, image.height)

        # Crop the face region
        face_image = image.crop((face.left, face.top, face.right, face.bottom))

        # Calculate blur strength
        radius = _calculate_filter_size(face, strength)

        # Apply a Gaussian blur to the cropped region
        blurred_face_image = face_image.filter(ImageFilter.GaussianBlur(radius=radius))

        # Paste the blurred region back onto the image
        image.paste(blurred_face_image, (face.left, face.top, face.right, face.bottom))

    return image
