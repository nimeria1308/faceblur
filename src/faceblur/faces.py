# Copyright (C) 2025, Simona Dimitrova

import concurrent.futures as cf
import face_recognition
import math
import numpy as np
import os

from faceblur.av.container import InputContainer
from PIL.Image import Image


MAX_IMAGE_SIDE = 1920


def _find_divisor(width, height, max_side):
    side = max(width, height)
    return math.ceil(side / max_side)


def identify_faces_from_image(image: Image, max_side=MAX_IMAGE_SIDE):
    divisor = _find_divisor(image.width, image.height, max_side)
    if divisor > 1:
        # Needs to be scaled down
        image = image.resize((image.width // divisor, image.height // divisor))

    return face_recognition.face_locations(np.array(image))


def _process_frame(image, index, frame, max_side):
    return index, frame, identify_faces_from_image(image, max_side)


def identify_faces_from_video(container: InputContainer, threads=os.cpu_count(), max_side=MAX_IMAGE_SIDE):
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

                    # find the faces in this frame
                    futures.add(
                        executor.submit(
                            _process_frame,
                            frame.to_image(),
                            packet.stream.index, current_frame, max_side))

                    # stream_faces[current_frame] = faces_in_frame
                    current_frame += 1

                # update the lastly processed frame
                frames[packet.stream.index] = current_frame

        _process_done(futures)

    return {index: [faces[frame] for frame in sorted(faces)] for index, faces in faces.items()}
