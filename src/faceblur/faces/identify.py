# Copyright (C) 2025, Simona Dimitrova

import av.error
import tqdm

from faceblur.faces.model import Model, DEFAULT as DEFAULT_MODEL
from faceblur.faces.mediapipe import MediaPipeDetector
from faceblur.faces.dlib import DLibDetector
from faceblur.av.container import InputContainer
from faceblur.threading import TerminatingCookie
from PIL.Image import Image


DETECTORS = {
    Model.MEDIA_PIPE_SHORT_RANGE: lambda options: MediaPipeDetector(0, **options),
    Model.MEDIA_PIPE_FULL_RANGE: lambda options: MediaPipeDetector(1, **options),
    Model.DLIB_HOG: lambda options: DLibDetector("hog", **options),
    Model.DLIB_CNN: lambda options: DLibDetector("cnn", **options),
}


def identify_faces_from_video(container: InputContainer,
                              model=DEFAULT_MODEL,
                              model_options={},
                              progress=tqdm.tqdm,
                              stop: TerminatingCookie = None):

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
        faces = {stream.index: (detector.faces, detector.encodings) for stream, detector in detectors.items()}

    finally:
        for detector in detectors.values():
            detector.close()

    return faces


def identify_faces_from_image(image: Image,
                              model=DEFAULT_MODEL,
                              model_options={}):

    with DETECTORS[model](model_options) as detector:
        detector.detect(image)
        return detector.faces[0]
