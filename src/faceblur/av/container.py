# Copyright (C) 2025, Simona Dimitrova

import av

from faceblur.av.video import encoder_from_decoder

EXTENSIONS = [
    "asf", "wmv",                   # windows video
    "avi",                          # audio/video interleave
    "mov", "mp4", "m4v", "3gp",     # mov
    "mkv",                          # matroska
    "mpg", "mpeg", "vob",           # MPEG1/2
    "mjpg",                         # Motion JPEG
    "webm",
]


def process(filename_input, filename_output, frame_callback, encoder=None, thread_type=None):
    with av.open(filename_input) as container_input:
        with av.open(filename_output, "w") as container_output:

            def packet_process_video(packet, stream_output):
                for frame in packet.decode():
                    # process frame
                    frame = frame_callback(frame)

                    # now encode
                    for packet_output in stream_output.encode(frame):
                        container_output.mux(packet_output)

                if packet.dts is None:
                    # Flush the encoder.
                    # Note that the "empty" packet MUST fist be passed to the
                    # encoder to signal flushing
                    while True:
                        try:
                            for packet_output in stream_output.encode(None):
                                container_output.mux(packet_output)
                        except av.error.EOFError:
                            break

            def packet_remux(packet, stream_output):
                # We need to skip the "flushing" packets that `demux` generates.
                if packet.dts is None:
                    return

                # We need to assign the packet to the new stream.
                packet.stream = stream_output
                container_output.mux(packet)

            def packet_skip(packet, stream_output):
                # Simply ignore the packet
                pass

            stream_handlers = {
                "video": packet_process_video,
                "audio": packet_remux,
                # currently data streams are not remuxed, as it causes a sigfault in PyAV
            }

            def create_stream_video(stream_input):
                stream_output = encoder_from_decoder(stream_input, container_output, encoder)

                # Make use of better threading
                if thread_type:
                    stream_input.thread_type = thread_type
                    stream_output.thread_type = thread_type

                return stream_output

            def create_stream_remux(stream_input):
                return container_output.add_stream_from_template(stream_input)

            def create_stream_nop(stream_input):
                pass

            output_creators = {
                "video": create_stream_video,
                "audio": create_stream_remux,
                # currently data streams are not remuxed, as it causes a sigfault in PyAV
            }

            def create_output_stream(stream_input):
                output_stream = output_creators.get(stream_input.type, create_stream_nop)(stream_input)
                output_handler = stream_handlers.get(stream_input.type, packet_skip)
                return output_stream, output_handler

            streams = {stream: create_output_stream(stream) for stream in container_input.streams}

            for packet in container_input.demux():
                output_stream, stream_handler = streams.get(packet.stream)
                stream_handler(packet, output_stream)
