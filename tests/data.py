# Copyright (C) 2025, Simona Dimitrova

import os

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.path import is_filename_from_ext_group
from faceblur.path import walk_files
from pymediainfo import MediaInfo
from shutil import rmtree
from subprocess import check_call

TEST_DATA_FOLDER = "testdata"

FFMPEG_FATE_SUITE_URL = "rsync://fate-suite.ffmpeg.org/fate-suite/"

FFMPEG_FATE_SUITE_FOLDER = os.path.join(TEST_DATA_FOLDER, "fate")

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

    # UnknownCodecError on encode()
    "canopus/hq25i.avi",
    "canopus/hqx422a.avi",
    "canopus/hqx422.avi",
    "canopus/hq.avi",
    "canopus/hqa.avi",
    "wc4-xan/wc4trailer-partial.avi",
    "wc4-xan/wc4_2.avi",
    "aasc/AASC-1.5MB.AVI",
    "vixl/pig-vixl.avi",
    "012v/sample.avi",
    "avid/avid_ntsc_interlaced.avi",
    "quickdraw/Airplane.mov",
    "CSCD/sample_video.avi",
    "vqc/samp1.avi",
    "ulti/hit12w.avi",
    "qpeg/Clock.avi",
    "msmpeg4v1/mpg4.avi",
    "spv1/bunny.avi",
    "spv1/24bpp.avi",
    "mss1/screen_codec.wmv",
    "g2m/g2m3.asf",
    "g2m/g2m2.asf",
    "g2m/g2m4.asf",
    "hap/HapAlphaOnly_snappy1chunk_127x71.mov",
    "hap/HAPQA_Snappy_16chunk_127x1.mov",
    "hap/HAPQA_NoSnappy_127x1.mov",
    "hap/hapy.mov",
    "hap/HapAlphaOnly_NoSnappy_128x72.mov",
    "hap/hap1.mov",
    "hap/hap5.mov",
    "hap/HAPQA_Snappy_1chunk_127x1.mov",
    "hap/hapy-12-chunks.mov",
    "VMnc/VS2k5DebugDemo-01-partial.avi",
    "VMnc/test.avi",
    "tscc/tsc2_16bpp.avi",
    "tscc/oneminute.avi",
    "KMVC/LOGO1.AVI",
    "duck/sonic3dblast_intro-partial.avi",
    "duck/tr20_low.avi",
    "duck/tr20_mid.avi",
    "duck/vf2end-partial.avi",
    "duck/tr20_high.avi",
    "duck/tm20.avi",
    "svq3/Vertical400kbit.sorenson3.mov",
    "svq3/svq3_decoding_regression.mov",
    "svq3/svq3_watermark.mov",
    "fraps/sample-v1.avi",
    "fraps/psclient-partial.avi",
    "fraps/Griffin_Ragdoll01-partial.avi",
    "fraps/fraps-v5-bouncing-balls-partial.avi",
    "fraps/test3-nosound-partial.avi",
    "fraps/WoW_2006-11-03_14-58-17-19-nosound-partial.avi",
    "cyuv/cyuv.avi",
    "vble/flowers-partial-2MB.avi",
    "rt21/ISKATE.AVI",
    "rt21/VPAR0026.AVI",
    "kega/kgv1.avi",
    "dxtory/dxtory_mic.avi",
    "iv50/Educ_Movie_DeadlyForce.avi",
    "iv32/OPENINGH.avi",
    "iv32/cubes.mov",
    "vcr1/VCR1test.avi",
    "rscc/8bpp.avi",
    "rscc/16bpp_555.avi",
    "rscc/24bpp.avi",
    "rscc/pip.avi",
    "rscc/32bpp.avi",
    "wnv1/wnv1-codec.avi",
    "auravision/SOUVIDEO.AVI",
    "8bps/full9iron-partial.mov",
    "iv41/indeo41-partial.avi",
    "pixlet/pixlet_rgb.mov",
    "fic/fic-partial-2MB.avi",
    "mjpegb/mjpegb_part.mov",
    "sp5x/sp5x_problem.avi",
    "mss2/msscreencodec.wmv",
    "mss2/mss2_2.wmv",
    "mss2/rlepal.wmv",
    "mss2/rlepals.wmv",
    "mss2/rle555.wmv",
    "mss2/rle555s.wmv",
    "lcl/mszh-1frame.avi",
    "cavs/bunny.mp4",
    "cavs/cavs.mpg",
    "zerocodec/sample-zeco.avi",
    "lagarith/lag-yv12.avi",
    "lagarith/lag-yuy2.avi",
    "lagarith/lagarith-1.3.27-black-frames-and-off-by-ones.avi",
    "lagarith/lag-rgb32.avi",
    "lagarith/lag-rgb24.avi",
    "lagarith/lagarith-red.avi",
    "lscr/lscr_compr9_short.avi",
    "vp3/coeff_level64.mkv",
    "vp3/vp31.avi",
    "vp4/KTkvw8dg1J8.avi",
    "flash-vp6/300x180-Scr-f8-056alpha.mov",
    "cllc/sample-cllc-rgb.avi",
    "cllc/sample-cllc-yuy2-noblock.avi",
    "cllc/sample-cllc-argb.avi",
    "vp5/potter512-400-partial.avi",
    "fmvc/fmvcVirtualDub_small.avi",
    "fmvc/6-methyl-5-hepten-2-one-CC-db_small.avi",
    "frwu/frwu.avi",
    "loco/pig-loco-rgb.avi",
    "loco/pig-loco-0.avi",
    "aic/small_apple_intermediate_codec.mov",
    "aic/aic_odd_dimensions.mov",

    # ValueError: 'h263' format does not support 'mpeg4' codec on encode()
    "mpeg4/resize_up-up.h263",
    "mpeg4/resize_down-up.h263",
    "mpeg4/resize_down-down.h263",
    "mpeg4/resize_up-down.h263",
    "mpeg4/xvid_vlc_trac7411.h263",

    # PermissionError on encode()
    "mpeg4/packed_bframes.avi",

    # ValueError (Invalid argument, errno 22) in encode()
    "cram/toon.avi",
    "cram/skating.avi",
    "vp9-test-vectors/vp92-2-20-10bit-yuv420.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv440.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv440.webm",
    "vp9-test-vectors/vp92-2-20-12bit-yuv420.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv444.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv422.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv422.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv444.webm",
    "dxv/dxv3-hqna.mov",
    "dxv/dxv3-hqwa.mov",
    "dnxhd/dnxhr_cid1271_12bit.mov",
    "dnxhd/dnxhr444_cid1270.mov",
    "h264/ref_10.avi",
    "h264/reinit-small_420_9-to-small_420_8.h264",
    "h264/reinit-small_422_9-to-small_420_9.h264",
    "h264/unescaped_extradata.mp4",
    "h264-444/444_9bit_cavlc.h264",
    "h264-444/444_9bit_cabac.h264",
    "mkv/hdr10_plus_vp9_sample.webm",
    "h264-high-depth/normal-9.h264",
    "qtrle/Animation-Monochrome.mov",
    "qtrle/Animation-16Greys.mov",
    "qtrle/criticalpath-credits.mov",
    "qtrle/mr-cork-rle.mov",
    "qtrle/Animation-4Greys.mov",
    "prores/Sequence_1-Apple_ProRes_with_Alpha.mov",
    "prores/prores4444_with_transparency.mov",
    "cvid/pcitva15.avi",
    "cvid/laracroft-cinepak-partial.avi",
    "cvid/catfight-cvid-pal8-partial.mov",
]


