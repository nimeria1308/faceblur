# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os
import tqdm

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.stream import OutputStream
from faceblur.av.video import ENCODERS, THREAD_TYPES, THREAD_TYPE_DEFAULT
from faceblur.faces import identify_faces_from_video
from faceblur.faces import blur_faces

av.logging.set_level(av.logging.ERROR)

OUTPUT_DEFAULT = "faceblur"


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

    parser.add_argument("--thread_type", "-t",
                        choices=THREAD_TYPES,
                        default=THREAD_TYPE_DEFAULT,
                        help="PyAV decoder/encoder threading model")

    parser.add_argument("--threads", "-j",
                        default=os.cpu_count(), type=int,
                        help=f"""
                        How many threads to use for decoding/encoding video.
                        Defaults to the number of logical cores: {os.cpu_count()}.""")

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

            # First find the faces. We can't do that on a frame-by-frame basis as it requires
            # to have the full data to interpolate missing face locations
            with InputContainer(input_filename, args.thread_type, args.threads) as input_container:
                faces = identify_faces_from_video(input_container, args.threads)

            # let's reverse the lists so that we would be popping elements, rather than read + delete
            for frames in faces.values():
                frames.reverse()

            def __process_video_frame(frame: av.VideoFrame, stream: OutputStream):
                # Get the list of faces for this stream and frame
                faces_in_frame = faces[stream.input.index].pop()

                # do extra processing only if any faces were found
                if faces_in_frame:
                    # av.video.frame.VideoFrame -> PIL.Image
                    image = frame.to_image()

                    # De-identify
                    image = blur_faces(image, faces_in_frame, args.strength)

                    # PIL.Image -> av.video.frame.VideoFrame
                    new_frame = av.VideoFrame.from_image(image)
                    new_frame.time_base = frame.time_base
                    new_frame.dts = frame.dts
                    new_frame.pts = frame.pts
                    frame = new_frame

                return frame

            output_filename = __create_output(input_filename, args.output, args.format)
            with InputContainer(input_filename, args.thread_type, args.threads) as input_container:
                with OutputContainer(output_filename, input_container) as output_container:
                    # Demux the packet from input
                    packet = input_container.demux()

                    # Put into output (if demuxed)
                    output_container.mux(packet, __process_video_frame)


if __name__ == "__main__":
    main()
