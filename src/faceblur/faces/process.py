# Copyright (C) 2025, Simona Dimitrova

import itertools

from faceblur.faces.track import IOU_MIN_SCORE, track_faces_iou
from faceblur.faces.track import MIN_TRACK_RELATIVE_SIZE, filter_frames_with_tracks
from faceblur.faces.interpolate import interpolate_faces


def process_frames(frames, min_iou_score=IOU_MIN_SCORE, min_track_relative_size=MIN_TRACK_RELATIVE_SIZE):
    # Bin faces into tracks in order to filter false positives and interpolate false negatives
    tracks, frames_with_tracks = track_faces_iou(frames, min_iou_score)

    # Filter out false positives (i.e. faces from unpopular tracks)
    frames_with_tracks = filter_frames_with_tracks(tracks, frames_with_tracks, min_track_relative_size)

    # Interpolate false negatives (i.e. faces missing from some frames)
    frames_interpolated = interpolate_faces(tracks, frames_with_tracks)

    # Now mix them
    assert len(frames) == len(frames_interpolated)

    return list(itertools.zip_longest(frames, frames_interpolated))
