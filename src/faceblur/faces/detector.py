# Copyright (C) 2025, Simona Dimitrova

class Detector:
    def __init__(self, detector):
        self._detector = detector
        self._faces = []

    @property
    def faces(self):
        return list(self._faces)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def detect(self, image):
        raise NotImplementedError()

    def close(self):
        self._detector.close()
