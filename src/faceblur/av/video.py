# Copyright (C) 2025, Simona Dimitrova

import av
import av.stream
import pymediainfo

from faceblur.av.stream import InputStream, OutputStream

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


def _dimensions_for_rotated(width: int, height: int, rotation: float):
    angle = _get_angle360(rotation)

    if abs(angle - 90) < 1:
        # Rotated by 90
        return height, width
    elif abs(angle - 270) < 1:
        # Rotated by 270
        return height, width
    else:
        return width, height


class InputVideoStream(InputStream):
    _info: pymediainfo.Track

    def __init__(self, stream: av.stream.Stream, info: pymediainfo.Track):
        super().__init__(stream)
        self._info = info

    @property
    def info(self):
        return self._info


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
            frame_rate = round(input_stream._stream.guessed_rate)

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
            "width",
            "height",
            # "field_order", # N/A

            "color_range",
            "color_primaries",
            "color_trc",
            "colorspace",

            # "chroma_sample_location", # N/A
            "sample_aspect_ratio",
            # "has_b_frames", # Read-only
            "framerate",

            "extradata",
        ]

        for p in params:
            value = getattr(input_stream._stream.codec_context, p)
            if value is not None:
                setattr(output_stream.codec_context, p, value)

        # Get rotation from stream side data and fix the resolutions
        rotation = float(input_stream.info.get("rotation", 0))
        if rotation:
            c_in = input_stream._stream.codec_context
            c_out = output_stream.codec_context
            width, height = _dimensions_for_rotated(c_in.width, c_in.height, rotation)
            c_out.width = width
            c_out.height = height

        super().__init__(output_stream, input_stream)

    def process(self, packet: av.Packet, frame_callback=None):
        for frame in packet.decode():
            if frame_callback:
                # Process frame
                frame = frame_callback(frame)

            # now encode
            for packet_output in self._output_stream.encode(frame):
                self._output_stream.container.mux(packet_output)

        if packet.dts is None:
            # Flush the encoder.
            # Note that the "empty" packet MUST fist be passed to the
            # encoder to signal flushing
            while True:
                try:
                    for packet_output in self._output_stream.encode(None):
                        self._output_stream.container.mux(packet_output)
                except av.error.EOFError:
                    break
