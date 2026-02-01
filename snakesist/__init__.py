from importlib import metadata

from snakesist.exist_client import ExistClient, NodeResource

__version__ = metadata.version("snakesist")


__all__ = (ExistClient.__name__, NodeResource.__name__, "__version__")
