# Copyright (C) 2025, Simona Dimitrova

import math
import mediapipe as mp
import numpy as np
import os
import tqdm

from faceblur.av.container import InputContainer
from PIL.Image import Image

mp_face_detection = mp.solutions.face_detection

IDENTIFY_IMAGE_SIZE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def _identify_faces_from_image(image: Image, face_detection, image_size=IDENTIFY_IMAGE_SIZE):
    # Cache original dimension as results are normalised
    width = image.width
    height = image.height

    divisor = _find_divisor(image.width, image.height, image_size)
    if divisor > 1:
        # Needs to be scaled down
        image = image.resize((image.width // divisor, image.height // divisor))

    faces = []
    results = face_detection.process(np.array(image))
    if results.detections:
        max_box = Box(0, width - 1, height - 1, 0)

        for detection in results.detections:
            box = detection.location_data.relative_bounding_box

            # Adjust the faces as mediapipe returns relative data
            left = int(box.xmin * width)
            top = int(box.ymin * height)
            right = int((box.xmin + box.width) * width) - 1
            bottom = int((box.ymin + box.height) * height) - 1

            # Make sure the face box is within the image as detection may return coords out of bounds
            face = Box(top, right, bottom, left).intersect(max_box)
            faces.append(face)

    return faces


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
        if intersection_bottom >= intersection_top and intersection_left <= intersection_right:
            return Box(intersection_top, intersection_right, intersection_bottom, intersection_left)
        else:
            # No intersection
            return None

    def area(self):
        return (self.bottom - self.top + 1) * (self.right - self.left + 1)

    def __repr__(self):
        return f"Box(top={self.top}, right={self.right}, bottom={self.bottom}, left={self.left})"

    def __eq__(self, other):
        return self.top == other.top and self.right == other.right and self.bottom == other.bottom and self.left == other.left


def _intersection_over_union(box1, box2):
    intersection = box1.intersect(box2)
    if not intersection:
        # Do not intersect
        return 0

    intersection_area = intersection.area()

    # area of the union
    union_area = box1.area() + box2.area() - intersection_area

    # intersection over union
    return intersection_area / union_area


def _track_faces(frames, min_score=0.5):
    tracks = []

    for frame, faces in enumerate(frames):
        for face in faces:
            # The stats
            best_track_index = -1
            best_track_score = 0

            # Check if this face matches a track
            for track_index, track in enumerate(tracks):
                # Compare against the most recent instance of the track
                score = _intersection_over_union(face, track[-1])
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


def _interpolate_faces(frames, maximum_frame_depth=30, tracking_confidence=0.05):
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
            if 1 < frame_distance < maximum_frame_depth:
                frames_to_interpolate = frame_distance - 1
                # interpolate back
                for offset, dt in enumerate(np.linspace(0, 1, frames_to_interpolate + 2)[1:-1]):
                    new_face = _interpolate_boxes(previous_face, face, dt)
                    frame_to_fix = frames[previous_frame+1+offset]
                    frame_to_fix.append(new_face)

            previous_faces[track_index] = (frame, face)

    return frames


def identify_faces_from_video(container: InputContainer, image_size=IDENTIFY_IMAGE_SIZE, progress=tqdm.tqdm):

    faces = {stream.index: [] for stream in container.streams if stream.type == "video"}

    with progress(desc="Detecting faces", total=container.video.frames, unit=" frames", leave=False) as progress:
        # TODO Use both models: 0 for selfies, 1 for moderate distance
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            for packet in container.demux():
                if packet.stream.type == "video":
                    for frame in packet.decode():
                        image = frame.to_image()
                        detected_faces = _identify_faces_from_image(image, face_detection, image_size)
                        faces[packet.stream.index].append(detected_faces)

                        if packet.stream == container.video:
                            progress.update()

    # Convert the coords to something meaningful
    return {index: _interpolate_faces(faces) for index, faces in faces.items()}
