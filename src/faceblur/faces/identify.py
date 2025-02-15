# Copyright (C) 2025, Simona Dimitrova

import av.error
import tqdm

import faceblur.av.container as fb_container
import faceblur.faces.dlib as fb_dlib
import faceblur.faces.mediapipe as fb_mediapipe
import faceblur.faces.model as fb_model
import faceblur.threading as fb_threading

from PIL.Image import Image


DETECTORS = {
    fb_model.Model.MEDIA_PIPE_SHORT_RANGE: lambda options: fb_mediapipe.MediaPipeDetector(0, **options),
    fb_model.Model.MEDIA_PIPE_FULL_RANGE: lambda options: fb_mediapipe.MediaPipeDetector(1, **options),
    fb_model.Model.DLIB_HOG: lambda options: fb_dlib.DLibDetector("hog", **options),
    fb_model.Model.DLIB_CNN: lambda options: fb_dlib.DLibDetector("cnn", **options),
}


def identify_faces_from_video(container: fb_container.InputContainer,
                              model=fb_model.DEFAULT,
                              model_options={},
                              progress=tqdm.tqdm,
                              stop: fb_threading.TerminatingCookie = None):

    # Collect FPS data for each stream (needed for calculating tracking duration in seconds)
    frame_rate = {stream: stream._stream.guessed_rate for stream in container.streams if stream.type == "video"}

    # A detector for each face
    detectors = {stream: DETECTORS[model](model_options) for stream in container.streams if stream.type == "video"}

    try:
        with progress(desc="Detecting faces", total=container.video.frames, unit=" frames", leave=False) as progress:
            for packet in container.demux():
                if packet.stream.type == "video":
                    detector = detectors[packet.stream]
                    try:
                        for frame in packet.decode():
                            if stop:
                                stop.throwIfTerminated()

                            detector.detect(frame.to_image())

                            # Update progress if this is the main video stream,
                            # we are using the main video stream to keep track
                            if packet.stream == container.video:
                                progress.update()
                    except av.error.InvalidDataError as e:
                        # Drop the packet
                        pass

        # now get the faces from all streams/detectors
        faces = {stream.index: (detector.faces, detector.encodings,
                                frame_rate[stream]) for stream, detector in detectors.items()}

    finally:
        for detector in detectors.values():
            detector.close()

    return faces


def identify_faces_from_image(image: Image,
                              model=fb_model.DEFAULT,
                              model_options={}):

    with DETECTORS[model](model_options) as detector:
        detector.detect(image)
        return detector.faces[0]
