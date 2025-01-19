# Copyright (C) 2025, Simona Dimitrova

import logging
import os
import tqdm

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import THREAD_TYPE_DEFAULT
from faceblur.av.video import VideoFrame
from faceblur.faces.identify import identify_faces_from_video
from faceblur.faces.deidentify import blur_faces


DEFAULT_OUT = "_deident"


def _create_output(filename, output, format=None):
    # Create the output directory
    os.makedirs(output, exist_ok=True)

    if format:
        filename, ext = os.path.splitext(filename)
        ext = CONTAINER_FORMATS[format][0]
        filename = f"{filename}.{ext}"

    return os.path.join(output, os.path.basename(filename))


def _process_video_frame(frame: VideoFrame, faces, strength):
    # do extra processing only if any faces were found
    if faces:
        # av.video.frame.VideoFrame -> PIL.Image
        image = frame.to_image()

        # De-identify
        image = blur_faces(image, faces, strength)

        # PIL.Image -> av.video.frame.VideoFrame
        frame = VideoFrame.from_image(image, frame)

    return frame


def faceblur(
        inputs,
        output,
        strength=1.0,
        format=None,
        encoder=None,
        progress_type=tqdm.tqdm,
        thread_type=THREAD_TYPE_DEFAULT,
        threads=os.cpu_count()):

    # TODO: Support directories
    filenames = []
    for filename in inputs:
        _, ext = os.path.splitext(filename)
        if ext[1:].lower() not in CONTAINER_EXENTSIONS:
            logging.getLogger(__name__).warning(f"Skipping unsupported file type : {os.path.basename(filename)}")
            continue

        filenames.append(filename)

    # Start processing them one by one
    with progress_type(filenames, unit="file(s)") as progress:
        for input_filename in inputs:
            progress.set_description(desc=os.path.basename(input_filename))

            # First find the faces. We can't do that on a frame-by-frame basis as it requires
            # to have the full data to interpolate missing face locations
            with InputContainer(input_filename, thread_type, threads) as input_container:
                faces = identify_faces_from_video(input_container, threads, progress=progress_type)

            # let's reverse the lists so that we would be popping elements, rather than read + delete
            for frames in faces.values():
                frames.reverse()

            output_filename = _create_output(input_filename, output, format)
            with InputContainer(input_filename, thread_type, threads) as input_container:
                with OutputContainer(output_filename, input_container, encoder) as output_container:
                    with tqdm.tqdm(desc="Encoding", total=input_container.video.frames, unit="frames", leave=False) as progress:
                        # Demux the packet from input
                        for packet in input_container.demux():
                            if packet.stream.type == "video":
                                for frame in packet.decode():
                                    # Get the list of faces for this stream and frame
                                    faces_in_frame = faces[frame.stream.index].pop()

                                    # Process (if necessary)
                                    frame = _process_video_frame(frame, faces_in_frame, strength)

                                    # Encode + mux
                                    output_container.mux(frame)
                                    progress.update()
                            else:
                                # remux directly
                                output_container.mux(packet)
                                progress.update()
