# Copyright (C) 2025, Simona Dimitrova

import argparse
import av
import os

import faceblur.app as fb_app
import faceblur.av.container as fb_container
import faceblur.av.video as fb_video
import faceblur.faces.dlib as fb_dlib
import faceblur.faces.mediapipe as fb_mediapipe
import faceblur.faces.mode as fb_mode
import faceblur.faces.model as fb_model
import faceblur.faces.obfuscate as fb_obfuscate
import faceblur.help as fb_help
import faceblur.image as fb_image


def main():
    parser = argparse.ArgumentParser(
        description=fb_help.APP
    )

    parser.add_argument("inputs",
                        nargs="+",
                        help=fb_help.INPUTS)

    parser.add_argument("--output", "-o",
                        default=fb_app.DEFAULT_OUT,
                        help=f"{fb_help.OUTPUT}. Defaults to {fb_app.DEFAULT_OUT}.")

    parser.add_argument("--model", "-m",
                        choices=list(fb_model.Model),
                        default=fb_model.DEFAULT,
                        help=fb_help.MODEL)

    parser.add_argument("--model-confidence",
                        type=int,
                        help=fb_help.MODEL_MEDIAPIPE_CONFIDENCE)

    parser.add_argument("--model-upscaling",
                        type=int,
                        help=fb_help.MODEL_DLIB_UPSCALING)

    parser.add_argument("--disable-tracking",
                        action="store_true",
                        help="Disable face tracking for videos. On by default.")

    parser.add_argument("--tracking-min-iou",
                        type=int,
                        help=fb_help.TRACKING_MINIMUM_IOU)

    parser.add_argument("--tracking-max-encoding-distance",
                        type=int,
                        help=fb_help.TRACKING_MAX_FACE_ENCODING_DISTANCE)

    parser.add_argument("--tracking-duration",
                        type=float,
                        help=fb_help.TRACKING_DURATION)

    parser.add_argument("--tracking-min-face-duration",
                        type=float,
                        help=fb_help.TRACKING_MIN_FACE_DURATION)

    parser.add_argument("--mode", "-M",
                        choices=list(fb_mode.Mode),
                        default=fb_mode.DEFAULT,
                        help=fb_help.MODE)

    parser.add_argument("--strength", "-s",
                        type=int,
                        help=fb_help.BLUR_STRENGTH)

    parser.add_argument("--image-format", "-f",
                        choices=sorted(list(fb_image.FORMATS.keys())),
                        help=fb_help.IMAGE_FORMAT)

    parser.add_argument("--video-format", "-F",
                        choices=sorted(list(fb_container.FORMATS.keys())),
                        help=fb_help.VIDEO_FORMAT)

    parser.add_argument("--video-encoder", "-V", choices=fb_video.ENCODERS,
                        help=fb_help.VIDEO_ENCODER)

    parser.add_argument("--thread-type", "-t",
                        choices=fb_video.THREAD_TYPES,
                        default=fb_video.DEFAULT_THREAD_TYPE,
                        help=fb_help.THREAD_TYPE)

    parser.add_argument("--threads", "-j",
                        default=os.cpu_count(), type=int,
                        help=fb_help.THREADS)

    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help=fb_help.VERBOSE)

    args = parser.parse_args()

    # Fix the params

    # Model options
    model_options = {}

    if args.model_confidence is not None:
        if args.model in fb_mediapipe.MODELS:
            model_options["confidence"] = args.model_confidence
        else:
            parser.error(f"model {args.model} does not support --model-confidence")

    if args.model_upscaling is not None:
        if args.model in fb_dlib.MODELS:
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
            if args.model in fb_mediapipe.MODELS:
                tracking_options["score"] = args.tracking_min_iou
            else:
                parser.error(f"IoU tracking is not supported for model {args.model}")

        if args.tracking_max_encoding_distance is not None:
            if args.model in fb_dlib.MODELS:
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
        if args.mode in fb_obfuscate.MODES:
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

    fb_app.app(**args)


if __name__ == "__main__":
    main()
