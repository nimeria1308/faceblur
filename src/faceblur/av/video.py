# Copyright (C) 2025, Simona Dimitrova

import av
import av.container
import av.stream
import logging
import math
import pymediainfo

from faceblur.av.stream import InputStream, OutputStream
from faceblur.av.filter import Filter, Graph
from faceblur.av.frame import Frame
from faceblur.av.packet import Packet
from PIL.Image import Image

THREAD_TYPES = [
    "SLICE",
    "FRAME",
    "AUTO,"
]

THREAD_TYPE_DEFAULT = "AUTO"


def __check_codec(codec):
    try:
        codec = av.codec.Codec(codec, "w")
        return codec.type == "video"
    except av.codec.codec.UnknownCodecError:
        # Not encoder
        return False


ENCODERS = sorted([codec for codec in av.codecs_available if __check_codec(codec)])


def _get_angle360(angle: float):
    # Make sure the angle is in 0..360
    # See get_rotation() in fftools/cmdutils.c
    return angle - 360 * int(angle/360 + 0.9/360)


def _dimensions_for_rotated(width, height, angle):
    if abs(angle - 90) < 1:
        # Rotated by 90
        return height, width
    elif abs(angle - 270) < 1:
        # Rotated by 270
        return height, width
    else:
        return width, height


def _filters_for_rotated(angle, input_stream: InputStream):
    # Handle different rotations.
    # See `if (autorotate) {` in fftools/ffplay.c
    if abs(angle - 90) < 1:
        # Rotated by 90. Simple transpose is enough
        return [
            Filter("transpose", dir="clock"),
        ]
    elif abs(angle - 180) < 1:
        # Rotated by 180. Use horizontal and vertical flip
        return [
            Filter("hflip"),
            Filter("vflip"),
        ]
    elif abs(angle - 270) < 1:
        # Rotated by 270. Simple transpose is enough
        return [
            Filter("transpose", dir="cclock"),
        ]
    elif abs(angle) > 1:
        # Generic rotation by an odd angle
        return [
            Filter("rotate", angle=angle * (math.pi / 180)),
        ]
    else:
        # No rotation necessary (0 <= angle < 1)
        return None


class InputVideoStream(InputStream):
    _info: pymediainfo.Track
    _graph = None

    def __init__(self, stream: av.stream.Stream, info: pymediainfo.Track):
        super().__init__(stream)
        self._info = info

        # Get rotation from stream side data and fix the resolutions
        rotation = float(info.get("rotation", 0))
        cc = stream.codec_context
        angle = _get_angle360(rotation)
        self._width, self._height = _dimensions_for_rotated(cc.width, cc.height, angle)

        if rotation:
            # Need to create rotation filters
            filters = _filters_for_rotated(angle, stream)
            if filters:
                self._graph = Graph(self, filters)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def info(self):
        return self._info

    @property
    def frames(self):
        return self._stream.frames


class VideoFrame(Frame):
    def to_image(self) -> Image:
        return self._frame.to_image()

    @staticmethod
    def from_image(image: Image, frame: Frame):
        new_frame = av.VideoFrame.from_image(image)
        new_frame = Frame(new_frame)
        new_frame.copy_metadata(frame)
        return new_frame


class VideoPacket(Packet):
    _stream: InputVideoStream

    def decode(self):
        for frame in self._packet.decode():
            if self._stream._graph:
                self._stream._graph.push(frame)
                frame = self._stream._graph.pull()
            yield VideoFrame(frame, self.stream)


CODECS_NEED_SINGLE_THREAD = [
    "mjpeg",
]


class OutputVideoStream(OutputStream):
    def __init__(self,
                 output_container: av.container.OutputContainer,
                 input_stream: InputVideoStream = None,
                 encoder: str = None):

        if not encoder:
            # Use same encoder as decoder
            encoder = input_stream._stream.codec.name

        # We need a concrete frame rate to pass to add_stream
        frame_rate = input_stream._stream.codec_context.framerate
        if not frame_rate:
            # variable frame rate, but some encoders don't seem to work fine with it
            # so use the guessed one
            frame_rate = math.ceil(float(
                input_stream._info.get("maximum_frame_rate", input_stream._stream.guessed_rate)))

        try:
            output_stream = output_container.add_stream(encoder, frame_rate)
        except ValueError as e:
            logging.getLogger(__name__).warning(f"Could not set encoder '{encoder}': {
                e}. Using default encoder '{output_container.default_video_codec}'")

            # Provided encoder, or encode from input stream is not supported in this container
            # Use the default video encoder
            encoder = output_container.default_video_codec
            output_stream = output_container.add_stream(encoder, frame_rate)

        # Those parameters are from FFMPEG's avcodec_parameters_to_context(), which is
        # called from av.container.output.OutputContainer.add_stream_from_template().
        params = [
            # General
            "bit_rate",
            # "bits_per_coded_sample", # Not supported for encoders
            # "bits_per_raw_sample", # N/A
            "profile",
            # "level", # N/A

            # Video
            "pix_fmt",
            # do not read width/height directly from the codec context
            # "field_order", # N/A

            "color_range",
            "color_primaries",
            "color_trc",
            "colorspace",

            # "chroma_sample_location", # N/A
            "sample_aspect_ratio",
            # "has_b_frames", # Read-only

            "extradata",

            # Copy over the thread config
            "thread_type",
            "thread_count",
        ]

        for p in params:
            value = getattr(input_stream._stream.codec_context, p)
            if value is not None:
                setattr(output_stream.codec_context, p, value)

        # Get the dimensions from the InputStream not from CodecContext,
        # in order to take any rotation into account
        output_stream.codec_context.width = input_stream.width
        output_stream.codec_context.height = input_stream.height

        # FIXME: bit_rate_tolerance is None even after setting it explicitly

        # Some codecs like mjpeg do not work well with multuthreading
        if encoder in CODECS_NEED_SINGLE_THREAD:
            output_stream.codec_context.thread_count = 1

        super().__init__(output_stream, input_stream)

    def process(self, frame: VideoFrame):
        if frame.dts is not None:
            # Encode
            for packet_output in self._stream.encode(frame._frame):
                self._stream.container.mux(packet_output)
        else:
            # Flush the encoder.
            # Note that the "empty" packet MUST first be passed to the
            # encoder to signal flushing
            while True:
                try:
                    for packet_output in self._stream.encode(None):
                        self._stream.container.mux(packet_output)
                except av.error.EOFError:
                    break
