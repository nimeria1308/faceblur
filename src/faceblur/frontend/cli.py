# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os

from faceblur.app import DEFAULT_OUT
from faceblur.app import faceblur
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.video import ENCODERS, THREAD_TYPES, THREAD_TYPE_DEFAULT

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

    parser.add_argument("--format", "-f",
                        choices=sorted(list(CONTAINER_FORMATS.keys())),
                        help="""
                        Select a custom container format for video files.
                        If not speciefied it will use the same cotainer as each input.""")

    parser.add_argument("--encoder", "-e", choices=ENCODERS,
                        help="""
                        Select a custom video encoder.
                        If not speciefied it will use the same codecs as in the input videos""")

    parser.add_argument("--thread_type", "-t",
                        choices=THREAD_TYPES,
                        default=THREAD_TYPE_DEFAULT,
                        help="PyAV decoder/encoder threading model")

    parser.add_argument("--threads", "-j",
                        default=os.cpu_count(), type=int,
                        help=f"""
                        How many threads to use for decoding/encoding video.
                        Defaults to the number of logical cores: {os.cpu_count()}.""")

    args = vars(parser.parse_args())
    faceblur(**args)


if __name__ == "__main__":
    main()
