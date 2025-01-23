#!/usr/bin/env python3

# Copyright (C) 2025, Simona Dimitrova

import logging
import pytest
import sys

sys.path.append("src")

if __name__ == "__main__":
    sys.exit(pytest.main(["tests"] + sys.argv[1:]))
