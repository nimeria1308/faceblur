# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os

from faceblur.app import DEFAULT_OUT
from faceblur.app import faceblur
from faceblur.av.container import FORMATS as CONTAINER_FORMATS
from faceblur.av.video import ENCODERS, THREAD_TYPES, DEFAULT_THREAD_TYPE
from faceblur.faces.obfuscate import MODES as BLUR_MODES
from faceblur.faces.obfuscate import STRENGTH as DEFAULT_STRENGTH
from faceblur.faces.dlib import MODELS as DLIB_MODELS
from faceblur.faces.mediapipe import MODELS as MP_MODELS
from faceblur.faces.mode import Mode, DEFAULT as DEFAULT_MODE
from faceblur.faces.model import Model, DEFAULT as DEFAULT_MODEL
from faceblur.help import APP as APP_HELP
from faceblur.help import INPUTS as INPUTS_HELP
from faceblur.help import OUTPUT as OUTPUT_HELP
from faceblur.help import MODEL as MODEL_HELP
from faceblur.help import MODEL_MEDIAPIPE_CONFIDENCE as CONFIDENCE_HELP
from faceblur.help import MODEL_DLIB_UPSCALING as UPSCALING_HELP
from faceblur.help import TRACKING_MINIMUM_IOU as IOU_HELP
from faceblur.help import TRACKING_MAX_FACE_ENCODING_DISTANCE as ENCODING_HELP
from faceblur.help import TRACKING_DURATION as TRACKING_DURATION_HELP
from faceblur.help import TRACKING_MIN_FACE_DURATION as MIN_FACE_DURATION_HELP
from faceblur.help import MODE as MODE_HELP
from faceblur.help import BLUR_STRENGTH as STRENGTH_HELP
from faceblur.help import IMAGE_FORMAT as IMAGE_FORMAT_HELP
from faceblur.help import VIDEO_FORMAT as VIDEO_FORMAT_HELP
from faceblur.help import VIDEO_ENCODER as VIDEO_ENCODER_HELP
from faceblur.help import THREAD_TYPE as THREAD_TYPE_HELP
from faceblur.help import THREADS as THREADS_HELP
from faceblur.help import VERBOSE as VERBOSE_HELP
from faceblur.image import FORMATS as IMAGE_FORMATS

av.logging.set_level(av.logging.ERROR)


def main():
    parser = argparse.ArgumentParser(
        description=APP_HELP
    )

    parser.add_argument("inputs",
                        nargs="+",
                        help=INPUTS_HELP)

    parser.add_argument("--output", "-o",
                        default=DEFAULT_OUT,
                        help=f"{OUTPUT_HELP}. Defaults to {DEFAULT_OUT}.")

    parser.add_argument("--model", "-m",
                        choices=list(Model),
                        default=DEFAULT_MODEL,
                        help=MODEL_HELP)

    parser.add_argument("--model-confidence",
                        type=int,
                        help=CONFIDENCE_HELP)

    parser.add_argument("--model-upscaling",
                        type=int,
                        help=UPSCALING_HELP)

    parser.add_argument("--disable-tracking",
                        action="store_true",
                        help="Disable face tracking for videos. On by default.")

    parser.add_argument("--tracking-min-iou",
                        type=int,
                        help=IOU_HELP)

    parser.add_argument("--tracking-max-encoding-distance",
                        type=int,
                        help=ENCODING_HELP)

    parser.add_argument("--tracking-duration",
                        type=float,
                        help=TRACKING_DURATION_HELP)

    parser.add_argument("--tracking-min-face-duration",
                        type=float,
                        help=MIN_FACE_DURATION_HELP)

    parser.add_argument("--mode", "-M",
                        choices=list(Mode),
                        default=DEFAULT_MODE,
                        help=MODE_HELP)

    parser.add_argument("--strength", "-s",
                        type=int,
                        help=STRENGTH_HELP)

    parser.add_argument("--image-format", "-f",
                        choices=sorted(list(IMAGE_FORMATS.keys())),
                        help=IMAGE_FORMAT_HELP)

    parser.add_argument("--video-format", "-F",
                        choices=sorted(list(CONTAINER_FORMATS.keys())),
                        help=VIDEO_FORMAT_HELP)

    parser.add_argument("--video-encoder", "-V", choices=ENCODERS,
                        help=VIDEO_ENCODER_HELP)

    parser.add_argument("--thread-type", "-t",
                        choices=THREAD_TYPES,
                        default=DEFAULT_THREAD_TYPE,
                        help=THREAD_TYPE_HELP)

    parser.add_argument("--threads", "-j",
                        default=os.cpu_count(), type=int,
                        help=THREADS_HELP)

    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help=VERBOSE_HELP)

    args = parser.parse_args()

    # Fix the params

    # Model options
    model_options = {}

    if args.model_confidence is not None:
        if args.model in MP_MODELS:
            model_options["confidence"] = args.model_confidence
        else:
            parser.error(f"model {args.model} does not support --model-confidence")

    if args.model_upscaling is not None:
        if args.model in DLIB_MODELS:
            model_options["upscale"] = args.model_upscaling
        else:
            parser.error(f"model {args.model} does not support --model-upscaling")

    # Face tracking
    if args.disable_tracking:
        tracking_args = [
            args.tracking_min_iou,
            args.tracking_max_encoding_distance,
            args.tracking_duration,
            args.tracking_min_face_duration,
        ]

        if any(t is not None for t in tracking_args):
            parser.error(f"Providing tracking options has no effect when tracking is disabled")

        tracking_options = False
    else:
        tracking_options = {}

        if args.tracking_min_iou is not None:
            if args.model in MP_MODELS:
                tracking_options["score"] = args.tracking_min_iou
            else:
                parser.error(f"IoU tracking is not supported for model {args.model}")

        if args.tracking_max_encoding_distance is not None:
            if args.model in DLIB_MODELS:
                tracking_options["score"] = args.tracking_max_encoding_distance
            else:
                parser.error(f"Face encoding tracking is not supported for model {args.model}")

        if args.tracking_duration is not None:
            tracking_options["tracking_durtaion"] = args.tracking_duration

        if args.tracking_min_face_duration is not None:
            tracking_options["min_face_duration"] = args.tracking_min_face_duration

    # Mode
    mode_options = {}

    if args.strength is not None:
        if args.mode in BLUR_MODES:
            mode_options["strength"] = args.strength
        else:
            parser.error(f"--strength is not valid for mode {args.mode}")

    # Image options
    image = {
        "format": args.image_format,
    }

    # Video options
    video = {
        "format": args.video_format,
        "encoder": args.video_encoder,
    }

    threads = {
        "thread_type": args.thread_type,
        "threads": args.threads,
    }

    args = {
        "inputs": args.inputs,
        "output": args.output,
        "model": args.model,
        "model_options": model_options,
        "tracking_options": tracking_options,
        "mode": args.mode,
        "mode_options": mode_options,
        "image_options": image,
        "video_options": video,
        "thread_options": threads,
        "verbose": args.verbose,
    }

    faceblur(**args)


if __name__ == "__main__":
    main()
