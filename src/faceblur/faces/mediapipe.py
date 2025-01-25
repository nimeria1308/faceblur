# Copyright (C) 2025, Simona Dimitrova

import numpy as np


from faceblur.box import Box
from faceblur.faces.detector import Detector
from mediapipe.python.solutions.face_detection import FaceDetection


class MediaPipeDetector(Detector):
    def __init__(self, model, confidence=0.5):
        super().__init__(FaceDetection(min_detection_confidence=confidence, model_selection=model))

    def detect(self, image):
        faces = []

        results = self._detector.process(np.asarray(image))
        if results.detections:
            max_box = Box(0, image.width - 1, image.height - 1, 0)

            for detection in results.detections:
                box = detection.location_data.relative_bounding_box

                # Adjust the faces as mediapipe returns relative data
                left = int(box.xmin * image.width)
                top = int(box.ymin * image.height)
                right = int((box.xmin + box.width) * image.width) - 1
                bottom = int((box.ymin + box.height) * image.height) - 1

                # Make sure the face box is within the image as detection may return coords out of bounds
                face = Box(top, right, bottom, left).intersect(max_box)
                faces.append(face)

        self._faces.append(faces)
        return faces
