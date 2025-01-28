# Copyright (C) 2025, Simona Dimitrova


DEFAULT_IOU_MIN_SCORE = 0.05
DEFAULT_MIN_TRACK_RELATIVE_SIZE = 0.25


def track_faces_iou(frames, min_score=DEFAULT_IOU_MIN_SCORE):
    tracks = []
    frames_with_tracks = []

    for faces in frames:
        frame = []

        if faces:
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
                if best_track_score < min_score:
                    # New track
                    best_track_index = len(tracks)
                    tracks.append([face])

                tracks[best_track_index].append(face)
                frame.append((face, best_track_index))

        frames_with_tracks.append(frame)

    return tracks, frames_with_tracks


def filter_frames_with_tracks(
        tracks, frames_with_tracks,
        min_track_relative_size=DEFAULT_MIN_TRACK_RELATIVE_SIZE):

    min_track_size = int(min_track_relative_size * len(frames_with_tracks))

    return [
        [
            (face, track_index)
            for face, track_index in frame
            if len(tracks[track_index]) >= min_track_size
        ]
        for frame in frames_with_tracks
    ]
