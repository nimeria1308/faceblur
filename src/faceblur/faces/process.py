# Copyright (C) 2025, Simona Dimitrova

from faceblur.faces.track import track_faces_iou, IOU_MIN_SCORE
from faceblur.faces.track import track_faces_encodings, ENCODING_MAX_DISTANCE
from faceblur.faces.track import filter_frames_with_tracks
from faceblur.faces.interpolate import interpolate_faces

MIN_FACE_DURATION = 1
TRACKING_DURATION = 1


def process_faces_in_frames(frames, encodings, frame_rate, score,
                            min_face_duration=MIN_FACE_DURATION,
                            tracking_duration=TRACKING_DURATION):

    # Bin faces into tracks in order to filter false positives and interpolate false negatives
    if encodings:
        # Use advanced tracking through face encodings (supported by model)
        tracks, frames_with_tracks = track_faces_encodings(frames, encodings, score)
    else:
        # Use simple tracking via IoU
        tracks, frames_with_tracks = track_faces_iou(frames, score)

    # Filter out false positives (i.e. faces from unpopular tracks)
    min_track_size = int(min_face_duration * frame_rate)
    frames_with_tracks = filter_frames_with_tracks(tracks, frames_with_tracks, min_track_size)

    # Interpolate false negatives (i.e. faces missing from some frames)
    tracking_max_frame_distance = int(tracking_duration * frame_rate)
    frames_interpolated = interpolate_faces(tracks, frames_with_tracks, tracking_max_frame_distance)

    return frames, frames_interpolated
