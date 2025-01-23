# Copyright (C) 2025, Simona Dimitrova

import av
import json
import logging
import os
import tqdm

from enum import StrEnum
from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import THREAD_TYPE_DEFAULT
from faceblur.av.video import VideoFrame
from faceblur.faces.identify import identify_faces_from_image, identify_faces_from_video
from faceblur.faces.debug import debug_faces
from faceblur.faces.deidentify import blur_faces
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.image import FORMATS as IMAGE_FORMATS
from faceblur.image import image_open
from faceblur.path import is_filename_from_ext_group
from faceblur.threading import TerminatedException, TerminatingCookie

from pillow_heif import register_heif_opener
register_heif_opener()

DEFAULT_OUT = "_deident"

SUPPORTED_EXTENSIONS = set(CONTAINER_EXENTSIONS + IMAGE_EXTENSIONS)


class Mode(StrEnum):
    RECT_BLUR = "RECT_BLUR"
    DEBUG = "DEBUG"


DEFAULT_MODE = Mode.RECT_BLUR


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

    return sorted(list(set(filenames)))


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


def _process_video_frame(frame: VideoFrame, faces, strength, mode):
    # do extra processing only if any faces were found
    if mode == Mode.DEBUG:
        if faces:
            # any faces
            # av.video.frame.VideoFrame -> PIL.Image
            image = frame.to_image()

            # Draw face boxes
            image = debug_faces(image, faces)

            # PIL.Image -> av.video.frame.VideoFrame
            frame = VideoFrame.from_image(image, frame)

    elif mode == Mode.RECT_BLUR:
        if faces.interpolated:
            # av.video.frame.VideoFrame -> PIL.Image
            image = frame.to_image()

            # De-identify via a rectangular gaussian blur
            image = blur_faces(image, faces.interpolated, strength)

            # PIL.Image -> av.video.frame.VideoFrame
            frame = VideoFrame.from_image(image, frame)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    return frame


def _faceblur_image(input_filename, output, strength, confidence, format, mode):
    # Load
    image = image_open(input_filename)

    # Find faces
    faces = identify_faces_from_image(image, detection_confidence=confidence)

    output_filename = _create_output(input_filename, output, format)

    if mode == Mode.DEBUG:
        # Save face boxes to file
        with open(f"{output_filename}.json", "w") as f:
            json.dump(faces.to_json(), f, indent=4)

        # Draw face boxes
        image = debug_faces(image, faces)
    elif mode == Mode.RECT_BLUR:
        # De-identify via a rectangular gaussian blur
        image = blur_faces(image, faces.merged, strength)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    # Save
    image.save(output_filename)


def _faceblur_video(
        input_filename, output,
        strength, confidence,
        format, encoder,
        progress_type,
        thread_type, threads, stop, mode):

    # First find the faces. We can't do that on a frame-by-frame basis as it requires
    # to have the full data to interpolate missing face locations
    with InputContainer(input_filename, thread_type, threads) as input_container:
        faces = identify_faces_from_video(
            input_container, detection_confidence=confidence, progress=progress_type, stop=stop)

    output_filename = _create_output(input_filename, output, format)
    if mode == Mode.DEBUG:
        # Save face boxes to file
        with open(f"{output_filename}.json", "w") as f:
            faces_json = {index: [d.to_json() for d in detections] for index, detections in faces.items()}
            json.dump(faces_json, f, indent=4)

    # let's reverse the lists so that we would be popping elements, rather than read + delete
    for detections in faces.values():
        detections.reverse()

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
                                frame = _process_video_frame(frame, faces_in_frame, strength, mode)

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
        on_error=None,
        stop: TerminatingCookie = None,
        mode=DEFAULT_MODE,
        verbose=False):

    # WARNING/libav.swscaler           (66753 ): deprecated pixel format used, make sure you did set range correctly
    logging_format = "%(levelname)-7s/%(name)-24s (%(process)-6d): %(message)s"
    if verbose:
        av.logging.set_level(av.logging.VERBOSE)
        logging.basicConfig(format=logging_format, level=logging.DEBUG)
    else:
        av.logging.set_level(av.logging.ERROR)
        logging.basicConfig(format=logging_format)

    # Start processing them one by one
    filenames = get_supported_filenames(inputs)
    failed = False
    with total_progress(total=len(filenames), unit=" file(s)") as progress:
        for input_filename in filenames:
            progress.set_description(os.path.basename(input_filename))

            try:
                if stop:
                    stop.throwIfTerminated()

                if is_filename_from_ext_group(input_filename, IMAGE_EXTENSIONS):
                    # Handle images
                    _faceblur_image(input_filename, output, strength, confidence, image_format, mode)
                else:
                    # Assume video
                    _faceblur_video(input_filename, output, strength, confidence, video_format,
                                    video_encoder, file_progress, thread_type, threads, stop, mode)

                if on_done:
                    on_done(input_filename)

                progress.update()

            except TerminatedException as tex:
                # Cancelled prematurely
                if on_done:
                    break

            except Exception as ex:
                # Report error back to UI
                if on_error:
                    on_error(ex, input_filename)
                    failed = True
                    break
                else:
                    raise ex

    # All finished (only if not failed)
    if on_done and not failed:
        on_done(None)
