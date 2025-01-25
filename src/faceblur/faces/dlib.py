# Copyright (C) 2025, Simona Dimitrova

import concurrent.futures as cf
import face_recognition
import math
import os
import numpy as np


from faceblur.box import Box
from faceblur.faces.detector import Detector

MAX_IMAGE_SIZE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def _process_frame(detector, image, frame_number, divisor):
    faces = []

    for detection in face_recognition.face_locations(np.asarray(image), model=detector):
        # Adjust faces if the image was scaled down
        if divisor > 1:
            detection = [point * divisor for point in detection]

        face = Box(*detection)
        faces.append(face)

    return frame_number, faces


class DLibDetector(Detector):
    def __init__(self, model, max_image_size=MAX_IMAGE_SIZE, threads=os.cpu_count()):
        super().__init__(model)
        self._max_image_size = max_image_size
        self._threads = threads
        self._executor = cf.ProcessPoolExecutor(max_workers=threads)
        self._futures = set()
        self._faces = {}
        self._current_frame = 0

    def _process_done(self, done: set[cf.Future]):
        for future in done:
            current_frame, faces_in_frame = future.result()
            self._faces[current_frame] = faces_in_frame

        self._futures -= done

    def detect(self, image):
        # Do not pile up more work until there are enough free workers
        while len(self._futures) >= self._threads:
            # wait for one
            self._process_done(cf.wait(self._futures, return_when=cf.FIRST_COMPLETED).done)

        divisor = _find_divisor(image.width, image.height, self._max_image_size)
        if divisor > 1:
            # Needs to be scaled down
            image = image.resize((image.width // divisor, image.height // divisor))

        # queue up work
        self._futures.add(self._executor.submit(_process_frame,
                                                self._detector,
                                                np.asarray(image),
                                                self._current_frame,
                                                divisor))

        # next frame
        self._current_frame += 1

    @property
    def faces(self):
        # It means no more detections
        self._process_done(self._futures)

        # Return as a flat list
        return [self._faces[frame] for frame in sorted(self._faces)]

    def close(self):
        self._executor.shutdown()
