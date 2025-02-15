# Copyright (C) 2025, Simona Dimitrova

import av
import json
import logging
import os
import tqdm

import faceblur.av.container as fb_container
import faceblur.av.video as fb_video
import faceblur.faces.identify as fb_identify
import faceblur.faces.debug as fb_debug
import faceblur.faces.obfuscate as fb_obfuscate
import faceblur.faces.process as fb_process
import faceblur.faces.mode as fb_mode
import faceblur.faces.model as fb_model
import faceblur.image as fb_image
import faceblur.path as fb_path
import faceblur.threading as fb_threading


DEFAULT_OUT = "obfuscated"

SUPPORTED_EXTENSIONS = set(fb_container.EXTENSIONS + fb_image.EXTENSIONS)


def _get_filenames_file(filename, on_error):
    if not fb_path.is_filename_from_ext_group(filename, SUPPORTED_EXTENSIONS):
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
        is_image = fb_path.is_filename_from_ext_group(filename, fb_image.EXTENSIONS)
        formats = fb_image.FORMATS if is_image else fb_container.FORMATS
        filename, ext = os.path.splitext(filename)
        ext = formats[format][0]
        filename = f"{filename}.{ext}"

    return os.path.join(output, os.path.basename(filename))


def _process_video_frame(frame: fb_video.VideoFrame, faces, mode, mode_options):
    # do extra processing only if any faces were found
    if mode == fb_mode.Mode.DEBUG:
        if faces:
            # any faces
            # av.video.frame.VideoFrame -> PIL.Image
            image = frame.to_image()

            # Draw face boxes
            image = fb_debug.debug_faces(image, faces)

            # PIL.Image -> av.video.frame.VideoFrame
            frame = fb_video.VideoFrame.from_image(image, frame)

    elif mode in fb_obfuscate.MODES:
        if faces:
            # av.video.frame.VideoFrame -> PIL.Image
            image = frame.to_image()

            # Obfuscate via a rectangular gaussian blur (using processed faces)
            image = fb_obfuscate.blur_faces(mode, image, faces[1] if faces[1] is not None else faces[0], **mode_options)

            # PIL.Image -> av.video.frame.VideoFrame
            frame = fb_video.VideoFrame.from_image(image, frame)
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
    image = fb_image.image_open(input_filename)

    # Find faces
    faces = fb_identify.identify_faces_from_image(image, model, model_options=model_options)

    output_filename = _create_output(input_filename, output, format)

    if mode == fb_mode.Mode.DEBUG:
        # Save face boxes to file
        with open(f"{output_filename}.json", "w") as f:
            root = _get_debug_root(input_filename, output_filename, model, model_options, format)
            root["faces"] = [face.to_json() for face in faces]
            json.dump(root, f, indent=4)

        # Draw face boxes
        image = fb_debug.debug_faces(image, (faces, None))
    elif mode in fb_obfuscate.MODES:
        # Obfuscate via a rectangular gaussian blur
        image = fb_obfuscate.blur_faces(mode, image, faces, **mode_options)
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
        thread_type=fb_video.DEFAULT_THREAD_TYPE,
        threads=os.cpu_count()):

    # First find the faces. We can't do that on a frame-by-frame basis as it requires
    # to have the full data to interpolate missing face locations
    with fb_container.InputContainer(input_filename, thread_type, threads) as input_container:
        faces = fb_identify.identify_faces_from_video(
            input_container, model, model_options=model_options, progress=progress_type, stop=stop)

    if tracking_options:
        # Use face tracking and interpolation between frames
        # Clear false positive, fill in false negatives
        faces = {
            stream: fb_process.process_faces_in_frames(
                frames_in_stream[0],
                frames_in_stream[1],
                frames_in_stream[2],
                **tracking_options) for stream, frames_in_stream in faces.items()}
    else:
        faces = {
            stream: (faces_in_stream[0], None)
            for stream, faces_in_stream in faces.items()}

    output_filename = _create_output(input_filename, output, format)
    if mode == fb_mode.Mode.DEBUG:
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
        with fb_container.InputContainer(input_filename, thread_type, threads) as input_container:
            with fb_container.OutputContainer(output_filename, input_container, encoder) as output_container:
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


def app(
        inputs,
        output,
        model=fb_model.DEFAULT,
        model_options={},
        tracking_options={},
        mode=fb_mode.DEFAULT,
        mode_options={},
        image_options={},
        video_options={},
        thread_options={},
        on_done=None,
        on_error=None,
        stop: fb_threading.TerminatingCookie = None,
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

                if fb_path.is_filename_from_ext_group(input_filename, fb_image.EXTENSIONS):
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

            except fb_threading.TerminatedException as tex:
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
