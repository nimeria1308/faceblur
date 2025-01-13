# Copyright (C) 2025, Simona Dimitrova

import av

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


def encoder_from_decoder(stream_input, container_output, encoder=None):
    if not encoder:
        # Use same encoder as decoder
        encoder = stream_input.codec.name

    # We need a concrete frame rate to pass to add_stream
    frame_rate = stream_input.codec_context.framerate
    if not frame_rate:
        # variable frame rate, but some encoders don't seem to work fine with it
        # so use the guessed one
        frame_rate = round(stream_input.guessed_rate)

    stream_output = container_output.add_stream(encoder, frame_rate)

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
        value = getattr(stream_input.codec_context, p)
        if value is not None:
            setattr(stream_output.codec_context, p, value)

    return stream_output
