# Building

## Installing build dependencies
Make sure the following pip packages are installed in order to build:

    python -m pip install -U pip build twine

## Building source package and binary wheel
To create both the source package (`*.tar.gz`) and the binary wheel (`*.whl`):

    python -m build

# Upload
To upload to pypi simply use twine:

    twine upload dist/*.tar.gz dist/*.whl