def _prepare_ffmpeg_fate_suite():
    # Make sure FFMPEG fate suite it is rsynced
    # Check fate-rsync target in FFmpeg/tests/Makefile
    check_call([
        "rsync",
        "-vrltLW", "--timeout=60",
        FFMPEG_FATE_SUITE_URL, FFMPEG_FATE_SUITE_FOLDER
    ])


def _git_command(folder, *commands):
    check_call([
        "git", "-C", folder,
    ] + list(commands))


def _git_fetch_latest(folder):
    _git_command(folder, "fetch")
    _git_command(folder, "checkout", "origin/main")
    _git_command(folder, "reset", "--hard", "origin/main")
    _git_command(folder, "clean", "-fdx")


def _git_prepare(repo, folder):
    if os.path.isdir(folder):
        try:
            _git_fetch_latest(folder)
            # Fatch was OK, do not clone
            return
        except:
            # fall-back to clean clone
            rmtree(folder, ignore_errors=True)

    # Clone
    check_call(["git", "clone", repo, folder])


def _prepare_files():
    os.makedirs(TEST_DATA_FOLDER, exist_ok=True)
    _prepare_ffmpeg_fate_suite()


_prepare_files()

FFMPEG_FATE_FILES = walk_files(FFMPEG_FATE_SUITE_FOLDER, FFMPEG_FATE_SKIPPED)

# Select only relevant files
IMAGE_FILES = [f for f in FFMPEG_FATE_FILES if is_filename_from_ext_group(f, IMAGE_EXTENSIONS)]

# Only files with supported extensions, and only containers that actually have video streams
VIDEO_FILES = [f for f in FFMPEG_FATE_FILES
               if is_filename_from_ext_group(f, CONTAINER_EXENTSIONS) and MediaInfo.parse(f).video_tracks]
