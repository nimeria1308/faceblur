# Copyright (C) 2025, Simona Dimitrova

import av
import av.container
import av.stream
import logging
import pymediainfo

from faceblur.av.packet import Packet
from faceblur.av.stream import InputStream, OutputStream, CopyOutputStream
from faceblur.av.video import InputVideoStream, OutputVideoStream

FORMATS = {
    "mjpeg": ["mjpg", "mjpeg"],                 # raw MJPEG video, Loki SDL MJPEG
    "wmv": ["wmv", "asf"],                      # ASF (Advanced / Active Streaming Format)
    "avi": ["avi"],                             # AVI (Audio Video Interleaved)
    "mpeg": ["mpg", "mpeg"],                    # MPEG-1 Systems / MPEG program stream
    "mpeg-ts": ["ts", "m2t", "mts", "m2ts"],    # MPEG-TS (MPEG-2 Transport Stream)
    "3gp": ["3gp"],                             # 3GP (3GPP file format)
    "3g2": ["3g2"],                             # 3GP2 (3GPP2 file format)
    "mp4": ["mp4"],                             # MP4 (MPEG-4 Part 14)
    "mov": ["mov"],                             # QuickTime / MOV
    "mkv": ["mkv"],                             # Matroska
    "webm": ["webm"],                           # WebM
    "raw.h261": ["h261"],                       # raw H.261
    "raw.h263": ["h263"],                       # raw H.263
    "raw.h264": ["h264"],                       # raw H.264 video
    "raw.hevc": ["hevc"],                       # raw HEVC video
    "raw.yuv": ["yuv"],                         # raw YUV video
    "raw.rgb": ["rgb"],                         # raw RGB video
}

EXTENSIONS = sorted(list(set([ext for format in FORMATS.values() for ext in format])))


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
        self._streams = {stream: InputStream(stream) for stream in self._container.streams if stream.type != "video"}

        # video stream infos (tracks in MediaInfo terms)
        tracks = self._info.video_tracks

        # If there is only one track and ID, the ID doesn't matter
        if (len(tracks) == 1) and (len(self._container.streams.video) == 1):
            stream = self._container.streams.video[0]
            self._streams[stream] = InputVideoStream(stream, vars(self._info.video_tracks[0]))
        else:
            # Multiple tracks require matching the track IDs
            # Reshape the tracks into a {id: track}
            tracks = {t.track_id: t for t in tracks}

            # Directly use the ID for container formats that support IDs, e.g. MOV, MPEG, etc., see AVFMT_SHOW_IDS.
            # If IDs are not supported, assume the ID from the index the way MediaInfo expects them to be
            self._streams.update({
                stream:
                InputVideoStream(
                    stream, vars(tracks[stream.id if self._container.format.show_ids else stream.index + 1]))
                for stream in self._container.streams.video})

    @property
    def streams(self):
        return tuple(self._streams.values())

    def demux(self):
        for packet in self._container.demux():
            yield Packet(packet, self._streams[packet.stream])


class OutputContainer(Container):
    _container: av.container.OutputContainer
    _streams: dict[InputStream, OutputStream]

    def __init__(self, filename: str, template: InputContainer = None):
        super().__init__(av.open(filename, "w"))

        self._streams = {}

        if template:
            # Create output streams matching the input ones
            for stream in template._streams.values():
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
        stream = STREAM_TYPES[template._stream.type](self._container, template)

        # add to mappings of input -> output streams
        self._streams[template] = stream

        # and return to user
        return stream

    @property
    def streams(self):
        return tuple(self._streams.values())

    def mux(self, packets: av.Packet, frame_callback=None):
        if isinstance(packets, Packet):
            packets = [packets]

        for packet in packets:
            if packet.stream in self._streams:
                # Process the packet (this may mux it)
                self._streams[packet.stream].process(packet, frame_callback)
