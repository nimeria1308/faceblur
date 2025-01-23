# Copyright (C) 2025, Simona Dimitrova

import pytest

from faceblur.av.container import InputContainer
from data import VIDEO_FILES


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_demux(filename):
    with InputContainer(filename) as input_container:
        for packet in input_container.demux():
            assert packet
