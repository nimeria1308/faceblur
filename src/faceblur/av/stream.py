# Copyright (C) 2025, Simona Dimitrova

import av
import av.container
import av.data.stream
import av.stream


class Stream():
    _stream: av.stream.Stream

    def __init__(self, stream: av.stream.Stream):
        self._stream = stream

    @property
    def type(self):
        return self._stream.type

    @property
    def index(self):
        return self._stream.index


class InputStream(Stream):
    pass


class OutputStream(Stream):
    def __init__(self, output_stream: av.stream.Stream, input_stream: InputStream = None):
        super().__init__(output_stream)
        self._input_stream = input_stream

    @property
    def input(self):
        return self._input_stream

    def process(self, packet: av.Packet, frame_callback=None):
        # Do nothing by default
        pass


class CopyOutputStream(OutputStream):
    def __init__(self, output_container: av.container.OutputContainer, input_stream: InputStream = None):
        if input_stream.type == "data":
            # DataStream.name is 'the codec'
            output_stream = output_container.add_data_stream(input_stream._stream.name)
        else:
            output_stream = output_container.add_stream_from_template(input_stream._stream)

        super().__init__(output_stream, input_stream)

    def process(self, packet: av.Packet, frame_callback=None):
        # Simply copy the packet, i.e. remux

        # We need to skip the "flushing" packets that `demux` generates.
        if packet.dts is None:
            return

        # We need to associate the packet with the this stream
        packet.stream = self
        self._stream.container.mux(packet._packet)
