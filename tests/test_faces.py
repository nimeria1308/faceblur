# Copyright (C) 2025, Simona Dimitrova

import pytest

from data import IMAGE_FILES
from data import VIDEO_FILES
from faceblur.av.container import InputContainer
from faceblur.av.video import THREAD_TYPE_DEFAULT
from faceblur.faces.identify import identify_faces_from_image
from faceblur.faces.identify import identify_faces_from_video
from faceblur.image import image_open


@pytest.mark.parametrize("filename", IMAGE_FILES)
def test_faces_identify_from_image(filename):
    with image_open(filename) as image:
        assert image

        faces = identify_faces_from_image(image)
        assert faces is not None


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_faces_identify_from_video(filename):
    with InputContainer(filename, thread_type=THREAD_TYPE_DEFAULT) as input_container:
        faces = identify_faces_from_video(input_container)
        assert faces is not None
