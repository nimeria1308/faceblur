# Copyright (C) 2025, Simona Dimitrova

from enum import StrEnum


class Mode(StrEnum):
    RECT_BLUR = "RECT_BLUR"
    DEBUG = "DEBUG"


DEFAULT = Mode.RECT_BLUR
