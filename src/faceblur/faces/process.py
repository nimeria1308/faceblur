# Copyright (C) 2025, Simona Dimitrova

import itertools

from faceblur.faces.track import track_faces_iou
from faceblur.faces.track import track_faces_encodings
from faceblur.faces.track import MIN_TRACK_RELATIVE_SIZE, filter_frames_with_tracks
from faceblur.faces.interpolate import TRACKING_MAX_FRAME_DISTANCE, interpolate_faces


def process_faces_in_frames(frames, encodings, score,
                            min_track_relative_size=MIN_TRACK_RELATIVE_SIZE,
                            tracking_max_frame_distance=TRACKING_MAX_FRAME_DISTANCE):

    # Bin faces into tracks in order to filter false positives and interpolate false negatives
    if encodings:
        # Use advanced tracking through face encodings (supported by model)
        tracks, frames_with_tracks = track_faces_encodings(frames, encodings, score)
    else:
        # Use simple tracking via IoU
        tracks, frames_with_tracks = track_faces_iou(frames, score)

    # Filter out false positives (i.e. faces from unpopular tracks)
    frames_with_tracks = filter_frames_with_tracks(tracks, frames_with_tracks, min_track_relative_size)

    # Interpolate false negatives (i.e. faces missing from some frames)
    frames_interpolated = interpolate_faces(tracks, frames_with_tracks, tracking_max_frame_distance)

    # Now mix them
    assert len(frames) == len(frames_interpolated)

    return list(itertools.zip_longest(frames, frames_interpolated))
