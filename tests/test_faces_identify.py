# Copyright (C) 2025, Simona Dimitrova

import pytest

from data import FACES_IMAGE_FILES
from data import FACES_VIDEO_FILES
from faces import MODELS
from faceblur.av.container import InputContainer
from faceblur.av.video import DEFAULT_THREAD_TYPE
from faceblur.faces.identify import identify_faces_from_image
from faceblur.faces.identify import identify_faces_from_video
from faceblur.image import image_open

# Flatten
CONFIGS = [
    (model, options) for model in MODELS for options in MODELS[model]
]


@pytest.mark.parametrize("filename", FACES_IMAGE_FILES)
@pytest.mark.parametrize("model,model_options", CONFIGS, ids=str)
def test_faces_identify_from_image(filename, model, model_options):
    with image_open(filename) as image:
        assert image

        faces = identify_faces_from_image(image, model=model, model_options=model_options)
        assert faces is not None


@pytest.mark.parametrize("filename", FACES_VIDEO_FILES)
@pytest.mark.parametrize("model,model_options", CONFIGS, ids=str)
def test_faces_identify_from_video(filename, model, model_options):
    with InputContainer(filename, thread_type=DEFAULT_THREAD_TYPE) as input_container:
        faces = identify_faces_from_video(input_container, model=model, model_options=model_options)
        assert faces is not None
