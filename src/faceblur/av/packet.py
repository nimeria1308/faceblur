# Copyright (C) 2025, Simona Dimitrova

import av

import faceblur.av.stream as fb_stream


class Packet():
    def __init__(self, packet: av.Packet, stream: fb_stream.InputStream):
        self._packet = packet
        self._stream = stream

    @property
    def dts(self):
        return self._packet.dts

    @property
    def pts(self):
        return self._packet.pts

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, stream):
        self._stream = stream
        self._packet.stream = stream._stream

    def decode(self):
        for frame in self._packet.decode():
            yield frame
