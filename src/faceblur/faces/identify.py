# Copyright (C) 2025, Simona Dimitrova

import concurrent.futures as cf
import face_recognition
import math
import numpy as np
import os
import tqdm

from faceblur.av.container import InputContainer
from PIL.Image import Image


IDENTIFY_IMAGE_SIZE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def identify_faces_from_image(image: Image, image_size=IDENTIFY_IMAGE_SIZE, fast=True):
    divisor = _find_divisor(image.width, image.height, image_size)
    if divisor > 1:
        # Needs to be scaled down
        image = image.resize((image.width // divisor, image.height // divisor))

    faces = face_recognition.face_locations(np.array(image), model="hog" if fast else "cnn")

    # Adjust faces if the image was scaled down
    if divisor > 1:
        faces = [
            tuple(point * divisor for point in face)
            for face in faces
        ]

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


def _process_frame(image, index, frame, image_size, fast):
    return index, frame, identify_faces_from_image(image, image_size, fast)


def identify_faces_from_video(
        container: InputContainer, threads=os.cpu_count(),
        image_size=IDENTIFY_IMAGE_SIZE, fast=True, progress=tqdm.tqdm):

    faces = {stream.index: {} for stream in container.streams if stream.type == "video"}
    frames = {index: 0 for index in faces.keys()}
    futures = set()

    def _process_done(done: set[cf.Future]):
        for future in done:
            stream_index, current_frame, faces_in_frame = future.result()
            stream_faces = faces[stream_index]
            stream_faces[current_frame] = faces_in_frame

        nonlocal futures
        futures -= done

    with progress(desc="Detecting faces", total=container.video.frames, unit=" frames", leave=False) as progress:
        with cf.ProcessPoolExecutor(max_workers=threads) as executor:
            for packet in container.demux():
                if packet.stream.type == "video":
                    # list with faces for each frame for this video stream
                    current_frame = frames[packet.stream.index]

                    for frame in packet.decode():
                        # Do not pile up more work until there are enough free workers
                        while len(futures) >= threads:
                            # wait for one
                            _process_done(cf.wait(futures, return_when=cf.FIRST_COMPLETED).done)

                        if packet.stream == container.video:
                            progress.update()

                        # find the faces in this frame
                        futures.add(
                            executor.submit(
                                _process_frame,
                                frame.to_image(),
                                packet.stream.index, current_frame, image_size, fast))

                        # stream_faces[current_frame] = faces_in_frame
                        current_frame += 1

                    # update the lastly processed frame
                    frames[packet.stream.index] = current_frame

            _process_done(futures)

    # Convert the coords to something meaningful
    return {index: _interpolate_faces([[Box(*face) for face in faces[frame]] for frame in sorted(faces)]) for index, faces in faces.items()}
