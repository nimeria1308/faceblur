# Copyright (C) 2025, Simona Dimitrova

import av.error
import copy
import numpy as np
import tqdm

from faceblur.box import Box
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


def _track_faces(frames, min_score=0.5):
    tracks = []

    for faces in frames:
        for face in faces:
            # The stats
            best_track_index = -1
            best_track_score = 0

            # Check if this face matches a track
            for track_index, track in enumerate(tracks):
                # Compare against the most recent instance of the track
                score = face.intersection_over_union(track[-1])
                if score > best_track_score:
                    best_track_score = score
                    best_track_index = track_index

            # Did we find a track?
            if best_track_score >= min_score:
                track = tracks[best_track_index]
                track.append(face)
            else:
                # New track
                tracks.append([face])

    return tracks


def _interpolate(a, b, t):
    return a + (b - a) * t


def _interpolate_boxes(box1, box2, t):
    return Box(
        int(_interpolate(box1.top, box2.top, t)),
        int(_interpolate(box1.right, box2.right, t)),
        int(_interpolate(box1.bottom, box2.bottom, t)),
        int(_interpolate(box1.left, box2.left, t))
    )


def _interpolate_faces(frames, tracking_frame_distance, tracking_confidence):
    # Make sure to make a deep copy as we are going to be modifying the lists in place
    frames = copy.deepcopy(frames)
    tracks = _track_faces(frames, tracking_confidence)

    previous_faces = [
        (-1, track[0]) for track in tracks
    ]

    for frame, faces_in_frame in enumerate(frames):
        for face in faces_in_frame:
            # which track?
            track_index = -1
            for index, track in enumerate(tracks):
                if face in track:
                    track_index = index
                    break

            if track_index < 0:
                raise Exception(f"Could not find track for face {face}")

            # When was it last shown?
            previous_frame, previous_face = previous_faces[track_index]
            frame_distance = frame - previous_frame
            if 1 < frame_distance < tracking_frame_distance:
                frames_to_interpolate = frame_distance - 1
                # interpolate back
                for offset, dt in enumerate(np.linspace(0, 1, frames_to_interpolate + 2)[1:-1]):
                    new_face = _interpolate_boxes(previous_face, face, dt)
                    frame_to_fix = frames[previous_frame+1+offset]
                    frame_to_fix.append(new_face)

            previous_faces[track_index] = (frame, face)

    return frames


def identify_faces_from_video(container: InputContainer,
                              model=DEFAULT_MODEL,
                              model_options={},
                              tracking_frame_distance=30,
                              tracking_confidence=0.05,
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
        faces = {stream.index: detector.faces for stream, detector in detectors.items()}

    finally:
        for detector in detectors.values():
            detector.close()

    # Interpolate temporaly missing faces
    if tracking_confidence:
        faces = {index:
                 _interpolate_faces(faces, tracking_frame_distance, tracking_confidence)
                 for index, faces in faces.items()}

    return faces


def identify_faces_from_image(image: Image,
                              model=DEFAULT_MODEL,
                              model_options={}):

    with DETECTORS[model](model_options) as detector:
        return detector.detect(image)
