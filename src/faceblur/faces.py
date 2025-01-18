# Copyright (C) 2025, Simona Dimitrova

import face_recognition
import math
import numpy as np

from faceblur.av.container import InputContainer
from PIL.Image import Image


MAX_IMAGE_SIDE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def identify_faces_from_image(image: Image, max_side=MAX_IMAGE_SIDE):
    divisor = _find_divisor(image.width, image.height, max_side)
    if divisor > 1:
        # Needs to be scaled down
        image = image.resize((image.width // divisor, image.height // divisor))

    return face_recognition.face_locations(np.array(image))


def identify_faces_from_video(container: InputContainer, max_side=MAX_IMAGE_SIDE):
    faces = {stream.index: list() for stream in container.streams if stream.type == "video"}

    for packet in container.demux():
        if packet.stream.type == "video":
            # list with faces for each frame for this video stream
            stream_faces = faces[packet.stream.index]
            for frame in packet.decode():
                # find the faces in this frame
                faces_in_frame = identify_faces_from_image(frame.to_image(), max_side)
                print(faces_in_frame)
                # and add them to the list of found faces for the previous frames
                stream_faces.append(faces_in_frame)

    return faces
