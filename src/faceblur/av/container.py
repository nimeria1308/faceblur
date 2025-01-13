# Copyright (C) 2025, Simona Dimitrova

import av
import av.container
import av.stream
import logging
import pymediainfo

from faceblur.av.stream import InputStream, OutputStream, CopyOutputStream
from faceblur.av.video import InputVideoStream, OutputVideoStream

EXTENSIONS = [
    "asf", "wmv",                   # windows video
    "avi",                          # audio/video interleave
    "mov", "mp4", "m4v", "3gp",     # mov
    "mkv",                          # matroska
    "mpg", "mpeg", "vob",           # MPEG1/2
    "mjpg",                         # Motion JPEG
    "webm",
]


class Container():
    def __init__(self, container: av.container.Container):
        self._container = container

    # Explicit close
    def close(self):
        """Close the container resource"""
        self._container.close()

    # Make sure not leaking on object destruction
    def __dealloc__(self):
        self.close()

    # Context manager (with/as)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class InputContainer(Container):
    _container: av.container.InputContainer

    def __init__(self, filename: str, thread_type: str = None):
        super().__init__(av.open(filename, metadata_errors="ignore"))

        self._info = pymediainfo.MediaInfo.parse(filename)
        self._duration = float(self._container.duration / av.time_base) if self._container.duration else 0

        # Update the thread type for the video decoders
        if thread_type is not None:
            for stream in self._container.streams.video:
                stream.thread_type = thread_type

        # Create dummy input streams for all non-video streams
        streams = [InputStream(stream) for stream in self._container.streams if stream.type != "video"]

        # video stream infos (tracks in MediaInfo terms)
        tracks = self._info.video_tracks

        # If there is only one track and ID, the ID doesn't matter
        if (len(tracks) == 1) and (len(self._container.streams.video) == 1):
            streams += [InputVideoStream(self._container.streams.video[0], self._info.video_tracks[0])]
        else:
            # Multiple tracks require matching the track IDs
            # Reshape the tracks into a {id: track}
            tracks = {t.track_id: t for t in tracks}

            # Directly use the ID for container formats that support IDs, e.g. MOV, MPEG, etc., see AVFMT_SHOW_IDS.
            # If IDs are not supported, assume the ID from the index the way MediaInfo expects them to be
            streams += [
                InputVideoStream(stream, tracks[stream.id if self._container.format.show_ids else stream.index + 1])
                for stream in self._container.streams.video
            ]

        # Save as a read-only sequence, i.e. a tuple
        self._streams = tuple(streams)

    @property
    def streams(self):
        return self._streams

    def demux(self):
        return self._container.demux()


class OutputContainer(Container):
    _container: av.container.OutputContainer
    _streams: dict[av.stream.Stream, OutputStream]

    def __init__(self, filename: str, template: InputContainer = None):
        super().__init__(av.open(filename, "w"))

        self._streams = {}

        if template:
            # Create output streams matching the input ones
            for stream in template._streams:
                self.add_stream_from_template(stream)

    def add_stream_from_template(self, template: InputStream):
        STREAM_TYPES = {
            "audio": CopyOutputStream,
            "video": OutputVideoStream,
            # currently subtitles streams are not remuxed, as this needs to be tested
            # currently data streams are not remuxed, as no data encoders are present,
            # and creating a data stream without a codec only appears to work for .ts
        }

        if template._stream.type not in STREAM_TYPES:
            # Don't handle unsupported stream types
            logging.getLogger(__name__).warning("Skipping unsupported stream type %s", template._stream.type)
            return None

        # create the stream wrapper
        stream = STREAM_TYPES[template._stream.type](self._container, template._stream)

        # add to mappings of input -> output streams
        self._streams[template._stream] = stream

        # and return to user
        return stream

    @property
    def streams(self):
        return tuple(self._streams.values())

    def mux(self, packets: av.Packet, frame_callback=None):
        if isinstance(packets, av.Packet):
            packets = [packets]

        for packet in packets:
            if packet.stream in self._streams:
                # Process the packet (this may mux it)
                self._streams[packet.stream].process(packet, frame_callback)
