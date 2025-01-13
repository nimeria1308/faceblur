# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os
import tqdm

from faceblur.av.container import EXTENSIONS as VIDEO_EXTENSIONS, InputContainer, OutputContainer
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


def __create_output(filename, output):
    if not os.path.isabs(output):
        # create from filename's path
        output = os.path.abspath(os.path.join(os.path.dirname(filename), output))

    # Create the output directory
    os.makedirs(output, exist_ok=True)

    return os.path.join(output, os.path.basename(filename))


def main():
    parser = argparse.ArgumentParser(
        description="A tool to obfuscate faces from photos and videos via blurring them."
    )

    parser.add_argument("input",
                        nargs="+",
                        help="Input file(s). May be photos or videos")

    parser.add_argument("--output", "-o",
                        default=OUTPUT_DEFAULT,
                        help=f"""
                        Output folder for the blurred files. Defaults to {OUTPUT_DEFAULT}""")

    parser.add_argument("--encoder", "-e", choices=ENCODERS,
                        help="""
                        Select a custom encoder for the videos.
                        If not speciefied it will use the same as the input video""")

    parser.add_argument("--thread", "-t",
                        choices=THREAD_TYPES,
                        default=THREAD_TYPE_DEFAULT,
                        help="PyAV decoder/encoder threading model")

    args = parser.parse_args()

    # TODO: Support directories
    filenames = []
    for filename in args.input:
        _, ext = os.path.splitext(filename)
        if ext[1:].lower() not in VIDEO_EXTENSIONS:
            print(f"Skipping unsupported file type : {os.path.basename(filename)}")
            continue

        filenames.append(filename)

    # Start processing them one by one
    with tqdm.tqdm(filenames, unit="file(s)") as progress:
        for input_filename in progress:
            progress.set_description(desc=os.path.basename(input_filename))
            output_filename = __create_output(input_filename, args.output)
            with InputContainer(input_filename, args.thread) as input_container:
                with OutputContainer(output_filename, input_container) as output_container:
                    # Demux the packet from input
                    packet = input_container.demux()

                    # Put into output (if demuxed)
                    output_container.mux(packet, __process_video_frame)


if __name__ == "__main__":
    main()
