# Copyright (C) 2025, Simona Dimitrova

from faceblur.faces.model import DEFAULT as DEFAULT_MODEL
from faceblur.faces.model import Model

MODELS = {
    Model.MEDIA_PIPE_FULL_RANGE: [
        {},  # default (50)
        {"confidence": 25},
        {"confidence": 75},
    ],

    Model.DLIB_HOG: [
        {},  # default (1)
        {"upscale": 2},
    ],
}
