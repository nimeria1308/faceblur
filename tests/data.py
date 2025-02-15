# Copyright (C) 2025, Simona Dimitrova

import sys
import os

from faceblur.av.container import EXTENSIONS as CONTAINER_EXENTSIONS
from faceblur.image import EXTENSIONS as IMAGE_EXTENSIONS
from faceblur.image import FORMATS as IMAGE_FORMATS
from faceblur.path import is_filename_from_ext_group
from faceblur.path import walk_files
from pymediainfo import MediaInfo
from shutil import rmtree
from subprocess import check_call

TEST_DATA_FOLDER = "testdata"

# FFMPEG Fate suite repo and files
FFMPEG_FATE_SUITE_URL = "rsync://fate-suite.ffmpeg.org/fate-suite/"

FFMPEG_FATE_SUITE_FOLDER = os.path.join(TEST_DATA_FOLDER, "av", "fate")

FFMPEG_FATE_SKIPPED = [
    # PermissionError on demux()
    "iv8/zzz-partial.mpg",

    # PermissionError on decode()
    "wmv8/wmv_drm.wmv",

    # UnknownError on decode()
    "spv1/16bpp_555.avi",
    "spv1/32bpp.avi",
    "tdsc/tdsc.asf",
    "tscc/2004-12-17-uebung9-partial.avi",

    # PatchWelcomeError (Not yet implemented in FFmpeg, patches welcome) on decode()
    "vp6/interlaced32x32.avi",
    "vp6/interlaced32x64.avi",

    # UnknownCodecError on encode()
    "012v/sample.avi",
    "8bps/full9iron-partial.mov",
    "aasc/AASC-1.5MB.AVI",
    "aic/aic_odd_dimensions.mov",
    "aic/small_apple_intermediate_codec.mov",
    "auravision/SOUVIDEO.AVI",
    "avid/avid_ntsc_interlaced.avi",
    "canopus/hq.avi",
    "canopus/hq25i.avi",
    "canopus/hqa.avi",
    "canopus/hqx422.avi",
    "canopus/hqx422a.avi",
    "cavs/bunny.mp4",
    "cavs/cavs.mpg",
    "cllc/sample-cllc-argb.avi",
    "cllc/sample-cllc-rgb.avi",
    "cllc/sample-cllc-yuy2-noblock.avi",
    "CSCD/sample_video.avi",
    "cyuv/cyuv.avi",
    "duck/sonic3dblast_intro-partial.avi",
    "duck/tm20.avi",
    "duck/tr20_high.avi",
    "duck/tr20_low.avi",
    "duck/tr20_mid.avi",
    "duck/vf2end-partial.avi",
    "dxtory/dxtory_mic.avi",
    "fic/fic-partial-2MB.avi",
    "flash-vp6/300x180-Scr-f8-056alpha.mov",
    "fmvc/6-methyl-5-hepten-2-one-CC-db_small.avi",
    "fmvc/fmvcVirtualDub_small.avi",
    "fraps/fraps-v5-bouncing-balls-partial.avi",
    "fraps/Griffin_Ragdoll01-partial.avi",
    "fraps/psclient-partial.avi",
    "fraps/sample-v1.avi",
    "fraps/test3-nosound-partial.avi",
    "fraps/WoW_2006-11-03_14-58-17-19-nosound-partial.avi",
    "frwu/frwu.avi",
    "g2m/g2m2.asf",
    "g2m/g2m3.asf",
    "g2m/g2m4.asf",
    "hap/hap1.mov",
    "hap/hap5.mov",
    "hap/HapAlphaOnly_NoSnappy_128x72.mov",
    "hap/HapAlphaOnly_snappy1chunk_127x71.mov",
    "hap/HAPQA_NoSnappy_127x1.mov",
    "hap/HAPQA_Snappy_16chunk_127x1.mov",
    "hap/HAPQA_Snappy_1chunk_127x1.mov",
    "hap/hapy-12-chunks.mov",
    "hap/hapy.mov",
    "iv32/cubes.mov",
    "iv32/OPENINGH.avi",
    "iv41/indeo41-partial.avi",
    "iv50/Educ_Movie_DeadlyForce.avi",
    "kega/kgv1.avi",
    "KMVC/LOGO1.AVI",
    "lagarith/lag-rgb24.avi",
    "lagarith/lag-rgb32.avi",
    "lagarith/lag-yuy2.avi",
    "lagarith/lag-yv12.avi",
    "lagarith/lagarith-1.3.27-black-frames-and-off-by-ones.avi",
    "lagarith/lagarith-red.avi",
    "lcl/mszh-1frame.avi",
    "loco/pig-loco-0.avi",
    "loco/pig-loco-rgb.avi",
    "lscr/lscr_compr9_short.avi",
    "mjpegb/mjpegb_part.mov",
    "msmpeg4v1/mpg4.avi",
    "mss1/screen_codec.wmv",
    "mss2/mss2_2.wmv",
    "mss2/msscreencodec.wmv",
    "mss2/rle555.wmv",
    "mss2/rle555s.wmv",
    "mss2/rlepal.wmv",
    "mss2/rlepals.wmv",
    "pixlet/pixlet_rgb.mov",
    "qpeg/Clock.avi",
    "quickdraw/Airplane.mov",
    "rscc/16bpp_555.avi",
    "rscc/24bpp.avi",
    "rscc/32bpp.avi",
    "rscc/8bpp.avi",
    "rscc/pip.avi",
    "rt21/ISKATE.AVI",
    "rt21/VPAR0026.AVI",
    "sp5x/sp5x_problem.avi",
    "spv1/24bpp.avi",
    "spv1/bunny.avi",
    "svq3/svq3_decoding_regression.mov",
    "svq3/svq3_watermark.mov",
    "svq3/Vertical400kbit.sorenson3.mov",
    "tscc/oneminute.avi",
    "tscc/tsc2_16bpp.avi",
    "ulti/hit12w.avi",
    "vble/flowers-partial-2MB.avi",
    "vcr1/VCR1test.avi",
    "vixl/pig-vixl.avi",
    "VMnc/test.avi",
    "VMnc/VS2k5DebugDemo-01-partial.avi",
    "vp3/coeff_level64.mkv",
    "vp3/vp31.avi",
    "vp4/KTkvw8dg1J8.avi",
    "vp5/potter512-400-partial.avi",
    "vqc/samp1.avi",
    "wc4-xan/wc4_2.avi",
    "wc4-xan/wc4trailer-partial.avi",
    "wnv1/wnv1-codec.avi",
    "zerocodec/sample-zeco.avi",

    # ValueError: 'h263' format does not support 'mpeg4' codec on encode()
    "mpeg4/resize_down-down.h263",
    "mpeg4/resize_down-up.h263",
    "mpeg4/resize_up-down.h263",
    "mpeg4/resize_up-up.h263",
    "mpeg4/xvid_vlc_trac7411.h263",

    # PermissionError on encode()
    "mpeg4/packed_bframes.avi",

    # ValueError (Invalid argument, errno 22) in encode()
    "cram/skating.avi",
    "cram/toon.avi",
    "cvid/catfight-cvid-pal8-partial.mov",
    "cvid/laracroft-cinepak-partial.avi",
    "cvid/pcitva15.avi",
    "dnxhd/dnxhr_cid1271_12bit.mov",
    "dnxhd/dnxhr444_cid1270.mov",
    "dxv/dxv3-hqna.mov",
    "dxv/dxv3-hqwa.mov",
    "h264-444/444_9bit_cabac.h264",
    "h264-444/444_9bit_cavlc.h264",
    "h264-high-depth/normal-9.h264",
    "h264/ref_10.avi",
    "h264/reinit-small_420_9-to-small_420_8.h264",
    "h264/reinit-small_422_9-to-small_420_9.h264",
    "h264/unescaped_extradata.mp4",
    "mkv/hdr10_plus_vp9_sample.webm",
    "prores/prores4444_with_transparency.mov",
    "prores/Sequence_1-Apple_ProRes_with_Alpha.mov",
    "qtrle/Animation-16Greys.mov",
    "qtrle/Animation-4Greys.mov",
    "qtrle/Animation-Monochrome.mov",
    "qtrle/criticalpath-credits.mov",
    "qtrle/mr-cork-rle.mov",
    "vp9-test-vectors/vp92-2-20-10bit-yuv420.webm",
    "vp9-test-vectors/vp92-2-20-12bit-yuv420.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv422.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv440.webm",
    "vp9-test-vectors/vp93-2-20-10bit-yuv444.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv422.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv440.webm",
    "vp9-test-vectors/vp93-2-20-12bit-yuv444.webm",

    # PIL.UnidentifiedImageError: cannot identify image file
    "heif-conformance/C021.heic",
    "jpg/12bpp.jpg",

    # OSError: broken data stream when reading image file
    "jpeg2000/itu-iso/codestreams_profile0/p0_02.j2k",
    "jpeg2000/itu-iso/codestreams_profile1/p1_01.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_02_bset/ds0_ht_02_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_02_bset/ds0_ht_02_b12.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_03_bset/ds0_ht_03_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_03_bset/ds0_ht_03_b14.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_04_bset/ds0_ht_04_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_04_bset/ds0_ht_04_b12.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_05_bset/ds0_ht_05_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_05_bset/ds0_ht_05_b12.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_07_bset/ds0_ht_07_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_07_bset/ds0_ht_07_b15.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_07_bset/ds0_ht_07_b16.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_08_bset/ds0_ht_08_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_08_bset/ds0_ht_08_b15.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_08_bset/ds0_ht_08_b16.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_10_bset/ds0_ht_10_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_15_bset/ds0_hm_15_b8.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_15_bset/ds0_ht_15_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_15_bset/ds0_ht_15_b14.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile0/p0_16_bset/ds0_ht_16_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_01_bset/ds1_ht_01_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_01_bset/ds1_ht_01_b12.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_02_bset/ds1_ht_02_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_02_bset/ds1_ht_02_b12.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_03_bset/ds1_ht_03_b11.j2k",
    "jpeg2000/itu-iso/htj2k_bsets_profile1/p1_03_bset/ds1_ht_03_b12.j2k",
    "tiff/lzw_rgbaf32le.tif",
    "tiff/lzw_rgbf32le.tif",
    "tiff/uncompressed_rgbaf32le.tif",
    "tiff/uncompressed_rgbf32le.tif",
    "tiff/zip_rgbaf32le.tif",
    "tiff/zip_rgbf32le.tif",

    # OSError: encoder error -2 when writing image file
    "CCITT_fax/G31D.TIF",
    "CCITT_fax/G31DS.TIF",
    "CCITT_fax/G4.TIF",
    "CCITT_fax/G4S.TIF",

    # Fail after providing time_base (which is needed for proper VFR handling)
    # [mpeg2video] MPEG-1/2 does not support 90000/1 fps
    "mpeg2/mpeg2_field_encoding.ts",
    "mpeg2/matrixbench_mpeg2.lq1.mpg",
    "mpeg2/xdcam8mp2-1s_small.ts",
    "mpeg2/t.mpg",
    "ac3/mp3ac325-4864-small.ts",
    "vcr2/VCR2test.avi",
    "sub/scte20.ts",
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


def _git_fetch_latest(folder, branch):
    _git_command(folder, "fetch")
    _git_command(folder, "checkout", f"origin/{branch}")
    _git_command(folder, "reset", "--hard", f"origin/{branch}")
    _git_command(folder, "clean", "-fdx")


def _git_prepare(repo, folder, branch):
    if os.path.isdir(folder):
        try:
            _git_fetch_latest(folder, branch)
            # Fatch was OK, do not clone
            return
        except:
            # fall-back to clean clone
            rmtree(folder, ignore_errors=True)

    # Clone
    check_call(["git", "clone", repo, folder, "-b", branch])


# Pillow repo and files
PILLOW_REPO = "https://github.com/python-pillow/Pillow.git"
PILLOW_REPO_BRANCH = "main"
PILLOW_REPO_FOLDER = os.path.join(TEST_DATA_FOLDER, "av", "pillow")
PILLOW_TEST_FOLDER = os.path.join(PILLOW_REPO_FOLDER, "Tests", "images")

PILLOW_SKIPPED = [
    # PIL.UnidentifiedImageError: cannot identify image file
    "broken.png",
    "crash-2020-10-test.tif",
    "crash-63b1dffefc8c075ddc606c0a2f5fdc15ece78863.tif",
    "hopper_unknown_pixel_mode.tif",
    "invalid_header_length.jp2",
    "libtiff_segfault.tif",
    "negative_size.ppm",
    "not_enough_data.jp2",
    "oom-225817ca0f8c663be7ab4b9e717b02c661e66834.tif",
    "p_8.tga",
    "tiff_overflow_rows_per_strip.tif",
    "unbound_variable.jp2",
    "unknown_compression_method.png",
    "unknown_mode.j2k",
    "zero_height.j2k",


    # ValueError: Unable to seek to frame
    "seek_too_large.tif",

    # OSError: Truncated File Read
    "truncated_end_chunk.png",

    # OSError: -2
    "crash-0c7e0e8e11ce787078f00b5b0ca409a167f070e0.tif",
    "crash-0da013a13571cc8eb457a39fee8db18f8a3c7127.tif",
    "crash-0e16d3bfb83be87356d026d66919deaefca44dac.tif",
    "crash-1152ec2d1a1a71395b6f2ce6721c38924d025bf3.tif",
    "crash-1185209cf7655b5aed8ae5e77784dfdd18ab59e9.tif",
    "crash-338516dbd2f0e83caddb8ce256c22db3bd6dc40f.tif",
    "crash-4f085cc12ece8cde18758d42608bed6a2a2cfb1c.tif",
    "crash-74d2a78403a5a59db1fb0a2b8735ac068a75f6e3.tif",
    "crash-86214e58da443d2b80820cff9677a38a33dcbbca.tif",
    "crash-f46f5b2f43c370fe65706c11449f567ecc345e74.tif",
    "hopper_webp.tif",

    # OSError: image file is truncated (0 bytes not processed)
    "bmp/b/shortfile.bmp",
    "cross_scan_line_truncated.tga",
    "l2rgb_read.bmp",
    "truncated_jpeg.jpg",
    "ultrahdr.jpg",

    # OSError: broken data stream when reading image file
    "00r0_gray_l.jp2",
    "00r1_graya_la.jp2",
    "balloon_eciRGBv2_aware.jp2",
    "crash-4fb027452e6988530aa5dabee76eecacb3b79f8a.j2k",
    "crash-7d4c83eb92150fb8f1653a697703ae06ae7c4998.j2k",
    "crash-ccca68ff40171fdae983d924e127a721cab2bd50.j2k",
    "crash-d2c93af851d3ab9a19e34503626368b2ecde9c03.j2k",

    # OSError: unrecognized data stream contents when reading image file
    "broken_data_stream.png",

    # OSError: image file is truncated
    "truncated_image.png",

    # ValueError: Decompressed data too large for PngImagePlugin.MAX_TEXT_CHUNK
    "png_decompression_dos.png",

    # OSError: Expected to read 8 bytes but only got 0.
    "expected_to_read.jp2",

    # APNG
    "apng/chunk_no_fctl.png",
    "apng/syntax_num_frames_zero.png",

    # BMP
    "bmp/b/badbitcount.bmp",
    "bmp/b/badheadersize.bmp",
    "bmp/b/badpalettesize.bmp",
    "bmp/b/badwidth.bmp",
    "bmp/b/reallybig.bmp",
    "bmp/g/rgb32bf.bmp",
    "bmp/q/pal2.bmp",
    "bmp/q/pal8os2v2-16.bmp",
    "bmp/q/pal8oversizepal.bmp",
    "bmp/q/rgb16-231.bmp",
    "bmp/q/rgb24jpeg.bmp",
    "bmp/q/rgb24png.bmp",
    "bmp/q/rgb32-111110.bmp",
    "bmp/q/rgba16-4444.bmp",
    "bmp/q/rgba32abf.bmp",

    # OSError: encoder error -2 when writing image file
    "compression.tif",
    "g4_orientation_1.tif",
    "g4_orientation_2.tif",
    "g4_orientation_3.tif",
    "g4_orientation_4.tif",
    "g4_orientation_5.tif",
    "g4_orientation_6.tif",
    "g4_orientation_7.tif",
    "g4_orientation_8.tif",
    "g4-fillorder-test.tif",
    "g4-multi.tiff",
    "hopper_g4_500.tif",
    "hopper_g4.tif",
    "pport_g4.tif",
    "total-pages-zero.tif",

    # TypeError: cannot unpack non-iterable int object
    "1_trns.png",
    "i_trns.png",
]

# Pillow HEIF repo and files
PILLOW_HEIF_REPO = "https://github.com/bigcat88/pillow_heif.git"
PILLOW_HEIF_REPO_BRANCH = "master"
PILLOW_HEIF_REPO_FOLDER = os.path.join(TEST_DATA_FOLDER, "av", "pillow-heif")
PILLOW_HEIF_TEST_FOLDER = os.path.join(PILLOW_HEIF_REPO_FOLDER, "tests", "images", "heif")

# Intel IoT devkit sample videos for face detection
INTEL_SAMPLE_VIDEOS_REPO = "https://github.com/intel-iot-devkit/sample-videos"
INTEL_SAMPLE_VIDEOS_REPO_BRANCH = "master"
INTEL_SAMPLE_VIDEOS_REPO_FOLDER = os.path.join(TEST_DATA_FOLDER, "faces", "intel-videos")
INTEL_SAMPLE_VIDEOS_REPO_TEST_FOLDER = INTEL_SAMPLE_VIDEOS_REPO_FOLDER

# face_recognition official repo with examples
FACE_RECOGNITION_REPO = "https://github.com/ageitgey/face_recognition"
FACE_RECOGNITION_REPO_BRANCH = "master"
FACE_RECOGNITION_REPO_FOLDER = os.path.join(TEST_DATA_FOLDER, "faces", "face_recognition")
FACE_RECOGNITION_REPO_TEST_FOLDER = os.path.join(FACE_RECOGNITION_REPO_FOLDER, "examples")


def _prepare_files():
    os.makedirs(TEST_DATA_FOLDER, exist_ok=True)
    _prepare_ffmpeg_fate_suite()
    _git_prepare(PILLOW_REPO, PILLOW_REPO_FOLDER, PILLOW_REPO_BRANCH)
    _git_prepare(PILLOW_HEIF_REPO, PILLOW_HEIF_REPO_FOLDER, PILLOW_HEIF_REPO_BRANCH)
    _git_prepare(INTEL_SAMPLE_VIDEOS_REPO, INTEL_SAMPLE_VIDEOS_REPO_FOLDER, INTEL_SAMPLE_VIDEOS_REPO_BRANCH)
    _git_prepare(FACE_RECOGNITION_REPO, FACE_RECOGNITION_REPO_FOLDER, FACE_RECOGNITION_REPO_BRANCH)


_prepare_files()

FFMPEG_FATE_FILES = walk_files(FFMPEG_FATE_SUITE_FOLDER, FFMPEG_FATE_SKIPPED)

PILLOW_FILES = walk_files(PILLOW_TEST_FOLDER, PILLOW_SKIPPED)

PILLOW_HEIF_FILES = walk_files(PILLOW_HEIF_TEST_FOLDER)

INTEL_VIDEO_FILES = walk_files(INTEL_SAMPLE_VIDEOS_REPO_TEST_FOLDER)

FACE_RECOGNITION_FILES = walk_files(FACE_RECOGNITION_REPO_TEST_FOLDER)

# Select only relevant files
IMAGE_FILES = FFMPEG_FATE_FILES + PILLOW_FILES + PILLOW_HEIF_FILES
IMAGE_FILES = [f for f in IMAGE_FILES if is_filename_from_ext_group(f, IMAGE_EXTENSIONS)]


def _is_heic(filename):
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() in IMAGE_FORMATS["heif"]


if sys.platform == "darwin":
    # Skip HEIC files on MacOS as saving a HEIC file causes a segfault
    IMAGE_FILES = [f for f in IMAGE_FILES if not _is_heic(f)]

# Only files with supported extensions, and only containers that actually have video streams
VIDEO_FILES = [f for f in FFMPEG_FATE_FILES
               if is_filename_from_ext_group(f, CONTAINER_EXENTSIONS) and MediaInfo.parse(f).video_tracks]
