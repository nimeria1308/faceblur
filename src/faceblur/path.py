# Copyright (C) 2025, Simona Dimitrova

import os


def is_filename_from_ext_group(filename, group):
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() in group


def walk_files(path, skipped=[]):
    files = []

    # Convert any skipped to absolute
    skipped = [
        os.path.abspath(os.path.join(path, f)) if not os.path.isabs(f) else f
        for f in skipped
    ]

    for root, dirs, files_in_dir in os.walk(path):
        for filename in files_in_dir:
            filename = os.path.abspath(os.path.join(root, filename))
            if filename not in skipped:
                files.append(filename)

    return files
