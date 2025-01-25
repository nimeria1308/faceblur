# Copyright (C) 2025, Simona Dimitrova

from enum import StrEnum

# Google's deprecated models: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/models.md
# Updated version (short-range only): https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector

# Face Recognition @ Pypi: https://pypi.org/project/face-recognition/
# dlib C++ face recognition: http://dlib.net/


class Model(StrEnum):
    # Google, Deprecated 2023, up to 2 metres: https://storage.googleapis.com/mediapipe-assets/face_detection_short_range.tflite
    MEDIA_PIPE_SHORT_RANGE = "MEDIA_PIPE_SHORT_RANGE"

    # Google, Deprecated 2023, up to 5 metres: https://storage.googleapis.com/mediapipe-assets/face_detection_full_range.tflite
    MEDIA_PIPE_FULL_RANGE = "MEDIA_PIPE_FULL_RANGE"

    # HOG (fast) model
    DLIB_HOG = "DLIB_HOG"

    # CNN (slow and accurate) model
    DLIB_CNN = "DLIB_CNN"


DEFAULT = Model.MEDIA_PIPE_FULL_RANGE
