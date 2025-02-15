# Copyright (C) 2025, Simona Dimitrova

import faceblur.faces.mode as fb_mode

from PIL import Image, ImageFilter, ImageDraw, ImageChops


MIN_FILTER_SIZE = 4
MAX_FILTER_SIZE = 1024
FACE_FILTER_DIVISOR = 20
STRENGTH = 100


def _calculate_filter_size(face, strength=STRENGTH):
    return tuple(
        max(MIN_FILTER_SIZE, min(MAX_FILTER_SIZE, int(round(f / FACE_FILTER_DIVISOR) * (strength / 100))))
        for f in (face.width, face.height)
    )


def blur_faces_rect(image: Image.Image, faces, strength):
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


def blur_faces_graceful(image: Image.Image, faces, strength):
    for face in faces:
        # Denormalise
        face = face.denormalise(image.width, image.height)

        # Calculate blur strength
        radius = _calculate_filter_size(face, strength)

        # Original dimentions of the face
        width, height = face.width, face.height

        # Expanded dimensions for the feather effect of the oval mask
        r_x, r_y = radius
        width_expanded, height_expanded = width + 2 * r_x, height + 2 * r_y

        # Create an oval image mask for the face region
        mask = Image.new("L", (width_expanded, height_expanded), 0)

        # Draw a solid ellipse in the mask (account for blur radius)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((r_x, r_y, r_x + width, r_y + height), fill=255)

        # Blur the mask to create a gradial effect
        mask = mask.filter(ImageFilter.BoxBlur(radius=radius))

        # Extract and blur the corresponding face area in the image
        # TODO: Do we need to blur the entire frame first in order to account
        # for gaussian effect being bigger than the blur radius
        face_image = image.crop((
            face.left - r_x,
            face.top - r_y,
            face.right + r_x,
            face.bottom + r_y
        ))

        blurred_face_image = face_image.filter(ImageFilter.GaussianBlur(radius=radius))

        # Composite the blurred face on the original image using the oval mask
        masked_blurred_faces = Image.composite(blurred_face_image, face_image, mask)
        image.paste(masked_blurred_faces, (face.left - r_x, face.top - r_y))

    return image


MODES = {
    fb_mode.Mode.RECT_BLUR: blur_faces_rect,
    fb_mode.Mode.GRACEFUL_BLUR: blur_faces_graceful,
}


def blur_faces(mode: fb_mode.Mode, image: Image, faces, strength=STRENGTH):
    if mode not in MODES:
        raise ValueError(f"Unsupported mode for blurring: {mode}")

    return MODES[mode](image, faces, strength)
