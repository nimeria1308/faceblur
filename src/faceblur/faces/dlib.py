# Copyright (C) 2025, Simona Dimitrova

import face_recognition
import math
import numpy as np


from faceblur.box import Box
from faceblur.faces.detector import Detector

MAX_IMAGE_SIZE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


class DLibDetector(Detector):
    def __init__(self, model, max_image_size=MAX_IMAGE_SIZE):
        super().__init__(model)
        self._max_image_size = max_image_size

    def detect(self, image):
        divisor = _find_divisor(image.width, image.height, self._max_image_size)
        if divisor > 1:
            # Needs to be scaled down
            image = image.resize((image.width // divisor, image.height // divisor))

        faces = []
        for detection in face_recognition.face_locations(np.asarray(image), model=self._detector):
            # Adjust faces if the image was scaled down
            if divisor > 1:
                detection = [point * divisor for point in detection]

            face = Box(*detection)
            faces.append(face)

        self._faces.append(faces)
        return faces

    def close(self):
        # no-op
        pass
