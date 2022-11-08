import sys

from snakesist.exist_client import ExistClient, NodeResource

if sys.version_info < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version


__version__ = version("snakesist")
