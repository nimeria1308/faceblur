# Copyright (C) 2025, Simona Dimitrova

import pytest

from data import IMAGE_FILES
from faceblur.faces.identify import identify_faces_from_image
from faceblur.image import image_open


@pytest.mark.parametrize("filename", IMAGE_FILES)
def test_faces_identify_from_image(filename):
    with image_open(filename) as image:
        assert image

        faces = identify_faces_from_image(image)
        assert faces is not None
