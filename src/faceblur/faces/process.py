# Copyright (C) 2025, Simona Dimitrova

from faceblur.faces.track import track_faces_iou
from faceblur.faces.track import track_faces_encodings
from faceblur.faces.track import MIN_TRACK_RELATIVE_SIZE, filter_frames_with_tracks
from faceblur.faces.interpolate import interpolate_faces

TRACKING_DURATION = 1


def process_faces_in_frames(frames, encodings, frame_rate, score,
                            min_track_relative_size=MIN_TRACK_RELATIVE_SIZE,
                            tracking_duration=TRACKING_DURATION):

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
    tracking_max_frame_distance = int(tracking_duration * frame_rate)
    frames_interpolated = interpolate_faces(tracks, frames_with_tracks, tracking_max_frame_distance)

    return frames, frames_interpolated
