# Copyright (C) 2025, Simona Dimitrova

import av.frame

from faceblur.av.stream import Stream


class Frame:
    def __init__(self, frame: av.frame.Frame, stream: Stream = None):
        self._frame = frame
        self._stream = stream

    @property
    def dts(self):
        return self._frame.dts

    @dts.setter
    def dts(self, dts):
        self._frame.dts = dts

    @property
    def pts(self):
        return self._frame.pts

    @pts.setter
    def pts(self, pts):
        self._frame.pts = pts

    @property
    def time_base(self):
        return self._frame.time_base

    @time_base.setter
    def time_base(self, time_base):
        self._frame.time_base = time_base

    @property
    def time(self):
        return self._frame.time

    @property
    def stream(self):
        return self._stream

    def copy_metadata(self, other):
        self._frame.dts = other._frame.dts
        self._frame.pts = other._frame.pts
        self._frame.time_base = other._frame.time_base
        self._stream = other._stream
