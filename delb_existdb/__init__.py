from __future__ import annotations

from importlib import metadata

from delb_existdb.exist_client import ExistClient, NodeResource

__version__ = metadata.version("delb_existdb")


__all__ = (ExistClient.__name__, NodeResource.__name__, "__version__")
