# Copyright (C) 2025, Simona Dimitrova

import os

from faceblur.av.video import DEFAULT_THREAD_TYPE
from faceblur.faces.mode import DEFAULT as DEFAULT_MODE
from faceblur.faces.model import DEFAULT as DEFAULT_MODEL
from faceblur.faces.obfuscate import STRENGTH as DEFAULT_STRENGTH
from faceblur.faces.dlib import UPSCALE as DEFAULT_UPSCALE
from faceblur.faces.mediapipe import CONFIDENCE as DEFAULT_CONFIDENCE
from faceblur.faces.process import TRACKING_DURATION, MIN_FACE_DURATION
from faceblur.faces.track import IOU_MIN_OVERLAP, ENCODING_MAX_DISTANCE


APP = "A tool to obfuscate faces from photos and videos"

INPUTS = "Input file(s). May be photos or videos"

OUTPUT = "Output folder for the blurred files"

MODEL = f"""
Detection models:

* MEDIA_PIPE_SHORT_RANGE: Google MediaPipe, up to 2 metres;
* MEDIA_PIPE_FULL_RANGE: Google MediaPipe, up to 5 metres;
* DLIB_HOG: DLIB Hog model. Good detection quality. Supports upscaling;
* DLIB_CNN: The best DLIB model, but extremely slow.

Defaults to {DEFAULT_MODEL}
"""

MODEL_MEDIAPIPE_CONFIDENCE = f"""
Only used for MEDIA_PIPE models.

Face detection confidence. The value is in the range 0...100 percent.
Smaller values find more faces, but produce more false positives.
Higher values find less faces, but produce less false positives.

Defaults to {DEFAULT_CONFIDENCE}
"""

MODEL_DLIB_UPSCALING = f"""
Only used for DLIB models.

Input upscaling. The value is a positive integer.
Values closer to 1 find more faces, but produce more false positives.
Higher values find less faces, but produce less false positives.

Defaults to {DEFAULT_UPSCALE}
"""

TRACKING = f"""
Face tracking used to do extra processing on faces in videos. On by default.
"""

TRACKING_MINIMUM_IOU = f"""
Only used for MEDIA_PIPE models.

Uses a simple heuristic to bin faces into tracks: intersection over union.
The value represents the minimum ovelap with previous face boxes (in percent) needed to place faces in the same track.
Identical boxes produces a value of 100 percent for IoU, and boxes that do not intersect at all produce a 0 percent.
The more subsequent face boxes overlap, the higher the score.
Higher values create more unique tracks, while lower values bin more faces into the same track.

Defaults to {IOU_MIN_OVERLAP}
"""

TRACKING_MAX_FACE_ENCODING_DISTANCE = f"""
Only used for DLIB models.

Uses a more robust face tracking heuristic: distance between face encodings, i.e. how similar the faces must be (in percent).
A face encoding is generated from the found face features (e.g. nose, eyes, etc.) so that it can more robustly match faces in separate frames.
Lower values create more unique tracks, while higher values bin more faces into the same track.

Defaults to {ENCODING_MAX_DISTANCE}
"""

TRACKING_DURATION = f"""
For how many seconds to track a unique face (face track). This is the amount of time it will interpolate faces back from the moment a face is found for a particular face track.

This is used to interpolate missing faces because of false negatives, either because the model could not find a face where there was one, or because the person's face was not visible (e.g. was occluded or was looking to the side).
Higher values are able to fill big gaps for when faces have not been found, e.g. a person is looking to the side for several seconds.

Defaults to {TRACKING_DURATION}
"""

TRACKING_MIN_FACE_DURATION = f"""
What is the minimum amount of seconds for a particular unique face (face track) needed to include the face in the output of detected faces.
This is used to filter out false positives: faces that the model found but were not really faces, e.g. vegetation.

Defaults to {MIN_FACE_DURATION}
"""

MODE = f"""
Modes of operation:

* RECT_BLUR: Uses gaussian blur directly on the face rects. Does not look very nice as it produces rectangular blurred boxes.
* GRACEFUL_BLUR: Uses gaussian blur on the faces, but then applies gradual oval masks to create a more natural look.
* DEBUG: Dumps found faces into a JSON file (one for each input) and then draws the found face boxes onto output. Red for the original boxes, blue for the processed faces.

Defaults to {DEFAULT_MODE}"""

BLUR_STRENGTH = f"""
Only used for blurring modes.

Specify the strength of the obfuscation (in percent).

Defaults to {DEFAULT_STRENGTH}
"""

IMAGE_FORMAT = """
Specifies the container format for generated image files.

If not speciefied it will use the same container as each input
"""

VIDEO_FORMAT = """
Specifies the container format for generated video files.

If not speciefied it will use the same container as each input
"""

VIDEO_ENCODER = """
Specifies the encoder for video files.

If not speciefied it will use the same codec as each input video"""

THREAD_TYPE = f"PyAV decoder/encoder threading model. Defaults to {DEFAULT_THREAD_TYPE}"

THREADS = f"""
How many threads to use for face detection, video decoding/encoding.

Defaults to the number of logical cores: {os.cpu_count()}
"""

VERBOSE = """
Enable verbose logging from all components.

Warning: Enabling verbose logging from PyAV sometimes causes encoding to stall
"""
