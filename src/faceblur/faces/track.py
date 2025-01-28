# Copyright (C) 2025, Simona Dimitrova

import face_recognition

IOU_MIN_SCORE = 0.05
MIN_TRACK_RELATIVE_SIZE = 0.25
ENCODING_MAX_DISTANCE = 0.6


def track_faces_iou(frames, min_score=IOU_MIN_SCORE):
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


def track_faces_encodings(frames, encodings_for_frames, encoding_max_distance=ENCODING_MAX_DISTANCE):
    tracks = []
    frames_with_tracks = []

    assert len(frames) == len(encodings_for_frames)

    for frame_index in range(len(frames)):
        faces = frames[frame_index]
        encodings = encodings_for_frames[frame_index]

        frame = []

        if faces:
            tracked_encodings = [track[-1][1] for track in tracks]

            for index in range(len(faces)):
                face = faces[index]
                encoding = encodings[index]

                distances = face_recognition.face_distance(tracked_encodings, encoding)
                distances = [(x, d) for x, d in enumerate(distances)]
                distances = sorted(distances, key=lambda d: d[1])

                if not distances or distances[0][1] > encoding_max_distance:
                    # Either nothing to compare against (new), or too different
                    # New track
                    track_index = len(tracks)
                    tracks.append([])
                else:
                    track_index = distances[0][0]

                tracks[track_index].append((face, encoding))
                frame.append((face, track_index))

        frames_with_tracks.append(frame)

    # Remove the face encodings from the tracks
    tracks = [[t[0] for t in track] for track in tracks]

    return tracks, frames_with_tracks


def filter_frames_with_tracks(
        tracks, frames_with_tracks,
        min_track_relative_size=MIN_TRACK_RELATIVE_SIZE):

    min_track_size = int(min_track_relative_size * len(frames_with_tracks))

    return [
        [
            (face, track_index)
            for face, track_index in frame
            if len(tracks[track_index]) >= min_track_size
        ]
        for frame in frames_with_tracks
    ]
