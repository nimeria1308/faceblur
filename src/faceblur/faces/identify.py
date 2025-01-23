# Copyright (C) 2025, Simona Dimitrova

import av.error
import math
import numpy as np
import tqdm

from enum import StrEnum
from faceblur.av.container import InputContainer
from faceblur.threading import TerminatingCookie
from mediapipe.python.solutions.face_detection import FaceDetection
from PIL.Image import Image


IDENTIFY_IMAGE_SIZE = 1920

# Google's deprecated models: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/models.md
# Updated version (short-range only): https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector


class Model(StrEnum):
    # Google, Deprecated 2023, up to 2 metres: https://storage.googleapis.com/mediapipe-assets/face_detection_short_range.tflite
    MEDIA_PIPE_SHORT_RANGE = "MEDIA_PIPE_SHORT_RANGE"

    # Google, Deprecated 2023, up to 5 metres: https://storage.googleapis.com/mediapipe-assets/face_detection_full_range.tflite
    MEDIA_PIPE_FULL_RANGE = "MEDIA_PIPE_FULL_RANGE"


class Detector:
    def __init__(self, detector):
        self._detector = detector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def detect(self, image):
        raise NotImplementedError()

    def close(self):
        self._detector.close()


class MediaPipeDetector(Detector):
    def __init__(self, model, confidence=0.5):
        super().__init__(FaceDetection(min_detection_confidence=confidence, model_selection=model))

    def detect(self, image, max_image_size):
        faces = []

        results = self._detector.process(np.asarray(image))
        if results.detections:
            max_box = Box(0, image.width - 1, image.height - 1, 0)

            for detection in results.detections:
                box = detection.location_data.relative_bounding_box

                # Adjust the faces as mediapipe returns relative data
                left = int(box.xmin * image.width)
                top = int(box.ymin * image.height)
                right = int((box.xmin + box.width) * image.width) - 1
                bottom = int((box.ymin + box.height) * image.height) - 1

                # Make sure the face box is within the image as detection may return coords out of bounds
                face = Box(top, right, bottom, left).intersect(max_box)
                faces.append(face)

        return faces


DEFAULT_MODEL = Model.MEDIA_PIPE_FULL_RANGE

DETECTORS = {
    Model.MEDIA_PIPE_SHORT_RANGE: lambda c: MediaPipeDetector(0, c),
    Model.MEDIA_PIPE_FULL_RANGE: lambda c: MediaPipeDetector(1, c),
}


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


class Box:
    def __init__(self, top, right, bottom, left):
        if left > right:
            raise ValueError(f"left={left} > right={right}")

        # The coordinate are inverted on Y
        if top > bottom:
            raise ValueError(f"top={top} > bottom={bottom}")

        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

    def intersect(self, other):
        # Calculate the intersection coordinates
        intersection_top = max(self.top, other.top)
        intersection_right = min(self.right, other.right)
        intersection_bottom = min(self.bottom, other.bottom)
        intersection_left = max(self.left, other.left)

        # Check if there is an intersection
        if intersection_top <= intersection_bottom and intersection_left <= intersection_right:
            return Box(intersection_top, intersection_right, intersection_bottom, intersection_left)
        else:
            # No intersection
            return None

    def union(self, other):
        # Calculate the union coordinates
        union_top = min(self.top, other.top)
        union_right = max(self.right, other.right)
        union_bottom = max(self.bottom, other.bottom)
        union_left = min(self.left, other.left)
        return Box(union_top, union_right, union_bottom, union_left)

    def area(self):
        return (self.bottom - self.top + 1) * (self.right - self.left + 1)

    def __repr__(self):
        return f"Box(top={self.top}, right={self.right}, bottom={self.bottom}, left={self.left})"

    def __eq__(self, other):
        return self.top == other.top and self.right == other.right and self.bottom == other.bottom and self.left == other.left

    def intersection_over_union(self, other):
        intersection = self.intersect(other)
        if not intersection:
            # Do not intersect
            return 0

        intersection_area = intersection.area()

        # area of the union
        union_area = self.area() + other.area() - intersection_area

        # intersection over union
        return intersection_area / union_area

    def to_json(self):
        return vars(self)


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
                              detection_confidence=0.5,
                              tracking_frame_distance=30,
                              tracking_confidence=0.05,
                              image_size=IDENTIFY_IMAGE_SIZE,
                              progress=tqdm.tqdm,
                              stop: TerminatingCookie = None):

    faces = {stream.index: [] for stream in container.streams if stream.type == "video"}

    with DETECTORS[model](detection_confidence) as detector:
        with progress(desc="Detecting faces", total=container.video.frames, unit=" frames", leave=False) as progress:
            for packet in container.demux():
                if packet.stream.type == "video":
                    try:
                        for frame in packet.decode():
                            if stop:
                                stop.throwIfTerminated()

                            detected_faces = detector.detect(frame.to_image(), image_size)

                            faces[packet.stream.index].append(detected_faces)

                            if packet.stream == container.video:
                                progress.update()
                    except av.error.InvalidDataError as e:
                        # Drop the packet
                        pass

    # Interpolate temporaly missing faces
    if tracking_confidence:
        faces = {index:
                 _interpolate_faces(faces, tracking_frame_distance, tracking_confidence)
                 for index, faces in faces.items()}

    return faces


def identify_faces_from_image(image: Image,
                              model=DEFAULT_MODEL,
                              detection_confidence=0.5,
                              image_size=IDENTIFY_IMAGE_SIZE):

    with DETECTORS[model](detection_confidence) as detector:
        return detector.detect(image, image_size)
