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
from faceblur.threading import TerminatedException, TerminatingCookie

from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()

DEFAULT_OUT = "_deident"

SUPPORTED_EXTENSIONS = set(CONTAINER_EXENTSIONS + IMAGE_EXTENSIONS)


def is_filename_from_ext_group(filename, group):
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() in group


def _get_filenames_file(filename, on_error):
    if not is_filename_from_ext_group(filename, SUPPORTED_EXTENSIONS):
        on_error(f"Skipping unsupported file type: {os.path.basename(filename)}")
        return set()

    return set([filename])


def _get_filenames_dir(dirname, on_error):
    results = set()

    for root, dirs, files in os.walk(dirname, topdown=False):
        for name in files:
            results.update(_get_filenames_file(os.path.join(root, name), on_error))
        for name in dirs:
            results.update(_get_filenames_dir(os.path.join(root, name), on_error))

    return results


def get_supported_filenames(inputs, on_error=logging.getLogger(__name__).warning):
    filenames = set()

    for i in inputs:
        if os.path.isdir(i):
            filenames.update(_get_filenames_dir(i, on_error))
        elif os.path.isfile(i):
            filenames.update(_get_filenames_file(i, on_error))
        else:
            on_error(f"Invalid path: {i}")

    return set(sorted(list(filenames)))


def _create_output(filename, output, format=None):
    # Create the output directory
    os.makedirs(output, exist_ok=True)

    if format:
        is_image = is_filename_from_ext_group(filename, IMAGE_EXTENSIONS)
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


def _faceblur_image(input_filename, output, strength, confidence, format):
    # Load
    image = Image.open(input_filename)

    # Find faces
    faces = identify_faces_from_image(image, detection_confidence=confidence)

    # De-identify
    image = blur_faces(image, faces, strength)

    # Save
    output_filename = _create_output(input_filename, output, format)
    image.save(output_filename)


def _faceblur_video(
        input_filename, output,
        strength, confidence,
        format, encoder,
        progress_type,
        thread_type, threads, stop):

    # First find the faces. We can't do that on a frame-by-frame basis as it requires
    # to have the full data to interpolate missing face locations
    with InputContainer(input_filename, thread_type, threads) as input_container:
        faces = identify_faces_from_video(
            input_container, detection_confidence=confidence, progress=progress_type, stop=stop)

    # let's reverse the lists so that we would be popping elements, rather than read + delete
    for frames in faces.values():
        frames.reverse()

    output_filename = _create_output(input_filename, output, format)
    try:
        with InputContainer(input_filename, thread_type, threads) as input_container:
            with OutputContainer(output_filename, input_container, encoder) as output_container:
                with progress_type(desc="Encoding", total=input_container.video.frames, unit=" frames", leave=False) as progress:
                    # Demux the packet from input
                    for packet in input_container.demux():
                        if packet.stream.type == "video":
                            for frame in packet.decode():
                                if stop:
                                    stop.throwIfTerminated()

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
    except Exception as e:
        # Error/Stop request while encoding, make sure to remove the output
        try:
            os.remove(output_filename)
        except:
            pass

        raise e


def faceblur(
        inputs,
        output,
        strength=1.0,
        confidence=0.5,
        video_format=None,
        video_encoder=None,
        image_format=None,
        total_progress=tqdm.tqdm,
        file_progress=tqdm.tqdm,
        thread_type=THREAD_TYPE_DEFAULT,
        threads=os.cpu_count(),
        on_done=None,
        stop: TerminatingCookie = None):

    try:
        # Start processing them one by one
        filenames = get_supported_filenames(inputs)
        with total_progress(total=len(filenames), unit=" file(s)") as progress:
            for input_filename in filenames:
                progress.set_description(os.path.basename(input_filename))

                if stop:
                    stop.throwIfTerminated()

                if is_filename_from_ext_group(input_filename, IMAGE_EXTENSIONS):
                    # Handle images
                    _faceblur_image(input_filename, output, strength, confidence, image_format)
                else:
                    # Assume video
                    _faceblur_video(input_filename, output, strength, confidence, video_format,
                                    video_encoder, file_progress, thread_type, threads, stop)

                if on_done:
                    on_done(input_filename)

                progress.update()

    except TerminatedException:
        # No action neccessary
        pass
    finally:
        if on_done:
            on_done(None)
