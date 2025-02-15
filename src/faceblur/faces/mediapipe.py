# Copyright (C) 2025, Simona Dimitrova

import numpy as np

from faceblur.box import Box
from faceblur.faces.detector import Detector
from faceblur.faces.model import Model
from mediapipe.python.solutions.face_detection import FaceDetection

CONFIDENCE = 0.5

MODELS = [
    Model.MEDIA_PIPE_SHORT_RANGE,
    Model.MEDIA_PIPE_FULL_RANGE,
]


class MediaPipeDetector(Detector):
    def __init__(self, model, confidence=CONFIDENCE):
        super().__init__(FaceDetection(min_detection_confidence=confidence, model_selection=model))

    def detect(self, image):
        faces = []

        results = self._detector.process(np.asarray(image))
        if results.detections:
            for detection in results.detections:
                box = detection.location_data.relative_bounding_box

                # Adjust the faces as mediapipe returns relative data
                left = box.xmin
                top = box.ymin
                right = box.xmin + box.width
                bottom = box.ymin + box.height

                # Make sure the face box is within the image as detection may return coords out of bounds
                face = Box(top, right, bottom, left)
                faces.append(face)

        self._faces.append(faces)
        return faces
