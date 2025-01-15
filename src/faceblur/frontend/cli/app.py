# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os
import tqdm

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import ENCODERS, THREAD_TYPES, THREAD_TYPE_DEFAULT
from PIL import ImageFilter

av.logging.set_level(av.logging.ERROR)

OUTPUT_DEFAULT = "faceblur"


def __process_video_frame(frame: av.VideoFrame):
    img = frame.to_image()
    img = img.filter(ImageFilter.BoxBlur(64))
    new_frame = av.VideoFrame.from_image(img)
    new_frame.time_base = frame.time_base
    new_frame.dts = frame.dts
    new_frame.pts = frame.pts
    return new_frame


def __create_output(filename, output=None, format=None):
    if output is None:
        # create from filename's path
        output = os.path.abspath(os.path.join(os.path.dirname(filename), OUTPUT_DEFAULT))

    # Create the output directory
    os.makedirs(output, exist_ok=True)

    if format:
        filename, ext = os.path.splitext(filename)
        ext = CONTAINER_FORMATS[format][0]
        filename = f"{filename}.{ext}"

    return os.path.join(output, os.path.basename(filename))


def main():
    parser = argparse.ArgumentParser(
        description="A tool to obfuscate faces from photos and videos via blurring them."
    )

    parser.add_argument("input",
                        nargs="+",
                        help="Input file(s). May be photos or videos")

    parser.add_argument(
        "--output", "-o", help=f"""
                        Output folder for the blurred files.
                        Relative and absolute paths are supported, in which case all files will be saved to that folder".
                        If not specified it will create {OUTPUT_DEFAULT} in the directory of each input.
                        Absolute paths are supported, in which case all files will be saved in that folder.""")

    parser.add_argument("--encoder", "-e", choices=ENCODERS,
                        help="""
                        Select a custom video encoder.
                        If not speciefied it will use the same codecs as in the input videos""")

    parser.add_argument("--format", "-f",
                        choices=sorted(list(CONTAINER_FORMATS.keys())),
                        help="""
                        Select a custom container format for video files.
                        If not speciefied it will use the same cotainer as each input.""")

    parser.add_argument("--thread", "-t",
                        choices=THREAD_TYPES,
                        default=THREAD_TYPE_DEFAULT,
                        help="PyAV decoder/encoder threading model")

    args = parser.parse_args()

    # TODO: Support directories
    filenames = []
    for filename in args.input:
        _, ext = os.path.splitext(filename)
        if ext[1:].lower() not in CONTAINER_EXENTSIONS:
            print(f"Skipping unsupported file type : {os.path.basename(filename)}")
            continue

        filenames.append(filename)

    # Start processing them one by one
    with tqdm.tqdm(filenames, unit="file(s)") as progress:
        for input_filename in progress:
            progress.set_description(desc=os.path.basename(input_filename))
            output_filename = __create_output(input_filename, args.output, args.format)
            with InputContainer(input_filename, args.thread) as input_container:
                with OutputContainer(output_filename, input_container) as output_container:
                    # Demux the packet from input
                    packet = input_container.demux()

                    # Put into output (if demuxed)
                    output_container.mux(packet, __process_video_frame)


if __name__ == "__main__":
    main()
