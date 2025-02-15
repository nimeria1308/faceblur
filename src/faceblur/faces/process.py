# Copyright (C) 2025, Simona Dimitrova

import faceblur.faces.track as fb_track
import faceblur.faces.interpolate as fb_interpolate


MIN_FACE_DURATION = 1
TRACKING_DURATION = 1


def process_faces_in_frames(frames, encodings, frame_rate, score,
                            min_face_duration=MIN_FACE_DURATION,
                            tracking_duration=TRACKING_DURATION):

    if score is None:
        # Set default score if not provided
        score = fb_track.ENCODING_MAX_DISTANCE if encodings else fb_track.IOU_MIN_OVERLAP

    # Bin faces into tracks in order to filter false positives and interpolate false negatives
    if encodings:
        # Use advanced tracking through face encodings (supported by model)
        tracks, frames_with_tracks = fb_track.track_faces_encodings(frames, encodings, score)
    else:
        # Use simple tracking via IoU
        tracks, frames_with_tracks = fb_track.track_faces_iou(frames, score)

    # Filter out false positives (i.e. faces from unpopular tracks)
    min_track_size = int(min_face_duration * frame_rate)
    frames_with_tracks = fb_track.filter_frames_with_tracks(tracks, frames_with_tracks, min_track_size)

    # Interpolate false negatives (i.e. faces missing from some frames)
    tracking_max_frame_distance = int(tracking_duration * frame_rate)
    frames_interpolated = fb_interpolate.interpolate_faces(tracks, frames_with_tracks, tracking_max_frame_distance)

    return frames, frames_interpolated
