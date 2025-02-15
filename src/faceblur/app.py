# Copyright (C) 2025, Simona Dimitrova

import av
import json
import logging
import os
import tqdm

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.container import InputContainer, OutputContainer
from faceblur.av.video import DEFAULT_THREAD_TYPE
from faceblur.av.video import VideoFrame
from faceblur.faces.mode import Mode
from faceblur.faces.mode import DEFAULT as DEFAULT_MODE
from faceblur.faces.model import DEFAULT as DEFAULT_MODEL
from faceblur.faces.identify import identify_faces_from_image, identify_faces_from_video
from faceblur.faces.debug import debug_faces
from faceblur.faces.obfuscate import blur_faces
from faceblur.faces.obfuscate import MODES as BLUR_MODES
from faceblur.faces.process import process_faces_in_frames
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.image import FORMATS as IMAGE_FORMATS
from faceblur.image import image_open
from faceblur.path import is_filename_from_ext_group
from faceblur.threading import TerminatedException, TerminatingCookie


DEFAULT_OUT = "obfuscated"

SUPPORTED_EXTENSIONS = set(CONTAINER_EXENTSIONS + IMAGE_EXTENSIONS)


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


def _process_video_frame(frame: VideoFrame, faces, mode, mode_options):
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

    elif mode in BLUR_MODES:
        if faces:
            # av.video.frame.VideoFrame -> PIL.Image
            image = frame.to_image()

            # De-identify via a rectangular gaussian blur (using processed faces)
            image = blur_faces(mode, image, faces[1] if faces[1] is not None else faces[0], **mode_options)

            # PIL.Image -> av.video.frame.VideoFrame
            frame = VideoFrame.from_image(image, frame)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    return frame


def _get_debug_root(input_filename, output_filename, model, model_options, format=None, encoder=None):
    root = {
        "input": input_filename,
        "output": output_filename,
        "model": {
            "name": model,
            "options": model_options,
        },
    }

    if format:
        root["output_format"] = format

    if encoder:
        root["output_encoder"] = encoder

    return root


def _faceblur_image(input_filename, output, model, model_options, mode, mode_options, format=None):
    # Load
    image = image_open(input_filename)

    # Find faces
    faces = identify_faces_from_image(image, model, model_options=model_options)

    output_filename = _create_output(input_filename, output, format)

    if mode == Mode.DEBUG:
        # Save face boxes to file
        with open(f"{output_filename}.json", "w") as f:
            root = _get_debug_root(input_filename, output_filename, model, model_options, format)
            root["faces"] = [face.to_json() for face in faces]
            json.dump(root, f, indent=4)

        # Draw face boxes
        image = debug_faces(image, (faces, None))
    elif mode in BLUR_MODES:
        # De-identify via a rectangular gaussian blur
        image = blur_faces(mode, image, faces, **mode_options)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    # Save
    image.save(output_filename)


def _faceblur_video(
        input_filename, output,
        model, model_options,
        tracking_options,
        mode, mode_options,
        progress_type,
        stop,
        format=None,
        encoder=None,
        thread_type=DEFAULT_THREAD_TYPE,
        threads=os.cpu_count()):

    # First find the faces. We can't do that on a frame-by-frame basis as it requires
    # to have the full data to interpolate missing face locations
    with InputContainer(input_filename, thread_type, threads) as input_container:
        faces = identify_faces_from_video(
            input_container, model, model_options=model_options, progress=progress_type, stop=stop)

    if tracking_options:
        # Use face tracking and interpolation between frames
        # Clear false positive, fill in false negatives
        faces = {
            stream: process_faces_in_frames(frames_in_stream[0], frames_in_stream[1], frames_in_stream[2], **tracking_options)
            for stream, frames_in_stream in faces.items()}
    else:
        faces = {
            stream: (faces_in_stream[0], None)
            for stream, faces_in_stream in faces.items()}

    output_filename = _create_output(input_filename, output, format)
    if mode == Mode.DEBUG:
        # Save face boxes to file
        with open(f"{output_filename}.json", "w") as f:
            root = _get_debug_root(input_filename, output_filename, model, model_options, format, encoder)
            faces_json = {index:
                          {
                              "original": [[face.to_json() for face in frame] for frame in frames[0]],
                              "processed": [[face.to_json() for face in frame] for frame in frames[1]] if tracking_options else [],
                          }
                          for index, frames in faces.items()}
            root["streams"] = faces_json
            root["tracking"] = tracking_options
            json.dump(root, f, indent=4)

    try:
        frame_index = 0
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
                                faces_in_frame = faces[frame.stream.index]
                                faces_in_frame = faces_in_frame[0][frame_index], faces_in_frame[1][frame_index] if tracking_options else None
                                frame_index += 1

                                # Process (if necessary)
                                frame = _process_video_frame(frame, faces_in_frame, mode, mode_options)

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
        model=DEFAULT_MODEL,
        model_options={},
        tracking_options={},
        mode=DEFAULT_MODE,
        mode_options={},
        image_options={},
        video_options={},
        thread_options={},
        on_done=None,
        on_error=None,
        stop: TerminatingCookie = None,
        total_progress=tqdm.tqdm,
        file_progress=tqdm.tqdm,
        verbose=False):

    # WARNING/libav.swscaler           (66753 ): deprecated pixel format used, make sure you did set range correctly
    logging_format = "%(levelname)-7s/%(name)-24s (%(process)-6d): %(message)s"
    if verbose:
        av.logging.set_level(av.logging.VERBOSE)
        logging.basicConfig(format=logging_format, level=logging.DEBUG)
    else:
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
                    _faceblur_image(input_filename, output, model, model_options, mode, mode_options, **image_options)
                else:
                    # Assume video
                    _faceblur_video(input_filename, output, model, model_options, tracking_options, mode, mode_options,
                                    file_progress, stop,
                                    **video_options,
                                    **thread_options)

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
