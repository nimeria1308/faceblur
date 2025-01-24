#!/usr/bin/env python3

# Copyright (C) 2025, Simona Dimitrova

import argparse
import csv
import logging
import os
import pymediainfo
import sys

# autopep8: off
sys.path.append("src")

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.path import is_filename_from_ext_group, walk_files
# autopep8: on


SUPPORTED_EXTENSIONS = set(CONTAINER_EXENTSIONS + IMAGE_EXTENSIONS)


def _set_up_logging(verbose):
    # WARNING/libav.swscaler           (66753 ): deprecated pixel format used, make sure you did set range correctly
    logging_format = "%(levelname)-7s/%(name)-24s (%(process)-6d): %(message)s"

    if verbose:
        logging.basicConfig(format=logging_format, level=logging.DEBUG)
    else:
        logging.basicConfig(format=logging_format)


def collect_infos(inputs, output=sys.stdout, verbose=False):
    _set_up_logging(verbose)

    # get files from subdirs
    files = [[i] if os.path.isfile(i) else walk_files(i) for i in inputs]
    files = [e for entry in files for e in entry]
    files = sorted(list(set(files)))

    # remove non supported
    files = [f for f in files if is_filename_from_ext_group(f, SUPPORTED_EXTENSIONS)]

    # Parse the files metadata
    infos = {f: pymediainfo.MediaInfo.parse(f) for f in files}
    infos = {f: info.video_tracks + info.image_tracks for f, info in infos.items()}

    tags = sorted(list(set([t for info in infos.values() for track in info for t in vars(track).keys()])))
    tags.remove("track_type")

    if "track_id" in tags:
        tags.remove("track_id")

    # Make sure it starts with data identifiers
    tags = ["filename", "track_id", "track_type"] + tags

    writer = csv.DictWriter(output, fieldnames=tags)
    writer.writeheader()

    for filename, tracks in infos.items():
        for track in tracks:
            track = vars(track)

            # Fill in filename
            track["filename"] = filename

            # Track ID may be missing for images, fill it in
            if "track_id" not in track:
                track["track_id"] = 0

            # Remove unnecessary lists
            for k, v in track.items():
                if isinstance(v, list):
                    track[k] = ", ".join(v)

            writer.writerow(track)


def main():
    parser = argparse.ArgumentParser(
        "Small tool used to collect metadata for a bunch of media files using PyMediaInfo.")

    parser.add_argument("inputs",
                        nargs="+",
                        help="Input file(s). May be photos or videos")

    parser.add_argument("--output", "-o",
                        default=sys.stdout,
                        type=argparse.FileType('w'),
                        help="Output file.")

    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help="Enable verbose logging from all components.")

    args = parser.parse_args()

    collect_infos(**vars(args))


if __name__ == "__main__":
    main()
