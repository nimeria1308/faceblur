# Copyright (C) 2025, Simona Dimitrova

import logging
import os
import tqdm

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import THREAD_TYPE_DEFAULT
from faceblur.av.video import VideoFrame
from faceblur.faces.identify import identify_faces_from_image, identify_faces_from_video
from faceblur.faces.deidentify import blur_faces
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.image import FORMATS as IMAGE_FORMATS

from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()

DEFAULT_OUT = "_deident"

SUPPORTED_EXTENSIONS = set(CONTAINER_EXENTSIONS + IMAGE_EXTENSIONS)


def _is_from_group(filename, group):
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() in group


def _get_filenames_file(filename):
    if not _is_from_group(filename, SUPPORTED_EXTENSIONS):
        logging.getLogger(__name__).warning(f"Skipping unsupported file type: {os.path.basename(filename)}")
        return set()

    return set([filename])


def _get_filenames_dir(dirname):
    results = set()

    for root, dirs, files in os.walk(dirname, topdown=False):
        for name in files:
            results.update(_get_filenames_file(os.path.join(root, name)))
        for name in dirs:
            results.update(_get_filenames_dir(os.path.join(root, name)))

    return results


def _get_filenames(inputs):
    filenames = set()

    for i in inputs:
        if os.path.isdir(i):
            filenames.update(_get_filenames_dir(i))
        elif os.path.isfile(i):
            filenames.update(_get_filenames_file(i))
        else:
            logging.getLogger(__name__).warning(f"Invalid path: {i}")

    return sorted(list(filenames))


def _create_output(filename, output, format=None):
    # Create the output directory
    os.makedirs(output, exist_ok=True)

    if format:
        is_image = _is_from_group(filename, IMAGE_EXTENSIONS)
        formats = IMAGE_FORMATS if is_image else CONTAINER_FORMATS
        filename, ext = os.path.splitext(filename)
        ext = formats[format][0]
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


def _faceblur_image(input_filename, output, strength, format):
    # Load
    image = Image.open(input_filename)

    # Find faces
    faces = identify_faces_from_image(image)

    # De-identify
    image = blur_faces(image, faces, strength)

    # Save
    output_filename = _create_output(input_filename, output, format)
    image.save(output_filename)


def _faceblur_video(
        input_filename, output,
        strength,
        format, encoder,
        progress_type,
        thread_type, threads):

    # First find the faces. We can't do that on a frame-by-frame basis as it requires
    # to have the full data to interpolate missing face locations
    with InputContainer(input_filename, thread_type, threads) as input_container:
        faces = identify_faces_from_video(input_container, progress=progress_type)

    # let's reverse the lists so that we would be popping elements, rather than read + delete
    for frames in faces.values():
        frames.reverse()

    output_filename = _create_output(input_filename, output, format)
    with InputContainer(input_filename, thread_type, threads) as input_container:
        with OutputContainer(output_filename, input_container, encoder) as output_container:
            with progress_type(desc="Encoding", total=input_container.video.frames, unit=" frames", leave=False) as progress:
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

                        if packet.dts is None:
                            # Flush encoder
                            output_container.mux(packet)
                    else:
                        # remux directly
                        output_container.mux(packet)


def faceblur(
        inputs,
        output,
        strength=1.0,
        format=None,
        video_encoder=None,
        progress_type=tqdm.tqdm,
        thread_type=THREAD_TYPE_DEFAULT,
        threads=os.cpu_count()):

    # Start processing them one by one
    with progress_type(_get_filenames(inputs), unit=" file(s)") as progress:
        for input_filename in progress:
            progress.set_description(desc=os.path.basename(input_filename))

            if _is_from_group(input_filename, IMAGE_EXTENSIONS):
                # TODO handle images
                _faceblur_image(input_filename, output, strength, None)
            else:
                # Assume video
                _faceblur_video(input_filename, output, strength, format,
                                video_encoder, progress_type, thread_type, threads)
