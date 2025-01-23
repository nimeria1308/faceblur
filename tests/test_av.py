# Copyright (C) 2025, Simona Dimitrova

import av.error
import pytest

from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import THREAD_TYPE_DEFAULT
from data import VIDEO_FILES


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_demux(filename):
    with InputContainer(filename, thread_type=THREAD_TYPE_DEFAULT) as input_container:
        for packet in input_container.demux():
            assert packet


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_decode(filename):
    with InputContainer(filename, thread_type=THREAD_TYPE_DEFAULT) as input_container:
        for packet in input_container.demux():
            assert packet

            if packet.stream.type == "video":
                try:
                    for frame in packet.decode():
                        assert frame
                except av.error.InvalidDataError as e:
                    # Drop the packet
                    pass
