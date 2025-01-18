# Copyright (C) 2025, Simona Dimitrova

import av.stream

from faceblur.av.stream import InputStream


class Filter():
    def __init__(self, name, **params):
        self._name = name
        self._params = params

    @property
    def name(self):
        return self._name

    @property
    def params(self):
        return self._params


class Graph():
    _graph: av.filter.Graph

    def __init__(self, stream: InputStream, filters: list[Filter]):
        # Create the filter graph:
        # input buffer -> filter 1 -> filter 2 -> ... -> output buffersink
        graph = av.filter.Graph()

        # Prepare the input
        buffer = graph.add_buffer(template=stream._stream)

        # Input buffer is treated as the initial filter
        previous_filter = buffer

        for f in filters:
            # Convert to filter params:
            # param1=value1:param2=value2:...
            params = ":".join([f"{k}={v}" for k, v in f.params.items()]) if f.params else None

            # Previous filter -> filter
            filter = graph.add(f.name, params) if params else graph.add(f.name)
            previous_filter.link_to(filter)
            previous_filter = filter

        # Last filter -> output sink
        buffersink = graph.add("buffersink")
        previous_filter.link_to(buffersink)

        # Compile the graph
        graph.configure()
        self._graph = graph

    def push(self, frame: av.VideoFrame):
        self._graph.vpush(frame)

    def pull(self):
        return self._graph.vpull()
