# Copyright (C) 2025, Simona Dimitrova

import threading

import faceblur.exception as fb_exception


class TerminatedException(fb_exception.FaceblurException):
    pass


class TerminatingCookie:
    def __init__(self):
        self._bomb = threading.Event()

    def requestTermination(self):
        self._bomb.set()

    def throwIfTerminated(self):
        if self._bomb.is_set():
            raise TerminatedException()
