# Copyright (C) 2025, Simona Dimitrova


class Progress:
    def __init__(self, desc=None, total=None, leave=True, unit=None):
        pass

    def set_description(self, description):
        pass

    def update(self, n=1):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
