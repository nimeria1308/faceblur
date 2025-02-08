# Copyright (C) 2025, Simona Dimitrova

import av.error
import os
import pytest
import tempfile

from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import DEFAULT_THREAD_TYPE
from data import VIDEO_FILES


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_demux(filename):
    with InputContainer(filename, thread_type=DEFAULT_THREAD_TYPE) as input_container:
        for packet in input_container.demux():
            assert packet


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_decode(filename):
    with InputContainer(filename, thread_type=DEFAULT_THREAD_TYPE) as input_container:
        for packet in input_container.demux():
            assert packet

            if packet.stream.type == "video":
                try:
                    for frame in packet.decode():
                        assert frame
                except av.error.InvalidDataError as e:
                    # Drop the packet
                    pass


@pytest.mark.parametrize("filename", VIDEO_FILES)
def test_video_recode(filename):
    with tempfile.TemporaryDirectory() as tempdir:
        with InputContainer(filename, thread_type=DEFAULT_THREAD_TYPE) as input_container:
            output = os.path.join(tempdir, os.path.basename(filename))
            with OutputContainer(output, input_container) as output_container:
                for packet in input_container.demux():
                    assert packet

                    if packet.stream.type == "video":
                        try:
                            for frame in packet.decode():
                                assert frame

                                # Encode + mux
                                output_container.mux(frame)

                        except av.error.InvalidDataError as e:
                            # Drop the packet
                            pass
