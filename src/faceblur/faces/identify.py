# Copyright (C) 2025, Simona Dimitrova

import concurrent.futures as cf
import face_recognition
import math
import numpy as np
import os
import tqdm

from faceblur.av.container import InputContainer
from PIL.Image import Image


IDENTIFY_IMAGE_SIZE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def identify_faces_from_image(image: Image, image_size=IDENTIFY_IMAGE_SIZE, fast=True):
    divisor = _find_divisor(image.width, image.height, image_size)
    if divisor > 1:
        # Needs to be scaled down
        image = image.resize((image.width // divisor, image.height // divisor))

    faces = face_recognition.face_locations(np.array(image), model="hog" if fast else "cnn")

    # Adjust faces if the image was scaled down
    if divisor > 1:
        faces = [
            tuple(point * divisor for point in face)
            for face in faces
        ]

    return faces


def _interpolate_faces(faces):
    # TODO: Need to fill in and interpolate missed faces.
    #
    return faces


def _process_frame(image, index, frame, image_size, fast):
    return index, frame, identify_faces_from_image(image, image_size, fast)


def identify_faces_from_video(
        container: InputContainer, threads=os.cpu_count(),
        image_size=IDENTIFY_IMAGE_SIZE, fast=True, progress=tqdm.tqdm):

    faces = {stream.index: {} for stream in container.streams if stream.type == "video"}
    frames = {index: 0 for index in faces.keys()}
    futures = set()

    def _process_done(done: set[cf.Future]):
        for future in done:
            stream_index, current_frame, faces_in_frame = future.result()
            stream_faces = faces[stream_index]
            stream_faces[current_frame] = faces_in_frame

        nonlocal futures
        futures -= done

    with progress(desc="Detecting faces", total=container.video.frames, unit="frames", leave=False) as progress:
        with cf.ProcessPoolExecutor(max_workers=threads) as executor:
            for packet in container.demux():
                if packet.stream.type == "video":
                    # list with faces for each frame for this video stream
                    current_frame = frames[packet.stream.index]

                    for frame in packet.decode():
                        # Do not pile up more work until there are enough free workers
                        while len(futures) >= threads:
                            # wait for one
                            _process_done(cf.wait(futures, return_when=cf.FIRST_COMPLETED).done)

                        if packet.stream == container.video:
                            progress.update()

                        # find the faces in this frame
                        futures.add(
                            executor.submit(
                                _process_frame,
                                frame.to_image(),
                                packet.stream.index, current_frame, image_size, fast))

                        # stream_faces[current_frame] = faces_in_frame
                        current_frame += 1

                    # update the lastly processed frame
                    frames[packet.stream.index] = current_frame

            _process_done(futures)

    return {index: _interpolate_faces([faces[frame] for frame in sorted(faces)]) for index, faces in faces.items()}
