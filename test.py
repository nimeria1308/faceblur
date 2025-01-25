#!/usr/bin/env python3

# Copyright (C) 2025, Simona Dimitrova

import av
import pytest
import sys

sys.path.append("src")

if __name__ == "__main__":
    if "--log-level=DEBUG" in sys.argv[1:]:
        # Increase verbosity for av only if asked, as some encoders get stuck
        av.logging.set_level(av.logging.VERBOSE)

    sys.exit(pytest.main(["tests"] + sys.argv[1:]))
