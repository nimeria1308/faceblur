# Copyright (C) 2025, Simona Dimitrova

import copy
import numpy as np

from faceblur.box import Box


DEFAULT_TRACKING_FRAME_DISTANCE = 30


def _interpolate(a, b, t):
    return a + (b - a) * t


def _interpolate_boxes(box1, box2, t):
    return Box(
        _interpolate(box1.top, box2.top, t),
        _interpolate(box1.right, box2.right, t),
        _interpolate(box1.bottom, box2.bottom, t),
        _interpolate(box1.left, box2.left, t)
    )


def interpolate_faces(tracks, frames_with_tracks, tracking_frame_distance=DEFAULT_TRACKING_FRAME_DISTANCE):
    # Make sure to make a deep copy as we are going to be modifying the lists in place
    frames = copy.deepcopy(frames_with_tracks)

    previous_faces = [
        (-1, track[0]) for track in tracks
    ]

    for frame in range(len(frames)):
        faces_in_frame = frames[frame]
        for face, track_index in faces_in_frame:
            # When was it last shown?
            previous_frame, previous_face = previous_faces[track_index]
            frame_distance = frame - previous_frame
            if 1 < frame_distance < tracking_frame_distance:
                frames_to_interpolate = frame_distance - 1

                # interpolate back
                for offset, dt in enumerate(np.linspace(0, 1, frames_to_interpolate + 2)[1:-1]):
                    new_face = _interpolate_boxes(previous_face, face, dt)
                    frame_to_fix = frames[previous_frame + 1 + offset]
                    frame_to_fix.append(new_face)

            previous_faces[track_index] = (frame, face)

        # Now fix this frame
        frames[frame] = [face for face, track_index in faces_in_frame]

    return frames
