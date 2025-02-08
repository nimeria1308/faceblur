# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os

from faceblur.app import DEFAULT_OUT
from faceblur.app import faceblur
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.video import ENCODERS, THREAD_TYPES, THREAD_TYPE_DEFAULT
from faceblur.faces.deidentify import MODES as BLUR_MODES
from faceblur.faces.mode import Mode, DEFAULT as DEFAULT_MODE
from faceblur.faces.model import Model, DEFAULT as DEFAULT_MODEL
from faceblur.image import FORMATS as IMAGE_FORMATS

av.logging.set_level(av.logging.ERROR)


def main():
    parser = argparse.ArgumentParser(
        description="A tool to obfuscate faces from photos and videos via blurring them."
    )

    parser.add_argument("inputs",
                        nargs="+",
                        help="Input file(s). May be photos or videos")

    parser.add_argument("--output", "-o",
                        default=DEFAULT_OUT,
                        help=f"Output folder for the blurred files. Defaults to {DEFAULT_OUT}.")

    parser.add_argument("--strength", "-s",
                        default=1.0, type=float,
                        help=f"""
                        Specify the strength of the deidentification.
                        It is a multiplier, so 0..1 makes them more recognisable,
                        while 1+ makes the less so.""")

    parser.add_argument("--video-format", "-f",
                        choices=sorted(list(CONTAINER_FORMATS.keys())),
                        help="""
                        Select a custom container format for video files.
                        If not speciefied it will use the same cotainer as each input.""")

    parser.add_argument("--video-encoder", "-V", choices=ENCODERS,
                        help="""
                        Select a custom video encoder.
                        If not speciefied it will use the same codecs as in the input videos""")

    parser.add_argument("--image-format", "-F",
                        choices=sorted(list(IMAGE_FORMATS.keys())),
                        help="""
                        Select a custom format for image files.
                        If not speciefied it will use the same format as each input.""")

    parser.add_argument("--thread-type", "-t",
                        choices=THREAD_TYPES,
                        default=THREAD_TYPE_DEFAULT,
                        help="PyAV decoder/encoder threading model")

    parser.add_argument("--threads", "-j",
                        default=os.cpu_count(), type=int,
                        help=f"""
                        How many threads to use for decoding/encoding video.
                        Defaults to the number of logical cores: {os.cpu_count()}.""")

    parser.add_argument("--mode", "-m",
                        choices=list(Mode),
                        default=DEFAULT_MODE,
                        help=f"""
                        Modes of operation:
                        RECT_BLUR: Uses gaussian blur directly on the face rects.
                        DEBUG: Dumps found faces and draws face boxes onto output.
                        Defaults to {DEFAULT_MODE}""")

    parser.add_argument("--model", "-M",
                        choices=list(Model),
                        default=DEFAULT_MODEL,
                        help=f"""
                        Detection models:
                        MEDIA_PIPE_SHORT_RANGE: Google MediaPipe, up to 2 metres.
                        MEDIA_PIPE_FULL_RANGE: Google MediaPipe, up to 5 metres.
                        Defaults to {DEFAULT_MODEL}""")

    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help="Enable verbose logging from all components.")

    args = parser.parse_args()

    # Fix the params

    # Mode
    mode_options = {}

    if args.mode in BLUR_MODES:
        mode_options["strength"] = args.strength

    # Image options
    image = {
        "format": args.image_format,
    }

    # Video options
    video = {
        "format": args.video_format,
        "encoder": args.video_encoder,
    }

    threads = {
        "thread_type": args.thread_type,
        "threads": args.threads,
    }

    args = {
        "inputs": args.inputs,
        "output": args.output,
        "model": args.model,
        "mode": args.mode,
        "mode_options": mode_options,
        "image_options": image,
        "video_options": video,
        "thread_options": threads,
        "verbose": args.verbose,
    }

    faceblur(**args)


if __name__ == "__main__":
    main()
