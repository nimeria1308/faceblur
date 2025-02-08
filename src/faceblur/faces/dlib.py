# Copyright (C) 2025, Simona Dimitrova

import concurrent.futures as cf
import face_recognition
import os
import numpy as np

from faceblur.box import Box
from faceblur.faces.detector import Detector

UPSCALE = 1


def _process_frame(detector, image, frame_number, upscale):
    arr = np.asarray(image)

    # Detect faces
    faces = face_recognition.face_locations(arr, model=detector, number_of_times_to_upsample=upscale)

    # Compute unique face encodings
    encodings = face_recognition.face_encodings(arr, faces, model="large")

    # Wrap in boxes, but normalise first
    faces = [Box(*face).normalise(image.width, image.height) for face in faces]

    return frame_number, faces, encodings


class DLibDetector(Detector):
    def __init__(self, model, upscale=UPSCALE, threads=os.cpu_count()):
        super().__init__(model)
        self._upscale = upscale
        self._threads = threads
        self._executor = cf.ProcessPoolExecutor(max_workers=threads)
        self._futures = set()
        self._faces = {}
        self._encodings = {}
        self._current_frame = 0

    def _process_done(self, done: set[cf.Future]):
        for future in done:
            current_frame, faces, encodings = future.result()
            self._faces[current_frame] = faces
            self._encodings[current_frame] = encodings

        self._futures -= done

    def detect(self, image):
        # Do not pile up more work until there are enough free workers
        while len(self._futures) >= self._threads:
            # wait for one
            self._process_done(cf.wait(self._futures, return_when=cf.FIRST_COMPLETED).done)

        # queue up work
        self._futures.add(self._executor.submit(_process_frame,
                                                self._detector,
                                                image,
                                                self._current_frame,
                                                self._upscale))

        # next frame
        self._current_frame += 1

    @property
    def faces(self):
        # It means no more detections
        self._process_done(self._futures)

        # Return as a flat list
        return [self._faces[frame] for frame in sorted(self._faces)]

    @property
    def encodings(self):
        # It means no more detections
        self._process_done(self._futures)

        # Return as a flat list
        return [self._encodings[frame] for frame in sorted(self._encodings)]

    def close(self):
        self._executor.shutdown()
