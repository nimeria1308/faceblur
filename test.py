#!/usr/bin/env python3

# Copyright (C) 2025, Simona Dimitrova

import av
import logging
import pytest
import sys

sys.path.append("src")

# WARNING/libav.swscaler           (66753 ): deprecated pixel format used, make sure you did set range correctly
logging_format = "%(levelname)-7s/%(name)-24s (%(process)-6d): %(message)s"
logging.basicConfig(format=logging_format, level=logging.DEBUG)
av.logging.set_level(av.logging.VERBOSE)

if __name__ == "__main__":
    sys.exit(pytest.main(["tests"] + sys.argv[1:]))
