# Copyright (C) 2025, Simona Dimitrova

import pytest

from faceblur.av.container import Container
from data import VIDEO_FILES


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_recode(filename):
    print(filename)
