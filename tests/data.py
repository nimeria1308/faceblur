# Copyright (C) 2025, Simona Dimitrova

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.path import is_filename_from_ext_group
from faceblur.path import walk_files
from pymediainfo import MediaInfo
from subprocess import check_call

FFMPEG_FATE_SUITE_URL = "rsync://fate-suite.ffmpeg.org/fate-suite/"

FFMPEG_FATE_SUITE = "testdata"

FFMPEG_FATE_SKIPPED = [
    # PermissionError on demux()
    "iv8/zzz-partial.mpg",

    # PermissionError on decode()
    "wmv8/wmv_drm.wmv",

    # UnknownError on decode()
    "spv1/16bpp_555.avi",
    "spv1/32bpp.avi",
    "tscc/2004-12-17-uebung9-partial.avi",
    "tdsc/tdsc.asf",

    # PatchWelcomeError (Not yet implemented in FFmpeg, patches welcome) on decode()
    "vp6/interlaced32x32.avi",
    "vp6/interlaced32x64.avi",
]

# Make sure it is rsynced
# Check fate-rsync target in FFmpeg/tests/Makefile
check_call([
    "rsync",
    "-vrltLW", "--timeout=60",
    FFMPEG_FATE_SUITE_URL, FFMPEG_FATE_SUITE
])

FFMPEG_FATE_FILES = walk_files(FFMPEG_FATE_SUITE, FFMPEG_FATE_SKIPPED)

# Select only relevant files
IMAGE_FILES = [f for f in FFMPEG_FATE_FILES if is_filename_from_ext_group(f, IMAGE_EXTENSIONS)]

# Only files with supported extensions, and only containers that actually have video streams
VIDEO_FILES = [f for f in FFMPEG_FATE_FILES
               if is_filename_from_ext_group(f, CONTAINER_EXENTSIONS) and MediaInfo.parse(f).video_tracks]
